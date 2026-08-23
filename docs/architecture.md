# Architecture

## Shape

ARVA is a modular monolith with three process roles: a Vinext/React control
plane, a FastAPI REST/WebSocket application, and a Python background worker.
PostgreSQL is the source of truth. Redis provides dependency health, worker
heartbeats, a bounded durable event stream, and tenant-scoped pub/sub fan-out.

```text
Browser
  │ HTTPS / JSON / JWT / WebSocket
  ▼
Vinext/React control plane
  │
  ▼
FastAPI API ─────────────── Redis
  │  auth/RBAC                ▲
  │  domain                   │
  │  simulation           background worker
  │  forecasting
  │  risk/optimization/policy
  │  decisions/incidents/experiments/audit
  ▼
PostgreSQL
```

The modular-monolith boundary keeps tenant authorization and decision
transactions local. Domains communicate through application services rather
than vendor SDKs. Production infrastructure integration belongs behind an
`InfrastructureAdapter`; the implemented adapter is the persistent simulated
environment.

## Closed loop

```text
Twin state
  → derived telemetry
  → adaptive forecast pipeline
  → evidence-backed risk
  → five heuristic alternatives + CP-SAT alternative
  → multi-objective scores
  → active-policy validation
  → recommendation / approval / controlled execution
  → measured cost, energy, queue, SLA, and reliability outcome
  → incident recovery and replanning
```

The simulator never reads UI constants. Workloads, nodes, samples, models,
forecasts, risks, candidate plans, decisions, incidents, checkpoints,
experiments, and audit logs are persisted.

## Security boundaries

- JWT claims contain user, organization, and role and are revalidated against
  the database on protected REST requests.
- Every operational service instance is initialized with the authenticated
  organization ID.
- Six roles map to centralized permissions.
- Argon2 hashes and signing secrets never appear in API responses.
- Request IDs connect safe error envelopes to structured logs.
- Login issues a `Secure` production, HTTP-only, SameSite cookie; bearer JWTs
  remain supported for API clients and authenticated WebSockets.
- Redis-backed request limits use tighter login thresholds and fail open only
  when Redis itself is unavailable.
- Responses include CSP, frame, MIME-sniffing, referrer, and permissions
  protections.
- WebSockets authenticate the same signed access token before accepting.
- Material mutations are appended to Redis Streams and published to the
  organization channel; sockets send reconnect-safe snapshots plus immediate
  event messages.
- Audit rows reject ORM update and delete operations.
- Deployment mode and policy checks are explicit state, not UI conventions.

## Deployment modes

| Mode | Behavior |
| --- | --- |
| Simulation | Actions mutate only the deterministic digital twin |
| Recommendation | Decisions are created but not executed |
| Approval | Decisions wait for an authorized approve/reject transition |
| Controlled autonomous | Feasible, low-risk, policy-allowed plans may execute |
