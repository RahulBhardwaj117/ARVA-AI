"""Deterministic tests for the complete closed-loop MVP."""

import pytest
from app.models.domain import AuditLog, Cluster, GPUProfile, Node, Team, Workload
from app.models.organization import Organization
from app.models.user import User
from app.services.forecasting import forecast_series
from app.services.optimization import Capacity, Job, cp_sat_plan
from app.services.platform import PlatformService, seed_environment
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def seed(session: Session, organization: Organization) -> PlatformService:
    """Seed and return an organization-scoped service."""
    seed_environment(session, organization)
    session.commit()
    return PlatformService(session, organization.id)


def test_seed_builds_required_digital_twin(
    session: Session,
    organization: Organization,
) -> None:
    seed(session, organization)

    assert session.scalar(select(func.count(Cluster.id))) == 3
    assert session.scalar(select(func.count(Node.id))) == 15
    assert session.scalar(select(func.count(GPUProfile.id))) == 3
    assert session.scalar(select(func.count(Team.id))) == 3
    assert session.scalar(select(func.count(Workload.id))) == 200


def test_simulation_generates_real_telemetry_and_decisions(
    session: Session,
    organization: Organization,
) -> None:
    platform = seed(session, organization)

    summary = platform.tick(30)
    intelligence = platform.refresh_intelligence()
    session.commit()

    assert summary["workloads"]["running"] > 0
    assert len(platform.metric_series(metric="gpu_utilization")) >= 30
    assert len(intelligence["forecasts"]) == 4
    assert intelligence["decision"]["rationale"]


def test_failure_recovery_and_experiment_are_measured(
    session: Session,
    organization: Organization,
    administrator: User,
) -> None:
    platform = seed(session, organization)
    platform.tick(45)

    incident = platform.inject("node_failure", administrator)
    assert incident.details["node"]
    recovered = platform.recover(incident, administrator)
    platform.inject("urgent_workload", administrator)
    experiment = platform.run_experiment(
        name="Test comparison",
        schedulers=["fifo", "priority", "arva_optimizer"],
        seed=7,
        scenario={"test": True},
    )

    assert recovered.status == "resolved"
    assert len(experiment.results) == 3
    assert experiment.winner in {"fifo", "priority", "arva_optimizer"}
    assert max(result["jobs_placed"] for result in experiment.results) > 0
    assert all("estimated_cost" in result for result in experiment.results)


def test_cost_spike_recovery_restores_canonical_prices(
    session: Session,
    organization: Organization,
    administrator: User,
) -> None:
    platform = seed(session, organization)
    canonical = {
        profile.name: profile.hourly_cost
        for profile in session.scalars(select(GPUProfile)).all()
    }

    incident = platform.inject("cost_spike", administrator)
    spiked = {
        profile.name: profile.hourly_cost
        for profile in session.scalars(select(GPUProfile)).all()
    }
    platform.recover(incident, administrator)
    recovered = {
        profile.name: profile.hourly_cost
        for profile in session.scalars(select(GPUProfile)).all()
    }

    assert all(spiked[name] > price for name, price in canonical.items())
    assert recovered == canonical


def test_reset_removes_injected_workloads_and_restores_seed_baseline(
    session: Session,
    organization: Organization,
    administrator: User,
) -> None:
    platform = seed(session, organization)
    platform.inject("demand_spike", administrator)
    platform.inject("urgent_workload", administrator)

    assert session.scalar(select(func.count(Workload.id))) == 237

    summary = platform.control("reset")

    assert session.scalar(select(func.count(Workload.id))) == 200
    assert summary["simulation"]["current_minute"] == 0
    assert summary["workloads"]["queued"] == 0


def test_audit_records_are_immutable(
    session: Session,
    organization: Organization,
) -> None:
    entry = AuditLog(
        organization_id=organization.id,
        actor_email="system@arva.local",
        action="test.created",
        target_type="test",
        outcome="success",
        details={},
    )
    session.add(entry)
    session.commit()

    entry.outcome = "changed"
    with pytest.raises(ValueError, match="immutable"):
        session.commit()
    session.rollback()

    entry = session.get(AuditLog, entry.id)
    session.delete(entry)
    with pytest.raises(ValueError, match="immutable"):
        session.commit()
    session.rollback()


def test_forecasting_and_cp_sat_have_real_fallbacks() -> None:
    short = forecast_series([1, 2, 3])
    long = forecast_series([float(index % 7 + index / 4) for index in range(30)])
    actions, status = cp_sat_plan(
        [
            Job(
                id="job-1",
                requested_gpus=2,
                memory_gb=40,
                priority=90,
                duration=30,
                deadline=60,
                team="research",
                queued_for=10,
            )
        ],
        [
            Capacity(
                id="expensive-node",
                free_gpus=4,
                memory_gb=80,
                hourly_cost=8,
                power_watts=700,
            ),
            Capacity(
                id="efficient-node",
                free_gpus=4,
                memory_gb=80,
                hourly_cost=2,
                power_watts=350,
            ),
        ],
    )

    assert short.model_name == "last_value"
    assert long.model_name == "random_forest"
    assert status in {"optimal", "feasible"}
    assert actions[0]["workload_id"] == "job-1"
    assert actions[0]["node_id"] == "efficient-node"


def test_operational_api_is_tenant_scoped_and_actionable(
    client: TestClient,
    session: Session,
    organization: Organization,
    administrator: User,
) -> None:
    seed(session, organization)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": administrator.email, "password": "ValidPassword!1"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    clusters = client.get("/api/v1/clusters", headers=headers)
    tick = client.post("/api/v1/simulation/tick?minutes=5", headers=headers)
    summary = client.get("/api/v1/metrics/summary", headers=headers)

    assert clusters.status_code == 200
    assert len(clusters.json()) == 3
    assert tick.status_code == 200
    assert summary.json()["simulation"]["current_minute"] == 5
