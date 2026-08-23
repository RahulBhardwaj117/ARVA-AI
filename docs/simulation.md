# Simulation

ARVA uses a deterministic discrete-time digital twin. One tick represents one
minute.

## Tick order

1. Advance the persistent clock.
2. Admit scheduled arrivals to the queue.
3. Progress running workloads.
4. Accrue hardware-profile cost and energy.
5. Record checkpoint progress at the configured interval.
6. Complete work and release node capacity.
7. Place queued work with the selected scheduler.
8. Derive and persist telemetry.
9. Refresh forecasts, risks, plans, and a decision every ten minutes.

Supported lifecycle states: pending, queued, running, checkpointing, migrating,
completed, failed, and cancelled. Recovery returns affected work to the queue
and restores the newest valid checkpoint when present.

Controls: start, pause, resume, single step, 0.25×–64× speed, reset, and bounded
manual tick.

Disruptions: demand spike, urgent workload, cost spike, and node failure. A node
failure evacuates work, preserves checkpoint progress, records an incident,
raises reliability risk, generates a new decision, and can be recovered through
the incident endpoint.

