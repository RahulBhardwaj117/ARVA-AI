# Database

## Tenancy and identity

- `organizations`: deployment mode, active policy, timezone
- `users`: organization-scoped identity, Argon2 hash, role, login status

## Digital twin

- `teams`: quotas, fair-share weights, budgets
- `gpu_profiles`: memory, compute, power, hourly cost, efficiency
- `clusters`: region, provider, carbon intensity, power envelope, labels
- `nodes`: cluster/profile, capacity, allocation, health, thermals, labels
- `workloads`: requested resources, lifecycle, placement, deadlines, progress,
  attempts, cost, energy, execution timestamps, constraints
- `simulations`: persistent clock, state, speed, seed, scheduler, scenario
- `metric_samples`: bounded time-series samples derived from twin state
- `checkpoints`: valid recoverable workload progress

## Intelligence and governance

- `model_versions`, `forecasts`, `risks`
- `candidate_plans`, `decisions`
- `policies`, `incidents`, `experiments`, `audit_logs`

All operational tables carry `organization_id`, UUID identity, and UTC creation
and update timestamps. Flexible evidence, rule, action, result, label, and
scenario payloads use JSON while searchable lifecycle and ownership fields
remain typed columns.

Migrations:

1. `0001_foundation`
2. `0002_operational_mvp`

