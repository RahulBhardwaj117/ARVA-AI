"""Application service for the simulation-first ARVA closed loop."""

import random
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session

from app.events import publish_event
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
    MetricSample,
    ModelVersion,
    Node,
    Policy,
    Risk,
    Simulation,
    SimulationStatus,
    Team,
    Workload,
    WorkloadStatus,
)
from app.models.organization import DeploymentMode, Organization
from app.models.user import User
from app.services.forecasting import forecast_series
from app.services.optimization import (
    Capacity,
    Job,
    cp_sat_plan,
    heuristic_plan,
    score_plan,
)

SCHEDULERS = ["fifo", "priority", "fair_share", "bin_packing", "deadline_aware"]


def entity_dict(entity: Any) -> dict[str, Any]:
    """Serialize a mapped entity without exposing SQLAlchemy internal state."""
    return {
        attribute.key: getattr(entity, attribute.key)
        for attribute in inspect(entity).mapper.column_attrs
    }


def audit(
    session: Session,
    organization_id: uuid.UUID,
    *,
    actor: User | None,
    action: str,
    target_type: str,
    target_id: str | None = None,
    outcome: str = "success",
    details: dict[str, object] | None = None,
) -> AuditLog:
    """Append one organization-scoped governance event."""
    entry = AuditLog(
        organization_id=organization_id,
        actor_id=actor.id if actor else None,
        actor_email=actor.email if actor else "system@arva.local",
        action=action,
        target_type=target_type,
        target_id=target_id,
        outcome=outcome,
        details=details or {},
    )
    session.add(entry)
    return entry


def seed_environment(session: Session, organization: Organization) -> None:
    """Create the deterministic, idempotent MVP environment."""
    organization.deployment_mode = DeploymentMode.SIMULATION
    rng = random.Random(42)

    teams = session.scalars(
        select(Team).where(Team.organization_id == organization.id)
    ).all()
    if not teams:
        teams = [
            Team(
                organization_id=organization.id,
                name=name,
                slug=slug,
                gpu_quota=quota,
                weight=weight,
                monthly_budget=budget,
            )
            for name, slug, quota, weight, budget in [
                ("Foundation Models", "foundation-models", 28, 1.5, 45000),
                ("Applied AI", "applied-ai", 18, 1.2, 28000),
                ("Research Lab", "research-lab", 12, 1.0, 18000),
            ]
        ]
        session.add_all(teams)
        session.flush()

    profiles = session.scalars(
        select(GPUProfile).where(GPUProfile.organization_id == organization.id)
    ).all()
    if not profiles:
        profiles = [
            GPUProfile(
                organization_id=organization.id,
                name=name,
                memory_gb=memory,
                compute_score=compute,
                power_watts=power,
                hourly_cost=cost,
                energy_efficiency=efficiency,
            )
            for name, memory, compute, power, cost, efficiency in [
                ("NVIDIA H100 80GB", 80, 9.5, 700, 4.75, 13.6),
                ("NVIDIA A100 80GB", 80, 7.4, 400, 3.25, 18.5),
                ("NVIDIA L40S 48GB", 48, 5.7, 350, 1.95, 16.3),
            ]
        ]
        session.add_all(profiles)
        session.flush()

    clusters = session.scalars(
        select(Cluster).where(Cluster.organization_id == organization.id)
    ).all()
    if not clusters:
        clusters = [
            Cluster(
                organization_id=organization.id,
                name=name,
                region=region,
                provider=provider,
                carbon_intensity=carbon,
                power_limit_kw=limit,
                labels={"tier": tier, "environment": "simulation"},
            )
            for name, region, provider, carbon, limit, tier in [
                ("Atlas Primary", "us-east-1", "AWS", 365, 48, "production"),
                ("Helios Efficient", "eu-north-1", "Azure", 82, 34, "green"),
                ("Orion Research", "ap-south-1", "GCP", 510, 28, "research"),
            ]
        ]
        session.add_all(clusters)
        session.flush()

    nodes = session.scalars(
        select(Node).where(Node.organization_id == organization.id)
    ).all()
    if not nodes:
        nodes = []
        for cluster_index, cluster in enumerate(clusters):
            for node_index in range(5):
                profile = profiles[(cluster_index + node_index) % len(profiles)]
                nodes.append(
                    Node(
                        organization_id=organization.id,
                        cluster_id=cluster.id,
                        gpu_profile_id=profile.id,
                        name=f"{cluster.name.split()[0].lower()}-gpu-{node_index + 1:02d}",
                        gpu_count=8 if profile.memory_gb == 80 else 4,
                        cpu_cores=96,
                        memory_gb=768,
                        temperature_c=36 + rng.random() * 5,
                        labels={
                            "rack": f"r{cluster_index + 1}",
                            "accelerator": profile.name,
                        },
                    )
                )
        session.add_all(nodes)
        session.flush()

    policy = session.scalar(
        select(Policy).where(
            Policy.organization_id == organization.id,
            Policy.is_active.is_(True),
        )
    )
    if policy is None:
        presets = [
            (
                "Balanced Operations",
                "balanced",
                {
                    "max_hourly_cost": 180,
                    "max_power_kw": 95,
                    "min_deadline_success": 0.9,
                    "allow_preemption": True,
                    "allow_autonomous_low_risk": True,
                    "weights": {
                        "throughput": 0.3,
                        "cost": 0.2,
                        "energy": 0.15,
                        "sla": 0.25,
                        "fairness": 0.1,
                    },
                },
            ),
            (
                "Cost Guardian",
                "cost_guardian",
                {
                    "max_hourly_cost": 110,
                    "max_power_kw": 100,
                    "min_deadline_success": 0.82,
                    "allow_preemption": True,
                    "allow_autonomous_low_risk": True,
                },
            ),
            (
                "SLA First",
                "sla_first",
                {
                    "max_hourly_cost": 240,
                    "max_power_kw": 120,
                    "min_deadline_success": 0.97,
                    "allow_preemption": False,
                    "allow_autonomous_low_risk": False,
                },
            ),
        ]
        policies = [
            Policy(
                organization_id=organization.id,
                name=name,
                description=f"ARVA {name.lower()} policy preset.",
                preset=preset,
                is_active=index == 0,
                rules=rules,
            )
            for index, (name, preset, rules) in enumerate(presets)
        ]
        session.add_all(policies)
        session.flush()
        organization.active_policy_id = str(policies[0].id)

    simulation = session.scalar(
        select(Simulation).where(Simulation.organization_id == organization.id)
    )
    if simulation is None:
        session.add(
            Simulation(
                organization_id=organization.id,
                name="ARVA deterministic operations twin",
                seed=42,
                scheduler="arva_optimizer",
                scenario={
                    "arrival_pattern": "diurnal_bursty",
                    "checkpoint_interval": 15,
                    "duration_minutes": 1440,
                },
            )
        )

    workload_count = session.scalar(
        select(func.count(Workload.id)).where(Workload.organization_id == organization.id)
    )
    if not workload_count:
        workload_types = [
            "llm_training",
            "fine_tuning",
            "batch_inference",
            "real_time_inference",
            "embedding",
            "research_notebook",
        ]
        workloads: list[Workload] = []
        for index in range(200):
            workload_type = rng.choice(workload_types)
            priority = rng.choice([25, 40, 50, 65, 80, 95])
            requested_gpus = (
                rng.choice([4, 8])
                if workload_type == "llm_training"
                else rng.choice([1, 1, 2, 4])
            )
            duration = rng.randint(20, 360)
            arrival = int((index / 200) * 720) + rng.randint(0, 18)
            deadline = arrival + duration + rng.randint(30, 240) if priority >= 65 else None
            workloads.append(
                Workload(
                    organization_id=organization.id,
                    team_id=teams[index % len(teams)].id,
                    name=f"{workload_type.replace('_', ' ').title()} #{index + 1:03d}",
                    workload_type=workload_type,
                    priority=priority,
                    requested_gpus=requested_gpus,
                    min_gpu_memory_gb=48 if requested_gpus >= 4 else 24,
                    duration_minutes=duration,
                    remaining_minutes=duration,
                    arrival_minute=arrival,
                    deadline_minute=deadline,
                    preemptible=workload_type not in {"real_time_inference"},
                    checkpointable=workload_type
                    in {"llm_training", "fine_tuning", "batch_inference"},
                    constraints={
                        "source": "seed",
                        "data_residency": None,
                        "max_retries": 2,
                    },
                )
            )
        session.add_all(workloads)

    model_count = session.scalar(
        select(func.count(ModelVersion.id)).where(
            ModelVersion.organization_id == organization.id
        )
    )
    if not model_count:
        session.add_all(
            [
                ModelVersion(
                    organization_id=organization.id,
                    name=f"{task.replace('_', ' ').title()} Forecaster",
                    task=task,
                    algorithm="adaptive_baseline",
                    version="1.0.0",
                    metrics={"mae": 0, "coverage": 0},
                    feature_names=["last", "rolling_mean", "rolling_std", "time_index"],
                )
                for task in [
                    "gpu_utilization",
                    "queue_depth",
                    "arrival_rate",
                    "failure_probability",
                ]
            ]
        )
    audit(
        session,
        organization.id,
        actor=None,
        action="environment.seeded",
        target_type="organization",
        target_id=str(organization.id),
        details={"clusters": 3, "nodes": 15, "workloads": 200, "seed": 42},
    )


class PlatformService:
    """Coordinate persistence, simulation, forecasts, risk, and decisions."""

    def __init__(self, session: Session, organization_id: uuid.UUID) -> None:
        self.session = session
        self.organization_id = organization_id

    def _all(self, model: type[Any], *, limit: int = 500) -> list[Any]:
        return list(
            self.session.scalars(
                select(model)
                .where(model.organization_id == self.organization_id)
                .order_by(model.created_at.desc())
                .limit(limit)
            )
        )

    def list_entities(self, model: type[Any], *, limit: int = 500) -> list[dict[str, Any]]:
        return [entity_dict(entity) for entity in self._all(model, limit=limit)]

    def get_entity(self, model: type[Any], entity_id: uuid.UUID) -> Any | None:
        return self.session.scalar(
            select(model).where(
                model.id == entity_id,
                model.organization_id == self.organization_id,
            )
        )

    def active_simulation(self) -> Simulation:
        simulation = self.session.scalar(
            select(Simulation)
            .where(Simulation.organization_id == self.organization_id)
            .order_by(Simulation.created_at)
        )
        if simulation is None:
            simulation = Simulation(
                organization_id=self.organization_id,
                name="ARVA operations twin",
                scenario={"checkpoint_interval": 15},
            )
            self.session.add(simulation)
            self.session.flush()
        return simulation

    def summary(self) -> dict[str, Any]:
        nodes = self._all(Node)
        workloads = self._all(Workload)
        total_gpus = sum(node.gpu_count for node in nodes if node.status != "failed")
        allocated = sum(node.allocated_gpus for node in nodes)
        running = [workload for workload in workloads if workload.status == "running"]
        queued = [workload for workload in workloads if workload.status == "queued"]
        completed = [workload for workload in workloads if workload.status == "completed"]
        open_risks = [risk for risk in self._all(Risk) if risk.status == "open"]
        incidents = [
            incident for incident in self._all(Incident) if incident.status != "resolved"
        ]
        simulation = self.active_simulation()
        return {
            "simulation": entity_dict(simulation),
            "clusters": len(self._all(Cluster)),
            "nodes": len(nodes),
            "healthy_nodes": sum(node.status == "ready" for node in nodes),
            "failed_nodes": sum(node.status == "failed" for node in nodes),
            "gpu_capacity": total_gpus,
            "allocated_gpus": allocated,
            "gpu_utilization": round(100 * allocated / max(total_gpus, 1), 1),
            "workloads": {
                "total": len(workloads),
                "queued": len(queued),
                "running": len(running),
                "completed": len(completed),
                "failed": sum(workload.status == "failed" for workload in workloads),
            },
            "cost": round(sum(workload.cost_accrued for workload in workloads), 2),
            "energy_kwh": round(sum(workload.energy_kwh for workload in workloads), 2),
            "sla_success": round(
                100
                * sum(
                    workload.deadline_minute is None
                    or simulation.current_minute <= workload.deadline_minute
                    for workload in completed
                )
                / max(len(completed), 1),
                1,
            ),
            "open_risks": len(open_risks),
            "critical_risks": sum(risk.severity == "critical" for risk in open_risks),
            "active_incidents": len(incidents),
            "recent_decisions": self.list_entities(Decision, limit=5),
        }

    def _planner_inputs(
        self,
        minute: int,
        *,
        full_ready_capacity: bool = False,
        include_running: bool = False,
    ) -> tuple[list[Job], list[Capacity]]:
        teams = {str(team.id): team.slug for team in self._all(Team)}
        profiles = {profile.id: profile for profile in self._all(GPUProfile)}
        jobs = [
            Job(
                id=str(workload.id),
                requested_gpus=workload.requested_gpus,
                memory_gb=workload.min_gpu_memory_gb,
                priority=workload.priority,
                duration=workload.remaining_minutes,
                deadline=(
                    workload.deadline_minute - minute
                    if workload.deadline_minute is not None
                    else None
                ),
                team=teams.get(str(workload.team_id), "unknown"),
                queued_for=max(0, minute - workload.arrival_minute),
            )
            for workload in self._all(Workload)
            if workload.status == WorkloadStatus.QUEUED.value
            or (
                include_running
                and workload.status == WorkloadStatus.RUNNING.value
            )
        ]
        capacities = [
            Capacity(
                id=str(node.id),
                free_gpus=(
                    node.gpu_count
                    if full_ready_capacity
                    else max(0, node.gpu_count - node.allocated_gpus)
                ),
                memory_gb=profiles[node.gpu_profile_id].memory_gb,
                hourly_cost=profiles[node.gpu_profile_id].hourly_cost,
                power_watts=profiles[node.gpu_profile_id].power_watts,
            )
            for node in self._all(Node)
            if node.status == "ready"
            and (full_ready_capacity or node.allocated_gpus < node.gpu_count)
        ]
        return jobs, capacities

    def _schedule(self, simulation: Simulation) -> int:
        jobs, capacities = self._planner_inputs(simulation.current_minute)
        if simulation.scheduler == "arva_optimizer":
            actions, _ = cp_sat_plan(jobs, capacities)
        else:
            actions = heuristic_plan(jobs, capacities, simulation.scheduler)
        jobs_by_id = {
            str(workload.id): workload
            for workload in self._all(Workload)
            if workload.status == WorkloadStatus.QUEUED.value
        }
        nodes_by_id = {str(node.id): node for node in self._all(Node)}
        placed = 0
        for action in actions:
            workload = jobs_by_id.get(str(action["workload_id"]))
            node = nodes_by_id.get(str(action["node_id"]))
            if (
                workload is None
                or node is None
                or node.allocated_gpus + workload.requested_gpus > node.gpu_count
            ):
                continue
            workload.node_id = node.id
            workload.cluster_id = node.cluster_id
            workload.status = WorkloadStatus.RUNNING.value
            workload.started_at = workload.started_at or datetime.now(UTC)
            workload.attempts += 1
            node.allocated_gpus += workload.requested_gpus
            placed += 1
        return placed

    def _sample_metrics(self, simulation: Simulation) -> MetricSample:
        summary = self.summary()
        sample = MetricSample(
            organization_id=self.organization_id,
            simulation_id=simulation.id,
            minute=simulation.current_minute,
            values={
                "gpu_utilization": float(summary["gpu_utilization"]),
                "queue_depth": float(summary["workloads"]["queued"]),
                "running_workloads": float(summary["workloads"]["running"]),
                "completed_workloads": float(summary["workloads"]["completed"]),
                "cost": float(summary["cost"]),
                "energy_kwh": float(summary["energy_kwh"]),
                "sla_success": float(summary["sla_success"]),
                "active_incidents": float(summary["active_incidents"]),
            },
        )
        self.session.add(sample)
        return sample

    def tick(self, minutes: int = 1) -> dict[str, Any]:
        """Advance deterministic state and derive telemetry from actual changes."""
        simulation = self.active_simulation()
        profiles = {profile.id: profile for profile in self._all(GPUProfile)}
        for _ in range(max(1, min(minutes, 60))):
            simulation.current_minute += 1
            for workload in self._all(Workload):
                if (
                    workload.status == WorkloadStatus.PENDING.value
                    and workload.arrival_minute <= simulation.current_minute
                ):
                    workload.status = WorkloadStatus.QUEUED.value
                    workload.submitted_at = datetime.now(UTC)

            nodes = {node.id: node for node in self._all(Node)}
            running = [
                workload
                for workload in self._all(Workload)
                if workload.status == WorkloadStatus.RUNNING.value
            ]
            for workload in running:
                node = nodes.get(workload.node_id)
                if node is None or node.status != "ready":
                    workload.status = WorkloadStatus.QUEUED.value
                    workload.node_id = None
                    workload.cluster_id = None
                    continue
                profile = profiles[node.gpu_profile_id]
                workload.remaining_minutes = max(0, workload.remaining_minutes - 1)
                workload.cost_accrued += (
                    workload.requested_gpus * profile.hourly_cost / 60
                )
                workload.energy_kwh += (
                    workload.requested_gpus * profile.power_watts / 60 / 1000
                )
                node.temperature_c = round(
                    min(86, 38 + 42 * node.allocated_gpus / max(node.gpu_count, 1)), 2
                )
                if (
                    workload.checkpointable
                    and simulation.current_minute % int(
                        simulation.scenario.get("checkpoint_interval", 15)
                    )
                    == 0
                ):
                    self.session.add(
                        Checkpoint(
                            organization_id=self.organization_id,
                            workload_id=workload.id,
                            minute=simulation.current_minute,
                            remaining_minutes=workload.remaining_minutes,
                            storage_uri=f"mock://checkpoints/{workload.id}/{simulation.current_minute}",
                        )
                    )
                if workload.remaining_minutes == 0:
                    workload.status = WorkloadStatus.COMPLETED.value
                    workload.completed_at = datetime.now(UTC)
                    node.allocated_gpus = max(
                        0, node.allocated_gpus - workload.requested_gpus
                    )
                    workload.node_id = None

            self._schedule(simulation)
            self._sample_metrics(simulation)
            if simulation.current_minute % 10 == 0:
                self.refresh_intelligence()

        self.session.commit()
        result = self.summary()
        publish_event(
            self.organization_id,
            "simulation.ticked",
            {
                "minute": result["simulation"]["current_minute"],
                "gpu_utilization": result["gpu_utilization"],
                "queue_depth": result["workloads"]["queued"],
            },
        )
        return result

    def control(self, action: str, *, speed: float | None = None) -> dict[str, Any]:
        """Apply a validated simulation clock action."""
        simulation = self.active_simulation()
        if action == "start" or action == "resume":
            simulation.status = SimulationStatus.RUNNING.value
        elif action == "pause":
            simulation.status = SimulationStatus.PAUSED.value
        elif action == "step":
            simulation.status = SimulationStatus.PAUSED.value
            return self.tick(1)
        elif action == "reset":
            simulation.status = SimulationStatus.READY.value
            simulation.current_minute = 0
            canonical_costs = {
                "NVIDIA H100 80GB": 4.75,
                "NVIDIA A100 80GB": 3.25,
                "NVIDIA L40S 48GB": 1.95,
            }
            for profile in self._all(GPUProfile):
                if profile.name in canonical_costs:
                    profile.hourly_cost = canonical_costs[profile.name]
            for node in self._all(Node):
                node.status = "ready"
                node.allocated_gpus = 0
                node.temperature_c = 38
            for workload in self._all(Workload):
                base_name, separator, suffix = workload.name.rpartition(" #")
                seeded_name = (
                    separator == " #"
                    and base_name
                    in {
                        "Llm Training",
                        "Fine Tuning",
                        "Batch Inference",
                        "Real Time Inference",
                        "Embedding",
                        "Research Notebook",
                    }
                    and len(suffix) == 3
                    and suffix.isdigit()
                    and 1 <= int(suffix) <= 200
                )
                if workload.constraints.get("source") != "seed" and not seeded_name:
                    self.session.delete(workload)
                    continue
                workload.status = WorkloadStatus.PENDING.value
                workload.node_id = None
                workload.cluster_id = None
                workload.remaining_minutes = workload.duration_minutes
                workload.cost_accrued = 0
                workload.energy_kwh = 0
                workload.started_at = None
                workload.completed_at = None
                workload.attempts = 0
            for model in [
                MetricSample,
                Forecast,
                Risk,
                CandidatePlan,
                Decision,
                Incident,
                Checkpoint,
                Experiment,
            ]:
                self.session.execute(
                    delete(model).where(model.organization_id == self.organization_id)
                )
        elif action == "speed":
            simulation.speed = max(0.25, min(speed or 1, 64))
        else:
            raise ValueError(f"Unsupported simulation action: {action}")
        self.session.commit()
        result = self.summary()
        publish_event(
            self.organization_id,
            f"simulation.{action}",
            {
                "minute": result["simulation"]["current_minute"],
                "status": result["simulation"]["status"],
            },
        )
        return result

    def refresh_intelligence(self) -> dict[str, Any]:
        """Forecast current series, detect risks, and generate a governed decision."""
        samples = list(
            reversed(
                self.session.scalars(
                    select(MetricSample)
                    .where(MetricSample.organization_id == self.organization_id)
                    .order_by(MetricSample.minute.desc())
                    .limit(80)
                ).all()
            )
        )
        if not samples:
            self._sample_metrics(self.active_simulation())
            samples = self._all(MetricSample, limit=1)
        forecasts: list[Forecast] = []
        for metric in ["gpu_utilization", "queue_depth", "cost", "active_incidents"]:
            result = forecast_series(
                [float(sample.values.get(metric, 0)) for sample in samples],
                horizon=6,
            )
            forecast = Forecast(
                organization_id=self.organization_id,
                metric=metric,
                horizon_minutes=30,
                model_name=result.model_name,
                confidence=result.confidence,
                prediction=result.prediction,
                lower_bound=result.lower,
                upper_bound=result.upper,
                features={"history_size": len(samples), "mae": result.mae},
            )
            self.session.add(forecast)
            forecasts.append(forecast)

        by_metric = {forecast.metric: forecast for forecast in forecasts}
        summary = self.summary()
        risk_specs: list[tuple[str, str, float, str, dict[str, object], str]] = []
        if by_metric["gpu_utilization"].upper_bound >= 85:
            risk_specs.append(
                (
                    "capacity",
                    "high" if by_metric["gpu_utilization"].upper_bound < 95 else "critical",
                    min(0.98, by_metric["gpu_utilization"].confidence + 0.05),
                    "GPU saturation is forecast within 30 minutes",
                    {
                        "forecast_upper": by_metric["gpu_utilization"].upper_bound,
                        "current": summary["gpu_utilization"],
                    },
                    "Rebalance queued jobs toward efficient free capacity.",
                )
            )
        if by_metric["queue_depth"].upper_bound >= 8:
            risk_specs.append(
                (
                    "queue",
                    "high",
                    by_metric["queue_depth"].confidence,
                    "Queue pressure threatens service objectives",
                    {
                        "forecast_upper": by_metric["queue_depth"].upper_bound,
                        "current": summary["workloads"]["queued"],
                    },
                    "Apply deadline-aware placement and protect urgent workloads.",
                )
            )
        if summary["active_incidents"]:
            risk_specs.append(
                (
                    "reliability",
                    "critical",
                    0.96,
                    "Active infrastructure incident requires recovery",
                    {"active_incidents": summary["active_incidents"]},
                    "Evacuate checkpointable jobs and replan remaining capacity.",
                )
            )
        if not risk_specs:
            risk_specs.append(
                (
                    "efficiency",
                    "low",
                    0.72,
                    "Opportunity to consolidate low-priority workloads",
                    {
                        "gpu_utilization": summary["gpu_utilization"],
                        "queue_depth": summary["workloads"]["queued"],
                    },
                    "Use bin-packing while retaining SLA headroom.",
                )
            )

        risk_type, severity, probability, title, evidence, recommendation = risk_specs[0]
        risk = Risk(
            organization_id=self.organization_id,
            risk_type=risk_type,
            severity=severity,
            probability=probability,
            horizon_minutes=30,
            title=title,
            evidence=evidence,
            recommended_action=recommendation,
        )
        self.session.add(risk)
        self.session.flush()
        decision = self.generate_decision(risk)
        self.session.flush()
        return {
            "forecasts": [entity_dict(forecast) for forecast in forecasts],
            "risk": entity_dict(risk),
            "decision": entity_dict(decision),
        }

    def _active_policy(self) -> Policy | None:
        return self.session.scalar(
            select(Policy).where(
                Policy.organization_id == self.organization_id,
                Policy.is_active.is_(True),
            )
        )

    def validate_plan(self, metrics: dict[str, float]) -> list[str]:
        """Return explicit policy violations for plan metrics."""
        policy = self._active_policy()
        if policy is None:
            return ["No active policy"]
        violations = []
        if metrics["estimated_cost"] > float(policy.rules.get("max_hourly_cost", 9999)):
            violations.append("Estimated cost exceeds the active policy limit")
        if metrics["deadline_success"] < float(
            policy.rules.get("min_deadline_success", 0)
        ):
            violations.append("Projected deadline success is below policy minimum")
        return violations

    def generate_decision(self, risk: Risk | None = None) -> Decision:
        """Generate 2-6 real alternatives and select the best feasible plan."""
        simulation = self.active_simulation()
        jobs, capacities = self._planner_inputs(simulation.current_minute)
        alternatives: list[tuple[str, list[dict[str, object]], str]] = []
        for strategy in SCHEDULERS:
            alternatives.append((strategy, heuristic_plan(jobs, capacities, strategy), "ok"))
        optimized, solver_status = cp_sat_plan(jobs, capacities)
        alternatives.append(("arva_optimizer", optimized, solver_status))

        plans: list[CandidatePlan] = []
        for strategy, actions, solver in alternatives[:6]:
            metrics = score_plan(actions, jobs, capacities)
            violations = self.validate_plan(metrics)
            score = (
                metrics["jobs_placed"] * 20
                + metrics["deadline_success"] * 40
                + metrics["priority_coverage"] * 25
                + metrics["team_fairness"] * 10
                + metrics["queue_reduction"] * 0.05
                - metrics["estimated_cost"] * 0.35
                - metrics["energy_kwh"] * 0.2
                - len(violations) * 100
            )
            plan = CandidatePlan(
                organization_id=self.organization_id,
                strategy=strategy,
                feasible=not violations,
                score=round(score, 3),
                objective_values={**metrics, "solver_status": solver},
                actions=actions,
                violations=violations,
            )
            self.session.add(plan)
            plans.append(plan)
        self.session.flush()
        selected = max(plans, key=lambda plan: plan.score)
        organization = self.session.get(Organization, self.organization_id)
        assert organization is not None
        requires_approval = organization.deployment_mode == DeploymentMode.APPROVAL
        status = "pending_approval" if requires_approval else "recommended"
        if (
            organization.deployment_mode == DeploymentMode.CONTROLLED_AUTONOMOUS
            and selected.feasible
            and (risk is None or risk.severity in {"low", "medium"})
        ):
            status = "executed"
            self._execute_actions(selected.actions)
        decision = Decision(
            organization_id=self.organization_id,
            risk_id=risk.id if risk else None,
            selected_plan_id=selected.id,
            status=status,
            action_type="schedule_and_rebalance",
            title=f"Apply {selected.strategy.replace('_', ' ')} plan",
            rationale=(
                f"Selected from {len(plans)} alternatives. It maximizes policy-weighted "
                f"throughput and SLA performance with score {selected.score:.1f}; "
                f"solver status {selected.objective_values.get('solver_status', 'n/a')}."
            ),
            confidence=0.88 if selected.feasible else 0.54,
            expected_outcome={
                key: float(value)
                for key, value in selected.objective_values.items()
                if isinstance(value, (int, float))
            },
            requires_approval=requires_approval,
        )
        self.session.add(decision)
        self.session.flush()
        for plan in plans:
            plan.decision_id = decision.id
        return decision

    def _execute_actions(self, actions: list[dict[str, object]]) -> int:
        workloads = {str(item.id): item for item in self._all(Workload)}
        nodes = {str(item.id): item for item in self._all(Node)}
        executed = 0
        for action in actions:
            workload = workloads.get(str(action.get("workload_id")))
            node = nodes.get(str(action.get("node_id")))
            if (
                workload
                and node
                and workload.status == WorkloadStatus.QUEUED.value
                and node.status == "ready"
                and node.allocated_gpus + workload.requested_gpus <= node.gpu_count
            ):
                workload.status = WorkloadStatus.RUNNING.value
                workload.node_id = node.id
                workload.cluster_id = node.cluster_id
                node.allocated_gpus += workload.requested_gpus
                executed += 1
        return executed

    def decide(self, decision: Decision, action: str, actor: User) -> Decision:
        """Approve, reject, or execute a persisted decision."""
        if action == "approve":
            decision.status = "approved"
            decision.decided_by = actor.id
        elif action == "reject":
            decision.status = "rejected"
            decision.decided_by = actor.id
        elif action == "execute":
            if decision.status not in {"approved", "recommended"}:
                raise ValueError("Only approved or recommended decisions can execute")
            plan = self.get_entity(CandidatePlan, decision.selected_plan_id)
            if plan is None or not plan.feasible:
                raise ValueError("The selected plan is not feasible")
            executed = self._execute_actions(plan.actions)
            decision.status = "executed"
            decision.decided_by = actor.id
            decision.actual_outcome = {"actions_executed": float(executed)}
        else:
            raise ValueError("Unsupported decision action")
        audit(
            self.session,
            self.organization_id,
            actor=actor,
            action=f"decision.{action}",
            target_type="decision",
            target_id=str(decision.id),
        )
        self.session.commit()
        publish_event(
            self.organization_id,
            f"decision.{action}",
            {"decision_id": str(decision.id), "status": decision.status},
        )
        return decision

    def inject(self, incident_type: str, actor: User | None = None) -> Incident:
        """Inject a measured demo disruption into the digital twin."""
        simulation = self.active_simulation()
        details: dict[str, object] = {}
        target_type = "organization"
        target_id: uuid.UUID | None = None
        if incident_type == "node_failure":
            node = next(
                (
                    item
                    for item in self._all(Node)
                    if item.status == "ready" and item.allocated_gpus > 0
                ),
                next((item for item in self._all(Node) if item.status == "ready"), None),
            )
            if node is None:
                raise ValueError("No healthy node is available to fail")
            target_type = "node"
            target_id = node.id
            affected = [
                item
                for item in self._all(Workload)
                if item.node_id == node.id and item.status == WorkloadStatus.RUNNING.value
            ]
            for workload in affected:
                checkpoint = self.session.scalar(
                    select(Checkpoint)
                    .where(
                        Checkpoint.workload_id == workload.id,
                        Checkpoint.valid.is_(True),
                    )
                    .order_by(Checkpoint.minute.desc())
                )
                if checkpoint:
                    workload.remaining_minutes = checkpoint.remaining_minutes
                workload.status = WorkloadStatus.QUEUED.value
                workload.node_id = None
                workload.cluster_id = None
            details = {
                "node": node.name,
                "affected_workloads": len(affected),
                "recovered_from_checkpoint": sum(
                    workload.checkpointable for workload in affected
                ),
            }
            node.status = "failed"
            node.allocated_gpus = 0
        elif incident_type == "demand_spike":
            teams = self._all(Team)
            for index in range(36):
                self.session.add(
                    Workload(
                        organization_id=self.organization_id,
                        team_id=teams[index % len(teams)].id,
                        name=f"Demand spike urgent inference #{index + 1}",
                        workload_type="real_time_inference",
                        status=WorkloadStatus.QUEUED.value,
                        priority=55 + (index % 5) * 10,
                        requested_gpus=1 if index % 4 else 2,
                        min_gpu_memory_gb=24,
                        duration_minutes=25 + index * 2,
                        remaining_minutes=25 + index * 2,
                        arrival_minute=simulation.current_minute,
                        deadline_minute=simulation.current_minute + 45 + index * 2,
                        preemptible=False,
                        checkpointable=False,
                        constraints={"source": "incident"},
                    )
                )
            details = {
                "new_workloads": 36,
                "priority_range": [55, 95],
                "requested_gpus": [1, 2],
            }
        elif incident_type == "cost_spike":
            profiles = self._all(GPUProfile)
            prior = {profile.name: profile.hourly_cost for profile in profiles}
            for profile in profiles:
                profile.hourly_cost = round(profile.hourly_cost * 1.45, 2)
            details = {"multiplier": 1.45, "prior_hourly_cost": prior}
        elif incident_type == "urgent_workload":
            team = self._all(Team)[1]
            workload = Workload(
                organization_id=self.organization_id,
                team_id=team.id,
                name="Executive priority model validation",
                workload_type="fine_tuning",
                status=WorkloadStatus.QUEUED.value,
                priority=100,
                requested_gpus=4,
                min_gpu_memory_gb=80,
                duration_minutes=75,
                remaining_minutes=75,
                arrival_minute=simulation.current_minute,
                deadline_minute=simulation.current_minute + 90,
                preemptible=False,
                checkpointable=True,
                constraints={"source": "incident"},
            )
            self.session.add(workload)
            self.session.flush()
            target_type = "workload"
            target_id = workload.id
            details = {"priority": 100, "deadline_minutes": 90}
        else:
            raise ValueError("Unsupported incident type")
        incident = Incident(
            organization_id=self.organization_id,
            incident_type=incident_type,
            severity="critical" if incident_type == "node_failure" else "high",
            title=incident_type.replace("_", " ").title(),
            target_type=target_type,
            target_id=target_id,
            detected_minute=simulation.current_minute,
            details=details,
        )
        self.session.add(incident)
        audit(
            self.session,
            self.organization_id,
            actor=actor,
            action="simulation.incident.injected",
            target_type=target_type,
            target_id=str(target_id) if target_id else None,
            details={"incident_type": incident_type, **details},
        )
        self.session.flush()
        self.refresh_intelligence()
        self.session.commit()
        publish_event(
            self.organization_id,
            "incident.injected",
            {
                "incident_id": str(incident.id),
                "incident_type": incident.incident_type,
                "severity": incident.severity,
            },
        )
        return incident

    def recover(self, incident: Incident, actor: User) -> Incident:
        """Restore a failed target and trigger checkpoint-aware replanning."""
        if incident.incident_type == "node_failure" and incident.target_id:
            node = self.get_entity(Node, incident.target_id)
            if node:
                node.status = "ready"
                node.temperature_c = 40
        elif incident.incident_type == "cost_spike":
            canonical_costs = {
                "NVIDIA H100 80GB": 4.75,
                "NVIDIA A100 80GB": 3.25,
                "NVIDIA L40S 48GB": 1.95,
            }
            for profile in self._all(GPUProfile):
                if profile.name in canonical_costs:
                    profile.hourly_cost = canonical_costs[profile.name]
        incident.status = "resolved"
        incident.recovered_minute = self.active_simulation().current_minute
        self._schedule(self.active_simulation())
        audit(
            self.session,
            self.organization_id,
            actor=actor,
            action="incident.recovered",
            target_type="incident",
            target_id=str(incident.id),
            details={"recovered_minute": incident.recovered_minute},
        )
        self.session.commit()
        publish_event(
            self.organization_id,
            "incident.recovered",
            {
                "incident_id": str(incident.id),
                "incident_type": incident.incident_type,
            },
        )
        return incident

    def run_experiment(
        self,
        *,
        name: str,
        schedulers: list[str],
        seed: int,
        scenario: dict[str, object],
    ) -> Experiment:
        """Compare schedulers on the same current queue and capacity snapshot."""
        simulation = self.active_simulation()
        jobs, capacities = self._planner_inputs(
            simulation.current_minute,
            full_ready_capacity=True,
            include_running=True,
        )
        results: list[dict[str, object]] = []
        for strategy in schedulers:
            if strategy == "arva_optimizer":
                actions, status = cp_sat_plan(jobs, capacities)
            else:
                actions = heuristic_plan(jobs, capacities, strategy)
                status = "heuristic"
            metrics = score_plan(actions, jobs, capacities)
            composite = (
                metrics["jobs_placed"] * 15
                + metrics["deadline_success"] * 50
                + metrics["priority_coverage"] * 55
                + metrics["team_fairness"] * 15
                + metrics["queue_reduction"] * 0.04
                - metrics["estimated_cost"] * 0.25
                - metrics["energy_kwh"] * 0.15
            )
            results.append(
                {
                    "scheduler": strategy,
                    "solver_status": status,
                    "score": round(composite, 3),
                    **metrics,
                }
            )
        winner = max(results, key=lambda row: float(row["score"]))["scheduler"]
        experiment = Experiment(
            organization_id=self.organization_id,
            name=name,
            status="completed",
            seed=seed,
            scenario={
                "source_minute": simulation.current_minute,
                "queued_jobs": len(jobs),
                "available_nodes": len(capacities),
                "capacity_model": "full_ready_fleet_replay",
                "demand_model": "running_and_queued_workloads",
                **scenario,
            },
            schedulers=schedulers,
            results=results,
            winner=str(winner),
        )
        self.session.add(experiment)
        self.session.commit()
        publish_event(
            self.organization_id,
            "experiment.completed",
            {
                "experiment_id": str(experiment.id),
                "winner": experiment.winner,
            },
        )
        return experiment

    def metric_series(
        self,
        *,
        metric: str,
        limit: int = 120,
    ) -> list[dict[str, float | int]]:
        """Return one bounded real series for frontend charts."""
        samples = list(
            reversed(
                self.session.scalars(
                    select(MetricSample)
                    .where(MetricSample.organization_id == self.organization_id)
                    .order_by(MetricSample.minute.desc())
                    .limit(max(1, min(limit, 1000)))
                ).all()
            )
        )
        return [
            {"minute": sample.minute, "value": float(sample.values.get(metric, 0))}
            for sample in samples
        ]
