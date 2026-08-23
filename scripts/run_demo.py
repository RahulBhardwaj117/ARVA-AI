"""Run the official measured ARVA demonstration against persistent state."""

from app.database.session import SessionLocal
from app.models.organization import Organization
from app.models.user import User
from app.services.platform import PlatformService
from sqlalchemy import select


def run() -> None:
    """Advance the twin, inject four disruptions, and compare schedulers."""
    with SessionLocal() as session:
        organization = session.scalar(
            select(Organization).where(Organization.slug == "arva-labs")
        )
        if organization is None:
            raise RuntimeError("Run scripts/seed_database.py before the demo")
        admin = session.scalar(
            select(User).where(
                User.organization_id == organization.id,
                User.email == "admin@arva.local",
            )
        )
        if admin is None:
            raise RuntimeError("The demo administrator is missing")
        platform = PlatformService(session, organization.id)
        platform.control("reset")
        baseline = platform.tick(90)
        injected = [
            platform.inject("demand_spike", admin),
            platform.inject("urgent_workload", admin),
            platform.inject("cost_spike", admin),
            platform.inject("node_failure", admin),
        ]
        experiment = platform.run_experiment(
            name="Official closed-loop scheduler comparison",
            schedulers=[
                "fifo",
                "priority",
                "fair_share",
                "bin_packing",
                "deadline_aware",
                "arva_optimizer",
            ],
            seed=42,
            scenario={"events": [incident.incident_type for incident in injected]},
        )
        after_disruption = platform.tick(20)
        node_incident = next(
            incident for incident in injected if incident.incident_type == "node_failure"
        )
        platform.recover(node_incident, admin)
        final = platform.tick(10)

        print("ARVA AI measured demo complete")
        print(
            f"Baseline: utilization={baseline['gpu_utilization']}%, "
            f"queue={baseline['workloads']['queued']}, cost=${baseline['cost']}"
        )
        print(
            f"Disrupted: utilization={after_disruption['gpu_utilization']}%, "
            f"queue={after_disruption['workloads']['queued']}, "
            f"incidents={after_disruption['active_incidents']}"
        )
        print(f"Experiment winner: {experiment.winner}")
        for result in experiment.results:
            print(
                f"  {result['scheduler']}: score={result['score']}, "
                f"placed={result['jobs_placed']}, cost=${result['estimated_cost']}, "
                f"deadline_success={result['deadline_success']}"
            )
        print(
            f"Recovered: healthy_nodes={final['healthy_nodes']}/{final['nodes']}, "
            f"queue={final['workloads']['queued']}"
        )


if __name__ == "__main__":
    run()
