# ARVA AI project audit

Audit date: 2026-07-28  
Audit scope: repository state before the completion build  
Baseline status: Phase 1 foundation only

This audit was completed before implementation work began. The repository had a
sound identity and runtime foundation, but it did not yet implement the product
described by the official completion brief. Priorities below drive the build
order: the digital twin and the closed-loop decision path are Critical; product
surfaces that depend on them are High; operational hardening is Medium or Low.

| Area | Expected Feature | Current Status | Evidence | Problem | Required Fix | Priority |
| --- | --- | --- | --- | --- | --- | --- |
| Repository | Complete, runnable modular monolith | Partial | Root workspace, `backend`, `frontend`, `scripts`, and `docs` exist | README explicitly stops at Phase 1 | Finish the existing architecture in place and update status honestly | Critical |
| Frontend | Full operational control plane | Partial | Landing, login, and foundation dashboard only | Navigation is disabled and the dashboard states that data does not exist | Add every required route, live queries, actions, states, tables, and charts | High |
| Backend | Complete versioned REST and WebSocket API | Partial | FastAPI app and `/api/v1/auth` exist | Only auth and an operator-check route are implemented | Add all domain routers, services, schemas, and sockets | Critical |
| Authentication | Secure login and current-user lookup | Complete | Argon2 password hashing, signed expiring JWT, `/auth/login`, `/auth/me` | Browser token storage remains a local-demo compromise | Preserve the working flow and document production cookie/IdP boundary | Medium |
| Authorization | Six roles with tenant-scoped permissions | Partial | Six roles and a small central permission matrix exist | Permissions cover only foundation operations | Extend permissions to decision, policy, simulation, experiment, audit, and user actions | High |
| Database | Durable product state | Partial | PostgreSQL, SQLAlchemy base, organizations and users | No operational domain tables | Add normalized domain tables and organization scope | Critical |
| Alembic | Incremental schema lifecycle | Partial | `0001_foundation` creates organizations and users | No product schema migration | Add an incremental full-MVP migration without replacing `0001` | Critical |
| Redis | Runtime event/cache fabric | Partial | Readiness ping and worker heartbeat | No streams, simulation coordination, or socket fan-out | Add event publication and worker simulation ticking | High |
| Worker | Background execution | Partial | Heartbeat loop only | It performs no useful product work | Tick active simulations and publish runtime events | High |
| WebSockets | Live telemetry, risks, decisions, incidents, simulation, experiments | Missing | No WebSocket route or connection manager | Frontend cannot receive live state | Add authenticated organization-scoped channels with reconnect-safe snapshots | High |
| Digital twin | Clusters, nodes, GPUs, teams, workloads and state | Missing | No infrastructure models or APIs | No environment exists to observe or control | Implement persistent tenant-scoped twin and deterministic seed | Critical |
| Simulation clock | Start, pause, resume, step, speed, reset and deterministic time | Missing | No simulation module | The MVP's primary operating mode does not exist | Build a persistent deterministic discrete-time engine | Critical |
| Workload lifecycle | Arrival, queue, placement, running, completion, failure, retry | Missing | No workload model or service | No real scheduling or outcome data | Implement state machine, constraints, retries, and event history | Critical |
| Telemetry | Time-series utilization, queue, latency, power, energy, cost and SLA | Missing | Dashboard intentionally omits metrics | Closed-loop observation is impossible | Derive telemetry from simulator state and persist/query series | Critical |
| Workload generator | Seeded synthetic mixed demand and disruptions | Missing | Seed creates only one admin | Demo has no repeatable operating data | Add deterministic generator and 200-workload seed | Critical |
| Schedulers | FIFO, priority, fair-share, bin-packing and deadline-aware | Missing | No scheduler code | No baselines or plan alternatives | Implement common scheduler interface and measurable strategies | Critical |
| OR-Tools | Real CP-SAT optimization | Missing | OR-Tools is not a dependency | Optimizer cannot enforce hard constraints | Add CP-SAT planner with deterministic feasible fallback | Critical |
| Candidate plans | Alternative plans with scores and trade-offs | Missing | No plan entity | Decisions have nothing to compare | Generate, validate, persist, rank, and explain alternatives | Critical |
| Forecasting | Arrival, queue, duration and failure forecasts with fallback | Missing | No ML dependencies or model registry | No predictive layer | Add last-value/linear/random-forest pipelines and model metadata | Critical |
| Risk detection | Capacity, queue, SLA, failure, cost and energy risks | Missing | No risk service or model | Forecasts cannot trigger action | Compute severity, probability, horizon, evidence, and status | Critical |
| Decision engine | Evidence-based governed recommendations and execution modes | Missing | No decision model or service | Closed loop stops before action | Connect forecasts, risks, plans, policies, execution, and evaluation | Critical |
| Policies | Versioned guardrails, presets, activation and validation | Missing | Organization has only a nullable policy ID string | No safe autonomy boundary | Add presets, versions, rules, dry-run validation, activation, and RBAC | Critical |
| Incidents | Failure injection, detection, recovery, migration and history | Missing | No incident model or API | Recovery demo cannot run | Add node/cost/demand failure paths, checkpoints, replanning, and outcomes | Critical |
| Checkpoints | Durable workload recovery checkpoints | Missing | No checkpoint entity | Failed training work cannot resume | Persist checkpoint progress and restore eligible jobs | High |
| Migration | Policy-compliant workload movement | Missing | No placement/migration service | Recovery cannot evacuate nodes | Implement preemption, evacuation, checkpoint-aware migration, and audit | High |
| Experiments | Scheduler/policy comparisons and run metrics | Missing | No experiment domain | Product cannot prove decisions improve outcomes | Run identical seeded scenarios and persist measured comparisons | High |
| Metrics | Summary KPIs and time-series query API | Missing | Health status is the only metric | UI would need invented numbers | Add backed summary and bounded series endpoints | Critical |
| Audit logs | Immutable actor/action/target/outcome records | Missing | Request logging only | Governance actions are not reviewable | Persist organization-scoped audit events and expose read APIs | High |
| Docker | One-command application stack | Partial | PostgreSQL, Redis, backend, worker, and frontend run in Compose | Stack only serves Phase 1 and seed is not automatic | Install product dependencies, migrate, seed, and health-check full MVP | High |
| Testing | Unit, integration, API, simulation, optimizer and UI coverage | Partial | Six backend foundation tests and one UI test | No product behavior is verified | Add deterministic domain, API, policy, scheduler, experiment, and frontend tests | Critical |
| Documentation | Architecture, database, API, simulation, ML, optimization, testing, deployment, demo, verification | Partial | Architecture, deployment, testing only | Docs describe future phases and contain stale Phase 1 claims | Replace stale claims and add every required operator/developer document | High |
| Security | Safe defaults, secrets boundary, tenant isolation and validation | Partial | Env-based signing key, Argon2, JWT and safe error envelopes | No rate limit; operational queries are not yet tenant scoped because they do not exist | Enforce organization scope everywhere, extend RBAC, validate input, document production controls | High |
| Error handling | Stable envelopes, request IDs, domain conflicts and useful UI states | Partial | Global API and validation handlers exist | Product-specific not-found/conflict/state errors are absent | Preserve envelope and add explicit domain errors plus loading/empty/retry UI | High |

## Build order

1. Add the persistent domain and deterministic simulation engine.
2. Derive telemetry, forecasts, risks, candidate plans, policies, decisions, and
   incident recovery from real simulator state.
3. Expose organization-scoped REST and WebSocket interfaces.
4. Seed a realistic environment and make the demo execute real scenarios.
5. Replace the disabled Phase 1 interface with the complete control plane.
6. Verify tests, migrations, Docker, the demo flow, and the privately hosted UI.

