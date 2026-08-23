# Final verification

Verification date: 2026-07-29  
Environment: Windows host, Docker Desktop, PostgreSQL 16, Redis 7

## Static and test gates

| Gate | Result |
| --- | --- |
| `ruff check backend scripts` | Passed |
| `pytest` | 15 passed |
| `npm run lint` | Passed |
| `npm test` | 2 files, 2 tests passed |
| `npx tsc --noEmit` | Passed |
| `npm run build` | Passed; 17 routes emitted |
| Root and frontend `npm audit` | 0 vulnerabilities |
| Docker frontend production build | Passed |
| Docker backend/worker build | Passed |

The frontend build includes landing, login, command center, infrastructure,
cluster detail, node explorer, workloads, forecasting, risks, decisions,
simulation, experiments, replay, policies, models, audit, and settings.

## Runtime gates

| Gate | Result |
| --- | --- |
| Compose services | Backend, frontend, PostgreSQL, and Redis healthy; worker running |
| Alembic | `0002_operational_mvp (head)` |
| Backend readiness | Database ready, Redis ready |
| Frontend root | HTTP 200 |
| OpenAPI | 46 paths |
| Unauthenticated domain request | HTTP 401 |
| Viewer at operator boundary | HTTP 403 |
| Cookie session | Login set an HTTP-only access-token cookie; logout regression passed |
| WebSocket telemetry | Snapshot received; REST tick immediately produced `simulation.ticked` |
| Redis event durability | 65 tenant events read from the bounded stream during final smoke |
| Security headers | API CSP, frame, MIME, referrer, and permissions headers present |
| Seed | 3 clusters, 15 nodes, 3 GPU profiles, 3 teams, 200 workloads, 6 users |
| REST smoke | Clock tick, 4 forecasts, 6 candidate plans, incident, completed experiment |
| Final twin state | Minute 0, ready, 0% utilization, queue 0, 200 workloads, 0 incidents |
| Private Sites deployment | Version 5 succeeded from commit `70d0996` and opened in-app |

## Measured demo result

The final official demo began with 43.0% GPU utilization and no queued work.
After demand, urgent work, cost, and node-failure disruptions, the twin reached
99.0% utilization with four queued jobs.

All schedulers replayed the same running-plus-queued demand against the same
full ready-fleet snapshot:

| Scheduler | Composite score | Jobs placed | Estimated cost | Deadline success |
| --- | ---: | ---: | ---: | ---: |
| FIFO | 667.360 | 51 | $885.17 | 1.0 |
| Priority | 647.686 | 50 | $891.28 | 1.0 |
| Fair share | 638.463 | 51 | $993.49 | 1.0 |
| Bin packing | 637.347 | 51 | $997.76 | 1.0 |
| Deadline aware | 621.179 | 50 | $990.84 | 1.0 |
| ARVA CP-SAT | **675.455** | **51** | **$854.16** | 1.0 |

Recovery restored 15/15 nodes and left three queued jobs during the final
ten-minute window. A second consecutive run produced the same baseline and
scheduler scores; final reset restored exactly the canonical 200 workloads.

## Dependency advisory accounting

Both the orchestration root and standalone frontend report `0 vulnerabilities`.
The frontend uses current patched React, React Server Components, Vite,
Cloudflare Vite plugin, Wrangler, PostCSS, and Sharp releases. The redundant
Next runtime package and vulnerable Next-specific ESLint preset were removed;
Vinext supplies the supported Next API surface and TypeScript declarations.

## Outcome

All implementation, migration, deterministic seed, API, authorization,
simulation, forecasting, optimization, decision, incident, experiment,
Redis stream/pub-sub, WebSocket, frontend build, and Docker execution gates
passed. The private Sites frontend is republished from the validated source
below; a public HTTPS backend remains a separate infrastructure deployment.
