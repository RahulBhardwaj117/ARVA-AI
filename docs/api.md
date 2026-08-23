# API

Base path: `/api/v1`. OpenAPI is available at `/docs`.

## REST groups

| Group | Representative endpoints |
| --- | --- |
| Auth | `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` |
| Organizations/users/teams | `GET /organizations`, `/users`, `/teams` |
| Hardware | `GET /gpu-profiles`, `/clusters`, `/clusters/{id}`, `/nodes`, `/nodes/{id}` |
| Workloads | list, submit, detail, cancel, retry |
| Metrics | `GET /metrics/summary`, `/metrics/series?metric=...` |
| Forecasts/models | list forecasts, run pipeline, list model registry |
| Risks | list and detail |
| Optimization | generate alternatives, list plans |
| Decisions | list, detail, approve/reject/execute |
| Policies | list, create version, dry-run validate, activate |
| Simulation | summary, control, tick, inject disruption |
| Incidents | list, detail, recover |
| Experiments | list, run, detail |
| Audit/events/settings | append-only audit log, `GET /events`, deployment mode |

## WebSockets

JWT is supplied as the `token` query parameter:

- `/ws/telemetry`
- `/ws/risks`
- `/ws/decisions`
- `/ws/incidents`
- `/ws/simulation`
- `/ws/experiments`
- `/ws/metrics`

Channels authenticate before accept and send reconnect-safe organization-scoped
snapshots. Material REST and worker actions are also published immediately from
tenant Redis channels. `GET /events` reads the bounded durable Redis Stream for
reconnection, support, and replay diagnostics.

Login returns the bearer token contract and also sets `arva_access_token` as an
HTTP-only SameSite cookie. Logout clears it. Browser requests may therefore use
the cookie while WebSocket clients continue to provide the short-lived token.

## Errors

```json
{
  "error": {
    "code": "INVALID_DECISION_STATE",
    "message": "Only approved or recommended decisions can execute",
    "details": {},
    "request_id": "REQ-..."
  }
}
```

Validation, authorization, not-found, conflict, dependency, and unexpected
failures use the same envelope. Internal exceptions and password material are
not returned.
