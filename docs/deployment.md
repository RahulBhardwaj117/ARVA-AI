# Deployment

## Docker Compose

```bash
docker compose up --build
```

| Service | Role | Health |
| --- | --- | --- |
| `frontend` | Vinext/React control plane on port 3000 | HTTP root |
| `backend` | FastAPI/OpenAPI on port 8000; migrates and seeds at boot | `/health` |
| `worker` | Advances simulations whose status is `running` | Redis heartbeat |
| `postgres` | Durable application state | `pg_isready` |
| `redis` | Runtime health, bounded event stream, tenant pub/sub | `PING` |

Named volumes retain PostgreSQL and Redis state across `docker compose down`.
`make reset` intentionally removes local volumes, rebuilds, migrates, and seeds.

## Configuration

Copy `.env.example` to `.env`. Required production changes are the signing
secret, database and Redis credentials, CORS origins, demo seed settings, and a
browser-reachable `NEXT_PUBLIC_API_URL`.

The hosted frontend receives an API URL at build time. `backend:8000` is only
valid inside the Compose network; a hosted frontend needs a deployed HTTPS API.

## Migration lifecycle

`0001_foundation` owns tenant and identity state.
`0002_operational_mvp` incrementally adds operational tables. Existing migration
files are not replaced.

```bash
docker compose exec backend alembic -c backend/alembic.ini current
docker compose exec backend alembic -c backend/alembic.ini upgrade head
```

## Production checklist

- TLS and trusted reverse proxy
- external secret manager and rotation
- reviewed external identity if the built-in HTTP-only cookie session is not used
- managed PostgreSQL backups and point-in-time recovery
- authenticated Redis with explicit persistence/eviction
- tuned production rate-limit thresholds and trusted-proxy policy
- single pre-deployment migration job
- centralized metrics, logs, traces, alerts, and retention
- reviewed production infrastructure adapter and action allowlist
