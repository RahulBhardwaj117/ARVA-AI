"""Persistent operational domain for the ARVA digital twin."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class WorkloadStatus(StrEnum):
    """Supported workload lifecycle states."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    CHECKPOINTING = "checkpointing"
    MIGRATING = "migrating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SimulationStatus(StrEnum):
    """Persistent simulation states."""

    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


class OrganizationEntity(UUIDPrimaryKeyMixin, TimestampMixin):
    """Fields shared by tenant-scoped domain entities."""

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


class Team(OrganizationEntity, Base):
    """Resource-owning team and fair-share allocation."""

    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    gpu_quota: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    monthly_budget: Mapped[float] = mapped_column(Float, default=10000, nullable=False)
    __table_args__ = (
        Index("ix_teams_organization_slug", "organization_id", "slug", unique=True),
    )


class GPUProfile(OrganizationEntity, Base):
    """GPU hardware profile used by twin nodes and placement constraints."""

    __tablename__ = "gpu_profiles"

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    memory_gb: Mapped[int] = mapped_column(Integer, nullable=False)
    compute_score: Mapped[float] = mapped_column(Float, nullable=False)
    power_watts: Mapped[float] = mapped_column(Float, nullable=False)
    hourly_cost: Mapped[float] = mapped_column(Float, nullable=False)
    energy_efficiency: Mapped[float] = mapped_column(Float, nullable=False)


class Cluster(OrganizationEntity, Base):
    """Logical infrastructure cluster in the digital twin."""

    __tablename__ = "clusters"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    region: Mapped[str] = mapped_column(String(80), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="healthy", nullable=False)
    carbon_intensity: Mapped[float] = mapped_column(Float, default=350, nullable=False)
    power_limit_kw: Mapped[float] = mapped_column(Float, default=40, nullable=False)
    labels: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)


class Node(OrganizationEntity, Base):
    """Compute node in a cluster."""

    __tablename__ = "nodes"

    cluster_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    gpu_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("gpu_profiles.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ready", nullable=False)
    gpu_count: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    allocated_gpus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cpu_cores: Mapped[int] = mapped_column(Integer, default=64, nullable=False)
    memory_gb: Mapped[int] = mapped_column(Integer, default=512, nullable=False)
    temperature_c: Mapped[float] = mapped_column(Float, default=38, nullable=False)
    labels: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)


class Workload(OrganizationEntity, Base):
    """AI workload and its simulated execution state."""

    __tablename__ = "workloads"

    team_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("teams.id"), nullable=False)
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("clusters.id"))
    node_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("nodes.id"))
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    workload_type: Mapped[str] = mapped_column(String(48), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=WorkloadStatus.PENDING.value, nullable=False, index=True
    )
    priority: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    requested_gpus: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    min_gpu_memory_gb: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    arrival_minute: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deadline_minute: Mapped[int | None] = mapped_column(Integer)
    preemptible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    checkpointable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_accrued: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    energy_kwh: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    constraints: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)


class MetricSample(OrganizationEntity, Base):
    """One bounded telemetry sample derived from twin state."""

    __tablename__ = "metric_samples"

    simulation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    minute: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    scope_type: Mapped[str] = mapped_column(String(32), default="organization", nullable=False)
    scope_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    values: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)


class Forecast(OrganizationEntity, Base):
    """Predictive output with model provenance and confidence."""

    __tablename__ = "forecasts"

    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    horizon_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    model_name: Mapped[str] = mapped_column(String(80), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    prediction: Mapped[float] = mapped_column(Float, nullable=False)
    lower_bound: Mapped[float] = mapped_column(Float, nullable=False)
    upper_bound: Mapped[float] = mapped_column(Float, nullable=False)
    features: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)


class ModelVersion(OrganizationEntity, Base):
    """Registered forecast model and evaluation metadata."""

    __tablename__ = "model_versions"

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    task: Mapped[str] = mapped_column(String(80), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(80), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="active", nullable=False)
    metrics: Mapped[dict[str, float]] = mapped_column(JSON, default=dict, nullable=False)
    feature_names: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class Risk(OrganizationEntity, Base):
    """Detected future or current infrastructure risk."""

    __tablename__ = "risks"

    risk_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="open", nullable=False)
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    horizon_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    evidence: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)


class Policy(OrganizationEntity, Base):
    """Versioned policy preset or custom guardrail set."""

    __tablename__ = "policies"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    preset: Mapped[str | None] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rules: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)


class CandidatePlan(OrganizationEntity, Base):
    """Ranked scheduler or optimizer alternative for a decision."""

    __tablename__ = "candidate_plans"

    decision_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    feasible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    objective_values: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    actions: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    violations: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class Decision(OrganizationEntity, Base):
    """Explainable recommendation, approval, or execution decision."""

    __tablename__ = "decisions"

    risk_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    selected_plan_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(String(32), default="recommended", nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    expected_outcome: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    actual_outcome: Mapped[dict[str, float] | None] = mapped_column(JSON)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(Uuid)


class Incident(OrganizationEntity, Base):
    """Injected or detected incident and recovery progress."""

    __tablename__ = "incidents"

    incident_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    detected_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    recovered_minute: Mapped[int | None] = mapped_column(Integer)
    details: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)


class Checkpoint(OrganizationEntity, Base):
    """Recoverable progress snapshot for checkpointable workloads."""

    __tablename__ = "checkpoints"

    workload_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workloads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    minute: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(240), nullable=False)
    valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Simulation(OrganizationEntity, Base):
    """Persistent simulation clock and deterministic configuration."""

    __tablename__ = "simulations"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), default=SimulationStatus.READY.value, nullable=False
    )
    current_minute: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    speed: Mapped[float] = mapped_column(Float, default=1, nullable=False)
    seed: Mapped[int] = mapped_column(Integer, default=42, nullable=False)
    scheduler: Mapped[str] = mapped_column(String(64), default="arva_optimizer", nullable=False)
    scenario: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)


class Experiment(OrganizationEntity, Base):
    """Measured comparison of schedulers under an identical scenario."""

    __tablename__ = "experiments"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    seed: Mapped[int] = mapped_column(Integer, default=42, nullable=False)
    scenario: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    schedulers: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    results: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list, nullable=False)
    winner: Mapped[str | None] = mapped_column(String(64))


class AuditLog(OrganizationEntity, Base):
    """Append-only governance and state-change record."""

    __tablename__ = "audit_logs"

    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    actor_email: Mapped[str] = mapped_column(String(320), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    target_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)


@event.listens_for(AuditLog, "before_update")
@event.listens_for(AuditLog, "before_delete")
def prevent_audit_mutation(*_: object) -> None:
    """Keep governance records append-only through the application ORM."""
    raise ValueError("Audit log records are immutable")
