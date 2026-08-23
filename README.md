# ARVA AI — Autonomous Decision Intelligence System

**Autonomous AI infrastructure optimization**

ARVA AI is a complete simulation-first control plane that observes a persistent
AI compute digital twin, forecasts demand, detects risks, generates alternative
plans, solves constrained placement, validates policy, selects explainable
decisions, executes inside an explicit deployment mode, measures outcomes, and
replans after disruption.

> Most platforms tell operators that infrastructure has a problem. ARVA AI
> predicts the problem, evaluates possible responses, selects the best governed
> action, and explains why.

## What is included

- 3 clusters, 15 heterogeneous GPU nodes, 3 hardware profiles, 3 teams, and 200
  deterministic mixed workloads
- discrete-time lifecycle simulation with start, pause, resume, step, speed,
  reset, checkpoints, cost, energy, thermals, telemetry, failures, and recovery
- FIFO, priority, fair-share, bin-packing, and deadline-aware schedulers
- real OR-Tools CP-SAT constrained placement with a deterministic fallback
- last-value, linear-regression, and random-forest forecasting pipeline
- evidence-backed capacity, queue, reliability, cost, and efficiency risks
- 2–6 candidate plans per decision with objective values and policy violations
- simulation, recommendation, approval, and controlled-autonomous modes
- versioned policy presets, decisions, incidents, experiments, audit events,
  REST APIs, OpenAPI, and seven live WebSocket channels
- 17 frontend routes with real API data, actions, tables, charts,
  loading/empty/error states, and responsive layouts
- PostgreSQL, durable Redis events and live fan-out, a background simulation
  worker, Docker Compose, migrations,
  deterministic seeding, demo automation, tests, and private Sites hosting

## Quick start

On Windows, double-click `ARVA.cmd` and choose **Start ARVA AI**. The launcher
starts Docker Desktop when needed, builds all five services, waits for them to
become healthy, checks the running application, and opens it in your browser.

The same workflow is available from PowerShell:

```powershell
.\arva.ps1 start
```

Docker Desktop is the only prerequisite for this complete local stack. The
backend applies both migrations and seeds the deterministic environment before
serving.

Useful project commands:

```powershell
.\arva.ps1 check    # quick, read-only runtime check
.\arva.ps1 verify   # every automated gate plus a live event/reset test
.\arva.ps1 demo     # measured scheduler and recovery demo
.\arva.ps1 status
.\arva.ps1 stop
```

`verify` checks backend lint and tests, dependency vulnerabilities, frontend
lint/tests/types/production build, Docker health, authentication, seeded data,
security headers, WebSocket delivery, durable events, and deterministic reset.
It advances the twin once and restores it to minute 0 with 200 workloads and no
incidents.

Open:

- Control plane: `http://localhost:3000`
- API documentation: `http://localhost:8000/docs`
- Liveness: `http://localhost:8000/health`
- Readiness: `http://localhost:8000/ready`

Development credentials:

```text
Email:    admin@arva.local
Password: ArvaDemo!2026
```

All six demo roles use the same configurable development password:
`admin`, `operator`, `engineer`, `researcher`, `viewer`, and `auditor` at
`@arva.local` (the administrator address is `admin@arva.local`).

## Run the official demo

```powershell
.\arva.ps1 demo
```

The demo resets the twin, advances a baseline, injects a demand spike, urgent
workload, price spike, and node failure, evaluates real forecasts and decisions,
compares six schedulers on the same state, recovers the node, and prints measured
outcomes.

## Development checks

Run the complete supported check:

```powershell
.\arva.ps1 verify
```

No finite test suite can prove that software has no possible defect, but this
command is the single source of truth for every configured verification gate.
On macOS/Linux or in a Unix shell, equivalent Make targets are `make start`,
`make check`, `make verify`, `make demo`, and `make down`.

## Architecture

```text
Vinext/React control plane
        │ REST + WebSocket
        ▼
FastAPI modular monolith ─── Redis live/event fabric
        │                         ▲
        ▼                         │
PostgreSQL source of truth ◄── simulation worker
        │
        └── twin → telemetry → forecast → risk → alternatives
                   → CP-SAT → policy → decision → outcome → replan
```

Every operational query is organization scoped. The frontend renders persisted
or computed backend results and never invents successful actions.

## Documentation

- [Project audit](docs/project-audit.md)
- [Architecture](docs/architecture.md)
- [Database](docs/database.md)
- [API](docs/api.md)
- [Simulation](docs/simulation.md)
- [Machine learning](docs/machine-learning.md)
- [Optimization](docs/optimization.md)
- [Testing](docs/testing.md)
- [Deployment](docs/deployment.md)
- [Demo](docs/demo.md)
- [Final verification](docs/final-verification.md)

## Production boundary

The MVP is intentionally simulation-first. Its infrastructure adapter is the
persistent digital twin; it does not write to Kubernetes or cloud control
planes. Login now issues an HTTP-only cookie, the API enforces distributed
rate limits and security headers, audit rows are append-only, and both root and
frontend npm audits are clean. Before connecting production infrastructure,
deploy behind TLS, rotate secrets, use authenticated managed PostgreSQL/Redis
with backups, and complete adapter-specific safety reviews.

The private Sites frontend is a real production deployment of the interface,
but a remotely usable control plane still requires a separately deployed HTTPS
FastAPI origin supplied as `NEXT_PUBLIC_API_URL`.
