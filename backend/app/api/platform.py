"""Organization-scoped operational REST API."""

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.permissions import Permission
from app.database.session import get_db
from app.dependencies import APIError, get_current_user, require_permission
from app.events import publish_event, read_recent_events
from app.models.domain import (
    AuditLog,
    CandidatePlan,
    Checkpoint,
    Cluster,
    Decision,
    Experiment,
    Forecast,
    GPUProfile,
    Incident,
    ModelVersion,
    Node,
    Policy,
    Risk,
    Team,
    Workload,
    WorkloadStatus,
)
from app.models.organization import DeploymentMode, Organization
from app.models.user import User
from app.services.platform import PlatformService, audit, entity_dict

router = APIRouter()


class WorkloadCreate(BaseModel):
    """New workload submission."""

    name: str = Field(min_length=3, max_length=180)
    workload_type: Literal[
        "llm_training",
        "fine_tuning",
        "batch_inference",
        "real_time_inference",
        "embedding",
        "research_notebook",
    ]
    team_id: uuid.UUID
    requested_gpus: int = Field(default=1, ge=1, le=64)
    min_gpu_memory_gb: int = Field(default=24, ge=1, le=192)
    duration_minutes: int = Field(ge=1, le=10080)
    priority: int = Field(default=50, ge=1, le=100)
    deadline_minute: int | None = Field(default=None, ge=1)
    preemptible: bool = True
    checkpointable: bool = True


class SimulationControl(BaseModel):
    """Simulation control command."""

    action: Literal["start", "pause", "resume", "step", "reset", "speed"]
    speed: float | None = Field(default=None, ge=0.25, le=64)


class IncidentCreate(BaseModel):
    """Supported deterministic disruption."""

    incident_type: Literal[
        "node_failure", "demand_spike", "cost_spike", "urgent_workload"
    ]


class DecisionAction(BaseModel):
    """Decision transition."""

    action: Literal["approve", "reject", "execute"]


class PolicyCreate(BaseModel):
    """Versioned custom policy."""

    name: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=3, max_length=2000)
    rules: dict[str, object]
    preset: str | None = None


class PolicyValidate(BaseModel):
    """Plan objective values checked against active rules."""

    objective_values: dict[str, float]


class ExperimentCreate(BaseModel):
    """Identical-snapshot scheduler comparison."""

    name: str = Field(default="Scheduler benchmark", min_length=3, max_length=160)
    schedulers: list[
        Literal[
            "fifo",
            "priority",
            "fair_share",
            "bin_packing",
            "deadline_aware",
            "arva_optimizer",
        ]
    ] = [
        "fifo",
        "priority",
        "fair_share",
        "bin_packing",
        "deadline_aware",
        "arva_optimizer",
    ]
    seed: int = 42
    scenario: dict[str, object] = {"source": "current_twin_snapshot"}


def service(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> PlatformService:
    """Resolve the organization-scoped application service."""
    return PlatformService(session, user.organization_id)


def not_found(name: str) -> APIError:
    """Build a safe missing-resource error."""
    return APIError(
        status_code=404,
        code=f"{name.upper()}_NOT_FOUND",
        message=f"The requested {name.replace('_', ' ')} was not found.",
    )


@router.get("/organizations", tags=["organizations"])
def organizations(user: User = Depends(get_current_user)) -> list[dict[str, Any]]:
    """Return the current tenant only."""
    return [entity_dict(user.organization)]


@router.get("/users", tags=["users"])
def users(
    user: User = Depends(require_permission(Permission.MANAGE_USERS)),
    session: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """List safe user records in the current organization."""
    records = session.scalars(
        select(User).where(User.organization_id == user.organization_id)
    ).all()
    return [
        {
            "id": record.id,
            "name": record.name,
            "email": record.email,
            "role": record.role,
            "is_active": record.is_active,
            "last_login_at": record.last_login_at,
        }
        for record in records
    ]


@router.get("/teams", tags=["teams"])
def teams(platform: PlatformService = Depends(service)) -> list[dict[str, Any]]:
    return platform.list_entities(Team)


@router.get("/gpu-profiles", tags=["gpu-profiles"])
def gpu_profiles(platform: PlatformService = Depends(service)) -> list[dict[str, Any]]:
    return platform.list_entities(GPUProfile)


@router.get("/clusters", tags=["clusters"])
def clusters(platform: PlatformService = Depends(service)) -> list[dict[str, Any]]:
    return platform.list_entities(Cluster)


@router.get("/clusters/{cluster_id}", tags=["clusters"])
def cluster_detail(
    cluster_id: uuid.UUID,
    platform: PlatformService = Depends(service),
) -> dict[str, Any]:
    cluster = platform.get_entity(Cluster, cluster_id)
    if cluster is None:
        raise not_found("cluster")
    payload = entity_dict(cluster)
    payload["nodes"] = [
        item
        for item in platform.list_entities(Node)
        if item["cluster_id"] == cluster.id
    ]
    return payload


@router.get("/nodes", tags=["nodes"])
def nodes(
    cluster_id: uuid.UUID | None = None,
    status: str | None = None,
    platform: PlatformService = Depends(service),
) -> list[dict[str, Any]]:
    records = platform.list_entities(Node)
    return [
        record
        for record in records
        if (cluster_id is None or record["cluster_id"] == cluster_id)
        and (status is None or record["status"] == status)
    ]


@router.get("/nodes/{node_id}", tags=["nodes"])
def node_detail(
    node_id: uuid.UUID,
    platform: PlatformService = Depends(service),
) -> dict[str, Any]:
    node = platform.get_entity(Node, node_id)
    if node is None:
        raise not_found("node")
    payload = entity_dict(node)
    payload["workloads"] = [
        item
        for item in platform.list_entities(Workload)
        if item["node_id"] == node.id
    ]
    return payload


@router.get("/workloads", tags=["workloads"])
def workloads(
    status: str | None = None,
    workload_type: str | None = None,
    limit: int = Query(default=250, ge=1, le=1000),
    platform: PlatformService = Depends(service),
) -> list[dict[str, Any]]:
    records = platform.list_entities(Workload, limit=limit)
    return [
        record
        for record in records
        if (status is None or record["status"] == status)
        and (workload_type is None or record["workload_type"] == workload_type)
    ]


@router.post("/workloads", status_code=201, tags=["workloads"])
def submit_workload(
    payload: WorkloadCreate,
    user: User = Depends(require_permission(Permission.SUBMIT_WORKLOAD)),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    platform = PlatformService(session, user.organization_id)
    team = platform.get_entity(Team, payload.team_id)
    if team is None:
        raise not_found("team")
    simulation = platform.active_simulation()
    workload = Workload(
        organization_id=user.organization_id,
        team_id=team.id,
        name=payload.name,
        workload_type=payload.workload_type,
        status=WorkloadStatus.QUEUED.value,
        priority=payload.priority,
        requested_gpus=payload.requested_gpus,
        min_gpu_memory_gb=payload.min_gpu_memory_gb,
        duration_minutes=payload.duration_minutes,
        remaining_minutes=payload.duration_minutes,
        arrival_minute=simulation.current_minute,
        deadline_minute=payload.deadline_minute,
        preemptible=payload.preemptible,
        checkpointable=payload.checkpointable,
        submitted_at=datetime.now(UTC),
        constraints={"source": "api"},
    )
    session.add(workload)
    session.flush()
    audit(
        session,
        user.organization_id,
        actor=user,
        action="workload.submitted",
        target_type="workload",
        target_id=str(workload.id),
    )
    session.commit()
    publish_event(
        user.organization_id,
        "workload.submitted",
        {"workload_id": str(workload.id), "priority": workload.priority},
    )
    return entity_dict(workload)


@router.get("/workloads/{workload_id}", tags=["workloads"])
def workload_detail(
    workload_id: uuid.UUID,
    platform: PlatformService = Depends(service),
) -> dict[str, Any]:
    workload = platform.get_entity(Workload, workload_id)
    if workload is None:
        raise not_found("workload")
    payload = entity_dict(workload)
    payload["checkpoints"] = [
        item
        for item in platform.list_entities(Checkpoint)
        if item["workload_id"] == workload.id
    ]
    return payload


@router.post("/workloads/{workload_id}/cancel", tags=["workloads"])
def cancel_workload(
    workload_id: uuid.UUID,
    user: User = Depends(require_permission(Permission.SUBMIT_WORKLOAD)),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    platform = PlatformService(session, user.organization_id)
    workload = platform.get_entity(Workload, workload_id)
    if workload is None:
        raise not_found("workload")
    if workload.status in {"completed", "cancelled"}:
        raise APIError(
            status_code=409,
            code="INVALID_WORKLOAD_STATE",
            message="A completed or cancelled workload cannot be cancelled.",
        )
    if workload.node_id:
        node = platform.get_entity(Node, workload.node_id)
        if node:
            node.allocated_gpus = max(0, node.allocated_gpus - workload.requested_gpus)
    workload.status = WorkloadStatus.CANCELLED.value
    audit(
        session,
        user.organization_id,
        actor=user,
        action="workload.cancelled",
        target_type="workload",
        target_id=str(workload.id),
    )
    session.commit()
    publish_event(
        user.organization_id,
        "workload.cancelled",
        {"workload_id": str(workload.id)},
    )
    return entity_dict(workload)


@router.post("/workloads/{workload_id}/retry", tags=["workloads"])
def retry_workload(
    workload_id: uuid.UUID,
    user: User = Depends(require_permission(Permission.SUBMIT_WORKLOAD)),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    platform = PlatformService(session, user.organization_id)
    workload = platform.get_entity(Workload, workload_id)
    if workload is None:
        raise not_found("workload")
    if workload.status != WorkloadStatus.FAILED.value:
        raise APIError(
            status_code=409,
            code="INVALID_WORKLOAD_STATE",
            message="Only failed workloads can be retried.",
        )
    workload.status = WorkloadStatus.QUEUED.value
    workload.node_id = None
    workload.cluster_id = None
    session.commit()
    publish_event(
        user.organization_id,
        "workload.retried",
        {"workload_id": str(workload.id)},
    )
    return entity_dict(workload)


@router.get("/metrics/summary", tags=["metrics"])
def metrics_summary(platform: PlatformService = Depends(service)) -> dict[str, Any]:
    return platform.summary()


@router.get("/metrics/series", tags=["metrics"])
def metrics_series(
    metric: Literal[
        "gpu_utilization",
        "queue_depth",
        "running_workloads",
        "completed_workloads",
        "cost",
        "energy_kwh",
        "sla_success",
        "active_incidents",
    ] = "gpu_utilization",
    limit: int = Query(default=120, ge=1, le=1000),
    platform: PlatformService = Depends(service),
) -> list[dict[str, float | int]]:
    return platform.metric_series(metric=metric, limit=limit)


@router.get("/forecasts", tags=["forecasts"])
def forecasts(platform: PlatformService = Depends(service)) -> list[dict[str, Any]]:
    return platform.list_entities(Forecast, limit=100)


@router.post("/forecasts/run", tags=["forecasts"])
def run_forecasts(
    user: User = Depends(require_permission(Permission.OPERATE_INFRASTRUCTURE)),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    platform = PlatformService(session, user.organization_id)
    result = platform.refresh_intelligence()
    session.commit()
    publish_event(user.organization_id, "intelligence.refreshed")
    return result


@router.get("/models", tags=["models"])
def models(platform: PlatformService = Depends(service)) -> list[dict[str, Any]]:
    return platform.list_entities(ModelVersion)


@router.get("/risks", tags=["risks"])
def risks(platform: PlatformService = Depends(service)) -> list[dict[str, Any]]:
    return platform.list_entities(Risk, limit=150)


@router.get("/risks/{risk_id}", tags=["risks"])
def risk_detail(
    risk_id: uuid.UUID,
    platform: PlatformService = Depends(service),
) -> dict[str, Any]:
    risk = platform.get_entity(Risk, risk_id)
    if risk is None:
        raise not_found("risk")
    return entity_dict(risk)


@router.post("/optimization/generate", tags=["optimization"])
def generate_plans(
    user: User = Depends(require_permission(Permission.MANAGE_DECISIONS)),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    platform = PlatformService(session, user.organization_id)
    decision = platform.generate_decision()
    session.commit()
    publish_event(
        user.organization_id,
        "decision.generated",
        {"decision_id": str(decision.id)},
    )
    return {
        "decision": entity_dict(decision),
        "plans": platform.list_entities(CandidatePlan, limit=6),
    }


@router.get("/optimization/plans", tags=["optimization"])
def plans(platform: PlatformService = Depends(service)) -> list[dict[str, Any]]:
    return platform.list_entities(CandidatePlan, limit=100)


@router.get("/decisions", tags=["decisions"])
def decisions(platform: PlatformService = Depends(service)) -> list[dict[str, Any]]:
    return platform.list_entities(Decision, limit=150)


@router.get("/decisions/{decision_id}", tags=["decisions"])
def decision_detail(
    decision_id: uuid.UUID,
    platform: PlatformService = Depends(service),
) -> dict[str, Any]:
    decision = platform.get_entity(Decision, decision_id)
    if decision is None:
        raise not_found("decision")
    payload = entity_dict(decision)
    payload["plans"] = [
        item
        for item in platform.list_entities(CandidatePlan, limit=100)
        if item["decision_id"] == decision.id
    ]
    return payload


@router.post("/decisions/{decision_id}/action", tags=["decisions"])
def transition_decision(
    decision_id: uuid.UUID,
    payload: DecisionAction,
    user: User = Depends(require_permission(Permission.MANAGE_DECISIONS)),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    platform = PlatformService(session, user.organization_id)
    decision = platform.get_entity(Decision, decision_id)
    if decision is None:
        raise not_found("decision")
    try:
        result = platform.decide(decision, payload.action, user)
    except ValueError as exc:
        raise APIError(
            status_code=409,
            code="INVALID_DECISION_STATE",
            message=str(exc),
        ) from exc
    return entity_dict(result)


@router.get("/policies", tags=["policies"])
def policies(platform: PlatformService = Depends(service)) -> list[dict[str, Any]]:
    return platform.list_entities(Policy)


@router.post("/policies", status_code=201, tags=["policies"])
def create_policy(
    payload: PolicyCreate,
    user: User = Depends(require_permission(Permission.MANAGE_POLICIES)),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    previous = session.scalar(
        select(Policy)
        .where(
            Policy.organization_id == user.organization_id,
            Policy.name == payload.name,
        )
        .order_by(Policy.version.desc())
    )
    policy = Policy(
        organization_id=user.organization_id,
        name=payload.name,
        description=payload.description,
        preset=payload.preset,
        version=(previous.version + 1) if previous else 1,
        rules=payload.rules,
    )
    session.add(policy)
    session.flush()
    audit(
        session,
        user.organization_id,
        actor=user,
        action="policy.created",
        target_type="policy",
        target_id=str(policy.id),
        details={"version": policy.version},
    )
    session.commit()
    return entity_dict(policy)


@router.post("/policies/validate", tags=["policies"])
def validate_policy(
    payload: PolicyValidate,
    platform: PlatformService = Depends(service),
) -> dict[str, Any]:
    required = {
        "estimated_cost": 0.0,
        "deadline_success": 1.0,
    }
    metrics = {**required, **payload.objective_values}
    violations = platform.validate_plan(metrics)
    return {"valid": not violations, "violations": violations}


@router.post("/policies/{policy_id}/activate", tags=["policies"])
def activate_policy(
    policy_id: uuid.UUID,
    user: User = Depends(require_permission(Permission.MANAGE_POLICIES)),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    platform = PlatformService(session, user.organization_id)
    policy = platform.get_entity(Policy, policy_id)
    if policy is None:
        raise not_found("policy")
    for existing in platform._all(Policy):
        existing.is_active = existing.id == policy.id
    organization = session.get(Organization, user.organization_id)
    if organization:
        organization.active_policy_id = str(policy.id)
    audit(
        session,
        user.organization_id,
        actor=user,
        action="policy.activated",
        target_type="policy",
        target_id=str(policy.id),
    )
    session.commit()
    return entity_dict(policy)


@router.get("/simulation", tags=["simulation"])
def simulation(platform: PlatformService = Depends(service)) -> dict[str, Any]:
    return platform.summary()


@router.post("/simulation/control", tags=["simulation"])
def control_simulation(
    payload: SimulationControl,
    user: User = Depends(require_permission(Permission.MANAGE_SIMULATION)),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    platform = PlatformService(session, user.organization_id)
    try:
        result = platform.control(payload.action, speed=payload.speed)
    except ValueError as exc:
        raise APIError(
            status_code=400,
            code="INVALID_SIMULATION_ACTION",
            message=str(exc),
        ) from exc
    audit(
        session,
        user.organization_id,
        actor=user,
        action=f"simulation.{payload.action}",
        target_type="simulation",
        target_id=str(platform.active_simulation().id),
        details={"speed": payload.speed} if payload.speed else {},
    )
    session.commit()
    return result


@router.post("/simulation/tick", tags=["simulation"])
def tick_simulation(
    minutes: int = Query(default=1, ge=1, le=60),
    user: User = Depends(require_permission(Permission.MANAGE_SIMULATION)),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    return PlatformService(session, user.organization_id).tick(minutes)


@router.post("/simulation/incidents", status_code=201, tags=["simulation"])
def inject_incident(
    payload: IncidentCreate,
    user: User = Depends(require_permission(Permission.MANAGE_SIMULATION)),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        incident = PlatformService(session, user.organization_id).inject(
            payload.incident_type, user
        )
    except ValueError as exc:
        raise APIError(
            status_code=409,
            code="INCIDENT_INJECTION_FAILED",
            message=str(exc),
        ) from exc
    return entity_dict(incident)


@router.get("/incidents", tags=["incidents"])
def incidents(platform: PlatformService = Depends(service)) -> list[dict[str, Any]]:
    return platform.list_entities(Incident, limit=100)


@router.get("/incidents/{incident_id}", tags=["incidents"])
def incident_detail(
    incident_id: uuid.UUID,
    platform: PlatformService = Depends(service),
) -> dict[str, Any]:
    incident = platform.get_entity(Incident, incident_id)
    if incident is None:
        raise not_found("incident")
    return entity_dict(incident)


@router.post("/incidents/{incident_id}/recover", tags=["incidents"])
def recover_incident(
    incident_id: uuid.UUID,
    user: User = Depends(require_permission(Permission.MANAGE_SIMULATION)),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    platform = PlatformService(session, user.organization_id)
    incident = platform.get_entity(Incident, incident_id)
    if incident is None:
        raise not_found("incident")
    return entity_dict(platform.recover(incident, user))


@router.get("/experiments", tags=["experiments"])
def experiments(platform: PlatformService = Depends(service)) -> list[dict[str, Any]]:
    return platform.list_entities(Experiment, limit=100)


@router.post("/experiments", status_code=201, tags=["experiments"])
def create_experiment(
    payload: ExperimentCreate,
    user: User = Depends(require_permission(Permission.RUN_EXPERIMENTS)),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    experiment = PlatformService(session, user.organization_id).run_experiment(
        name=payload.name,
        schedulers=list(dict.fromkeys(payload.schedulers)),
        seed=payload.seed,
        scenario=payload.scenario,
    )
    return entity_dict(experiment)


@router.get("/experiments/{experiment_id}", tags=["experiments"])
def experiment_detail(
    experiment_id: uuid.UUID,
    platform: PlatformService = Depends(service),
) -> dict[str, Any]:
    experiment = platform.get_entity(Experiment, experiment_id)
    if experiment is None:
        raise not_found("experiment")
    return entity_dict(experiment)


@router.get("/audit", tags=["audit"])
def audit_logs(
    user: User = Depends(require_permission(Permission.VIEW_AUDIT)),
    session: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return PlatformService(session, user.organization_id).list_entities(
        AuditLog, limit=300
    )


@router.get("/events", tags=["audit"])
def events(
    limit: int = Query(default=100, ge=1, le=500),
    user: User = Depends(require_permission(Permission.VIEW_AUDIT)),
) -> list[dict[str, object]]:
    """Return durable organization events from Redis Streams."""
    return read_recent_events(user.organization_id, limit=limit)


@router.get("/settings", tags=["organizations"])
def settings(user: User = Depends(get_current_user)) -> dict[str, Any]:
    return {
        "organization": entity_dict(user.organization),
        "available_deployment_modes": [mode.value for mode in DeploymentMode],
        "scheduler_options": [
            "fifo",
            "priority",
            "fair_share",
            "bin_packing",
            "deadline_aware",
            "arva_optimizer",
        ],
    }


@router.patch("/settings/deployment-mode", tags=["organizations"])
def deployment_mode(
    mode: DeploymentMode,
    user: User = Depends(require_permission(Permission.MANAGE_POLICIES)),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    organization = session.get(Organization, user.organization_id)
    if organization is None:
        raise not_found("organization")
    organization.deployment_mode = mode
    audit(
        session,
        user.organization_id,
        actor=user,
        action="organization.deployment_mode.changed",
        target_type="organization",
        target_id=str(organization.id),
        details={"mode": mode.value},
    )
    session.commit()
    return entity_dict(organization)
