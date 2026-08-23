# Official demo

Start the stack, sign in, and run:

```bash
docker compose exec backend python scripts/run_demo.py
```

The script:

1. resets the persistent twin;
2. advances a 90-minute baseline;
3. injects a demand spike;
4. adds an urgent deadline workload;
5. increases GPU price by 45%;
6. fails an active node and restores checkpointed progress;
7. advances 20 minutes through replanning;
8. compares six schedulers by replaying the same running-plus-queued demand
   against the same full ready-fleet snapshot;
9. recovers the failed node;
10. advances ten more minutes and prints backed results.

In the UI, use Simulation for the same injections, Risk Center for evidence,
Decisions for alternative selection/execution, Experiments for comparison, and
Replay/Audit for the governance trail.

Results are not hardcoded. Workload placements, hardware profiles, durations,
current queue age, policy constraints, cost, power, and CP-SAT solver output
produce the reported scores.

Reset removes injected and API-submitted workloads, restores the canonical 200
seed workloads and GPU prices, and clears operational results. Re-running the
script therefore produces the same baseline and scheduler scores.
