# Optimization

## Alternatives

Every plan generation evaluates:

- FIFO
- priority
- fair share
- bin packing
- deadline aware
- ARVA optimizer (OR-Tools CP-SAT)

The CP-SAT model creates a binary placement variable for every feasible
workload/node pair. Constraints enforce at-most-one placement per workload, node
GPU capacity, GPU memory compatibility, and node availability. Its objective
rewards priority, queue age, and deadline urgency while penalizing cost and
power. Search is time-bounded and deterministic. A priority heuristic is the
explicit fallback when the solver does not return feasible state.

Plan metrics are calculated from actions: jobs placed, GPU-hours, estimated
cost, energy, deadline success, and queue reduction. The active policy adds
violations for cost and SLA guardrails. A composite score ranks only measured
values and applies a strong infeasibility penalty.

The selected plan, all alternatives, solver status, violations, expected
outcome, rationale, confidence, approval requirement, execution state, actor,
and actual outcome are persisted.

