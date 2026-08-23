"""Create the operational digital-twin and decision tables.

Revision ID: 0002_operational_mvp
Revises: 0001_foundation
Create Date: 2026-07-28
"""

from collections.abc import Sequence

from alembic import op
from app.database.base import Base
from app.models import (  # noqa: F401
    AuditLog,
    CandidatePlan,
    Checkpoint,
    Cluster,
    Decision,
    Experiment,
    Forecast,
    GPUProfile,
    Incident,
    MetricSample,
    ModelVersion,
    Node,
    Policy,
    Risk,
    Simulation,
    Team,
    Workload,
)

revision: str = "0002_operational_mvp"
down_revision: str | None = "0001_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = [
    "teams",
    "gpu_profiles",
    "clusters",
    "nodes",
    "workloads",
    "metric_samples",
    "forecasts",
    "model_versions",
    "risks",
    "policies",
    "candidate_plans",
    "decisions",
    "incidents",
    "checkpoints",
    "simulations",
    "experiments",
    "audit_logs",
]


def upgrade() -> None:
    """Create the full MVP schema after the foundation identity schema."""
    bind = op.get_bind()
    for name in TABLES:
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)


def downgrade() -> None:
    """Remove operational tables while preserving foundation identity data."""
    bind = op.get_bind()
    for name in reversed(TABLES):
        Base.metadata.tables[name].drop(bind=bind, checkfirst=True)

