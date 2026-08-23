"""Heuristic schedulers and the real OR-Tools CP-SAT planner."""

from dataclasses import dataclass

from ortools.sat.python import cp_model


@dataclass(frozen=True)
class Job:
    """Planner projection of a queued workload."""

    id: str
    requested_gpus: int
    memory_gb: int
    priority: int
    duration: int
    deadline: int | None
    team: str
    queued_for: int


@dataclass(frozen=True)
class Capacity:
    """Planner projection of an available node."""

    id: str
    free_gpus: int
    memory_gb: int
    hourly_cost: float
    power_watts: float


def _job_order(jobs: list[Job], strategy: str) -> list[Job]:
    if strategy == "priority":
        return sorted(jobs, key=lambda job: (-job.priority, job.deadline or 10**9))
    if strategy == "fair_share":
        return sorted(jobs, key=lambda job: (job.team, -job.queued_for, -job.priority))
    if strategy == "bin_packing":
        return sorted(jobs, key=lambda job: (-job.requested_gpus, -job.priority))
    if strategy == "deadline_aware":
        return sorted(
            jobs,
            key=lambda job: (job.deadline or 10**9, -job.priority, -job.queued_for),
        )
    return sorted(jobs, key=lambda job: (-job.queued_for, -job.priority))


def heuristic_plan(
    jobs: list[Job],
    capacities: list[Capacity],
    strategy: str,
) -> list[dict[str, object]]:
    """Place jobs greedily using the requested baseline strategy."""
    available = {node.id: node.free_gpus for node in capacities}
    actions: list[dict[str, object]] = []
    for job in _job_order(jobs, strategy):
        candidates = [
            node
            for node in capacities
            if available[node.id] >= job.requested_gpus and node.memory_gb >= job.memory_gb
        ]
        if strategy == "bin_packing":
            candidates.sort(key=lambda node: available[node.id] - job.requested_gpus)
        else:
            candidates.sort(key=lambda node: (node.hourly_cost, -available[node.id]))
        if candidates:
            node = candidates[0]
            available[node.id] -= job.requested_gpus
            actions.append(
                {
                    "action": "place",
                    "workload_id": job.id,
                    "node_id": node.id,
                    "requested_gpus": job.requested_gpus,
                }
            )
    return actions


def cp_sat_plan(
    jobs: list[Job],
    capacities: list[Capacity],
    timeout_seconds: float = 2.0,
) -> tuple[list[dict[str, object]], str]:
    """Maximize policy-weighted placement subject to GPU and memory constraints."""
    if not jobs or not capacities:
        return [], "empty"

    model = cp_model.CpModel()
    placement: dict[tuple[int, int], cp_model.IntVar] = {}
    for job_index, job in enumerate(jobs):
        for node_index, node in enumerate(capacities):
            placement[(job_index, node_index)] = model.new_bool_var(
                f"place_{job_index}_{node_index}"
            )
            if job.memory_gb > node.memory_gb or job.requested_gpus > node.free_gpus:
                model.add(placement[(job_index, node_index)] == 0)
        model.add(
            sum(placement[(job_index, node_index)] for node_index in range(len(capacities)))
            <= 1
        )

    for node_index, node in enumerate(capacities):
        model.add(
            sum(
                placement[(job_index, node_index)] * jobs[job_index].requested_gpus
                for job_index in range(len(jobs))
            )
            <= node.free_gpus
        )

    objective_terms = []
    for job_index, job in enumerate(jobs):
        urgency = max(0, 120 - (job.deadline or 120))
        value = job.priority * 10_000 + job.queued_for * 800 + urgency * 1_500
        for node_index, node in enumerate(capacities):
            gpu_hours = job.requested_gpus * job.duration / 60
            estimated_cost = gpu_hours * node.hourly_cost
            estimated_energy = gpu_hours * node.power_watts / 1000
            penalty = int(estimated_cost * 250 + estimated_energy * 150)
            objective_terms.append(
                placement[(job_index, node_index)] * max(1, value - penalty)
            )
    model.maximize(sum(objective_terms))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout_seconds
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 42
    status = solver.solve(model)
    status_name = solver.status_name(status).lower()
    if status not in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
        return heuristic_plan(jobs, capacities, "priority"), f"fallback:{status_name}"

    actions = []
    for job_index, job in enumerate(jobs):
        for node_index, node in enumerate(capacities):
            if solver.value(placement[(job_index, node_index)]):
                actions.append(
                    {
                        "action": "place",
                        "workload_id": job.id,
                        "node_id": node.id,
                        "requested_gpus": job.requested_gpus,
                    }
                )
    return actions, status_name


def score_plan(
    actions: list[dict[str, object]],
    jobs: list[Job],
    capacities: list[Capacity],
) -> dict[str, float]:
    """Return comparable, non-hardcoded plan metrics."""
    jobs_by_id = {job.id: job for job in jobs}
    nodes_by_id = {node.id: node for node in capacities}
    placed = [jobs_by_id[str(action["workload_id"])] for action in actions]
    gpu_hours = sum(job.requested_gpus * job.duration / 60 for job in placed)
    cost = sum(
        jobs_by_id[str(action["workload_id"])].requested_gpus
        * jobs_by_id[str(action["workload_id"])].duration
        / 60
        * nodes_by_id[str(action["node_id"])].hourly_cost
        for action in actions
    )
    energy = sum(
        jobs_by_id[str(action["workload_id"])].requested_gpus
        * jobs_by_id[str(action["workload_id"])].duration
        / 60
        * nodes_by_id[str(action["node_id"])].power_watts
        / 1000
        for action in actions
    )
    deadlines_met = sum(
        1
        for job in placed
        if job.deadline is None or job.duration <= max(0, job.deadline)
    )
    queue_reduction = sum(job.queued_for for job in placed)
    total_priority = sum(job.priority for job in jobs)
    priority_coverage = sum(job.priority for job in placed) / max(total_priority, 1)
    all_teams = {job.team for job in jobs}
    served_teams = {job.team for job in placed}
    return {
        "jobs_placed": float(len(placed)),
        "gpu_hours": round(gpu_hours, 3),
        "estimated_cost": round(cost, 2),
        "energy_kwh": round(energy, 3),
        "deadline_success": round(deadlines_met / max(len(placed), 1), 3),
        "queue_reduction": float(queue_reduction),
        "priority_coverage": round(priority_coverage, 3),
        "team_fairness": round(len(served_teams) / max(len(all_teams), 1), 3),
    }
