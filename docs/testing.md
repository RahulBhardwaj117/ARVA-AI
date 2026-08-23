# Testing

## Layers

- authentication, safe errors, request IDs, and role boundaries
- deterministic seed cardinality and tenant scope
- simulation lifecycle, telemetry, forecasting, and decision generation
- node failure, checkpoint-aware recovery, and experiment measurement
- cost-spike recovery and deterministic removal of injected workloads on reset
- HTTP-only cookie authentication/logout, security headers, and immutable audit rows
- last-value and random-forest model selection
- OR-Tools feasible placement
- operational API integration
- accessible login behavior
- frontend lint, TypeScript compilation, and production route build
- PostgreSQL migrations, seed idempotence, Docker health, and demo smoke flow

## Commands

On Windows, use the project controller:

```powershell
.\arva.ps1 check
.\arva.ps1 verify
```

`check` is a fast read-only runtime check. It starts Docker Desktop and the
stack if necessary, then verifies the frontend, readiness dependencies,
authentication boundary, login, seed cardinality, security headers, and an
authenticated WebSocket snapshot.

`verify` is the release-grade local gate. It runs backend lint and all tests,
the frontend dependency audit, lint, tests, type check and production build,
validates/builds the Compose stack, exercises REST-to-WebSocket live delivery
and durable events, then resets the twin and proves the canonical final state.
The equivalent Unix-shell command is `make verify`.

Backend tests use one shared in-memory SQLite database per test and recreate the
complete mapped schema. Production migrations are independently verified
against PostgreSQL in Docker.

Randomness is seeded. CP-SAT uses a deterministic seed and one search worker.
Experiments snapshot the same queue and capacity for every scheduler so reported
differences come from scheduling behavior, not different inputs. Experiment
replay evaluates running plus queued demand against the full ready fleet, while
live placement continues to respect only currently free capacity.
