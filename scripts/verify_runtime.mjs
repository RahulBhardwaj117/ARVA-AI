/**
 * Dependency-free runtime verification for the live Docker stack.
 *
 * Usage:
 *   node scripts/verify_runtime.mjs --read-only
 *   node scripts/verify_runtime.mjs
 *
 * The full check advances the twin by one minute to prove Redis/WebSocket
 * fan-out, then resets the environment to the canonical 200-workload baseline.
 */

const readOnly = process.argv.includes("--read-only");
const apiUrl = (process.env.ARVA_API_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);
const frontendUrl = (
  process.env.ARVA_FRONTEND_URL ?? "http://localhost:3000"
).replace(/\/$/, "");
const email = process.env.ARVA_DEMO_ADMIN_EMAIL ?? "admin@arva.local";
const password = process.env.ARVA_DEMO_ADMIN_PASSWORD ?? "ArvaDemo!2026";
const checks = [];

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function pass(name, detail) {
  checks.push(name);
  console.log(`[PASS] ${name}${detail ? ` - ${detail}` : ""}`);
}

async function request(path, options = {}, expectedStatus = 200) {
  const response = await fetch(`${apiUrl}${path}`, options);
  const body = await response.text();
  let data = null;
  if (body) {
    try {
      data = JSON.parse(body);
    } catch {
      data = body;
    }
  }
  assert(
    response.status === expectedStatus,
    `${options.method ?? "GET"} ${path} returned ${response.status}, expected ${expectedStatus}`,
  );
  return { response, data };
}

async function receiveLiveSnapshot(token) {
  const websocketUrl = `${apiUrl.replace(/^http/, "ws")}/ws/telemetry?token=${encodeURIComponent(token)}`;
  const socket = new WebSocket(websocketUrl);
  let eventResolver;
  let eventRejecter;
  const eventPromise = new Promise((resolve, reject) => {
    eventResolver = resolve;
    eventRejecter = reject;
  });
  const snapshotPromise = new Promise((resolve, reject) => {
    const timer = setTimeout(
      () => reject(new Error("Timed out waiting for the WebSocket snapshot")),
      20_000,
    );
    socket.onmessage = (message) => {
      const payload = JSON.parse(String(message.data));
      if (payload.type === "snapshot") {
        clearTimeout(timer);
        resolve(payload.data);
      }
      if (
        payload.type === "event" &&
        payload.data?.type === "simulation.ticked"
      ) {
        eventResolver(payload.data);
      }
    };
    socket.onerror = () => {
      clearTimeout(timer);
      const error = new Error("The authenticated WebSocket connection failed");
      reject(error);
      eventRejecter(error);
    };
  });
  const snapshot = await snapshotPromise;
  return { socket, snapshot, eventPromise };
}

async function main() {
  console.log(
    `\nARVA AI ${readOnly ? "runtime check" : "full runtime verification"}\n`,
  );

  const frontend = await fetch(frontendUrl);
  assert(frontend.ok, `Frontend returned HTTP ${frontend.status}`);
  pass("Frontend", `HTTP ${frontend.status}`);

  const ready = await request("/ready");
  assert(ready.data?.checks?.database === "ready", "PostgreSQL is not ready");
  assert(ready.data?.checks?.redis === "ready", "Redis is not ready");
  pass("Backend readiness", "PostgreSQL and Redis ready");

  const unauthenticated = await request("/api/v1/clusters", {}, 401);
  assert(
    unauthenticated.data?.error?.code === "AUTHENTICATION_REQUIRED",
    "Unauthenticated requests did not return the safe auth error",
  );
  pass("Authentication boundary", "Unauthenticated request rejected");

  const login = await request("/api/v1/auth/login", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const token = login.data?.access_token;
  assert(token, "Login did not return an access token");
  assert(
    /HttpOnly/i.test(login.response.headers.get("set-cookie") ?? ""),
    "Login did not issue an HTTP-only cookie",
  );
  pass("Administrator login", "Bearer token and HTTP-only cookie issued");

  const headers = {
    authorization: `Bearer ${token}`,
    "content-type": "application/json",
  };
  const [clusters, nodes, workloads, users, openapi, summary] = await Promise.all(
    [
      request("/api/v1/clusters", { headers }),
      request("/api/v1/nodes?limit=500", { headers }),
      request("/api/v1/workloads?limit=500", { headers }),
      request("/api/v1/users", { headers }),
      request("/openapi.json"),
      request("/api/v1/metrics/summary", { headers }),
    ],
  );
  assert(clusters.data.length === 3, "Expected exactly 3 seeded clusters");
  assert(nodes.data.length === 15, "Expected exactly 15 seeded nodes");
  assert(workloads.data.length >= 200, "Expected at least 200 workloads");
  assert(users.data.length === 6, "Expected exactly 6 demo users");
  assert(
    Object.keys(openapi.data.paths ?? {}).length >= 46,
    "OpenAPI is missing expected routes",
  );
  assert(summary.data?.simulation, "Metrics summary is missing simulation state");
  pass(
    "Seed and API",
    `${clusters.data.length} clusters, ${nodes.data.length} nodes, ${workloads.data.length} workloads, ${users.data.length} users`,
  );

  const csp = ready.response.headers.get("content-security-policy") ?? "";
  assert(csp.includes("default-src 'none'"), "API CSP header is missing");
  assert(
    ready.response.headers.get("x-content-type-options") === "nosniff",
    "MIME-sniffing protection is missing",
  );
  pass("Security headers", "CSP and MIME protections present");

  const live = await receiveLiveSnapshot(token);
  assert(live.snapshot?.simulation, "WebSocket snapshot is missing simulation data");
  pass("WebSocket authentication", "Organization snapshot received");

  if (!readOnly) {
    let advanced = false;
    try {
      advanced = true;
      await request("/api/v1/simulation/tick?minutes=1", {
        method: "POST",
        headers,
      });
      const event = await Promise.race([
        live.eventPromise,
        new Promise((_, reject) =>
          setTimeout(
            () => reject(new Error("Timed out waiting for simulation.ticked")),
            20_000,
          ),
        ),
      ]);
      assert(event.type === "simulation.ticked", "Wrong live event received");
      const durableEvents = await request("/api/v1/events?limit=100", { headers });
      assert(
        durableEvents.data.some((item) => item.type === "simulation.ticked"),
        "The tick was not persisted in the Redis event stream",
      );
      pass("Live event fan-out", "REST tick received immediately over WebSocket");
      pass(
        "Durable events",
        `${durableEvents.data.length} recent Redis Stream events readable`,
      );
    } finally {
      live.socket.close();
      if (advanced) {
        await request("/api/v1/simulation/control", {
          method: "POST",
          headers,
          body: JSON.stringify({ action: "reset" }),
        });
      }
    }

    const [finalSummary, finalWorkloads, finalIncidents] = await Promise.all([
      request("/api/v1/metrics/summary", { headers }),
      request("/api/v1/workloads?limit=500", { headers }),
      request("/api/v1/incidents", { headers }),
    ]);
    assert(
      finalSummary.data.simulation.current_minute === 0,
      "Final reset did not return to minute 0",
    );
    assert(
      finalSummary.data.simulation.status === "ready",
      "Final reset did not return to ready state",
    );
    assert(
      finalWorkloads.data.length === 200,
      "Final reset did not restore exactly 200 canonical workloads",
    );
    assert(
      finalIncidents.data.length === 0,
      "Final reset did not clear incidents",
    );
    pass("Deterministic reset", "Minute 0, ready, 200 workloads, 0 incidents");
  } else {
    live.socket.close();
  }

  console.log(`\nRESULT: ${checks.length}/${checks.length} checks passed.\n`);
}

try {
  await main();
} catch (error) {
  console.error(`\n[FAIL] ${error instanceof Error ? error.message : String(error)}\n`);
  process.exitCode = 1;
}
