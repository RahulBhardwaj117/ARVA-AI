"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Bot,
  CheckCircle2,
  CircleDollarSign,
  Clock3,
  Cpu,
  Gauge,
  Leaf,
  Play,
  RefreshCw,
  Server,
  ShieldCheck,
  Sparkles,
  Square,
  StepForward,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { AppShell } from "@/components/app-shell";
import {
  ApiError,
  getPlatformData,
  patchPlatformAction,
  postPlatformAction,
} from "@/lib/api";
import { useLiveUpdates } from "@/lib/use-live-updates";
import { useAuthStore } from "@/stores/auth";

export type ControlPageKind =
  | "dashboard"
  | "infrastructure"
  | "nodes"
  | "workloads"
  | "forecasting"
  | "risks"
  | "decisions"
  | "simulation"
  | "experiments"
  | "replay"
  | "policies"
  | "models"
  | "audit"
  | "settings";

type DataRecord = Record<string, unknown>;

interface Summary {
  simulation: DataRecord;
  clusters: number;
  nodes: number;
  healthy_nodes: number;
  failed_nodes: number;
  gpu_capacity: number;
  allocated_gpus: number;
  gpu_utilization: number;
  workloads: {
    total: number;
    queued: number;
    running: number;
    completed: number;
    failed: number;
  };
  cost: number;
  energy_kwh: number;
  sla_success: number;
  open_risks: number;
  critical_risks: number;
  active_incidents: number;
  recent_decisions: DataRecord[];
}

const pageConfig: Record<
  ControlPageKind,
  {
    eyebrow: string;
    title: string;
    description: string;
    primary: string;
    secondary?: string;
  }
> = {
  dashboard: {
    eyebrow: "Command center",
    title: "Autonomous operations, made legible.",
    description:
      "Observe the twin, anticipate pressure, compare responses, and govern every action from one operational view.",
    primary: "/metrics/summary",
    secondary: "/metrics/series?metric=gpu_utilization",
  },
  infrastructure: {
    eyebrow: "Infrastructure",
    title: "Three clusters. One decision plane.",
    description:
      "Capacity, health, regional efficiency, and placement headroom across the complete simulated fleet.",
    primary: "/clusters",
    secondary: "/nodes",
  },
  nodes: {
    eyebrow: "Node explorer",
    title: "Inspect every accelerator boundary.",
    description:
      "Live allocation, thermals, hardware profiles, labels, and failure state for all fifteen nodes.",
    primary: "/nodes",
    secondary: "/gpu-profiles",
  },
  workloads: {
    eyebrow: "Workload lifecycle",
    title: "Demand, placement, and progress.",
    description:
      "Track arrivals through queueing, execution, checkpointing, recovery, and completion.",
    primary: "/workloads",
    secondary: "/teams",
  },
  forecasting: {
    eyebrow: "Predictive intelligence",
    title: "See pressure before it arrives.",
    description:
      "Forecast utilization, queue depth, spend, and reliability with transparent model provenance and uncertainty.",
    primary: "/forecasts",
    secondary: "/metrics/series?metric=queue_depth",
  },
  risks: {
    eyebrow: "Risk center",
    title: "Turn uncertainty into an actionable horizon.",
    description:
      "Capacity, queue, SLA, cost, energy, and reliability risks with evidence, probability, and a recommended response.",
    primary: "/risks",
    secondary: "/forecasts",
  },
  decisions: {
    eyebrow: "Decision intelligence",
    title: "Compare futures. Select the governed one.",
    description:
      "Every recommendation records alternatives, constraints, objectives, confidence, rationale, and execution state.",
    primary: "/decisions",
    secondary: "/optimization/plans",
  },
  simulation: {
    eyebrow: "Digital twin",
    title: "Control time. Test the unexpected.",
    description:
      "Start, pause, step, accelerate, reset, and inject repeatable disruptions into the persistent environment.",
    primary: "/simulation",
    secondary: "/incidents",
  },
  experiments: {
    eyebrow: "Experiments",
    title: "Benchmark decisions on identical state.",
    description:
      "Compare baseline schedulers and the CP-SAT optimizer using measured throughput, cost, energy, queue, and SLA outcomes.",
    primary: "/experiments",
    secondary: "/metrics/summary",
  },
  replay: {
    eyebrow: "Decision replay",
    title: "Reconstruct what happened and why.",
    description:
      "Review incidents, generated decisions, policy transitions, and outcomes as one evidence trail.",
    primary: "/audit",
    secondary: "/decisions",
  },
  policies: {
    eyebrow: "Policy governance",
    title: "Define the safe operating envelope.",
    description:
      "Versioned cost, energy, SLA, preemption, approval, and autonomy guardrails govern every candidate plan.",
    primary: "/policies",
    secondary: "/optimization/plans",
  },
  models: {
    eyebrow: "Model monitoring",
    title: "Transparent predictions, dependable fallbacks.",
    description:
      "Monitor active forecast tasks, algorithms, feature contracts, confidence, and current evaluation evidence.",
    primary: "/models",
    secondary: "/forecasts",
  },
  audit: {
    eyebrow: "Audit log",
    title: "Every material action leaves evidence.",
    description:
      "Organization-scoped actor, action, target, outcome, timestamp, and contextual details.",
    primary: "/audit",
  },
  settings: {
    eyebrow: "Control-plane settings",
    title: "Choose how ARVA is allowed to act.",
    description:
      "Move safely from simulation to recommendations, approval gates, or controlled autonomy.",
    primary: "/settings",
  },
};

const tableFields: Record<ControlPageKind, Array<[string, string]>> = {
  dashboard: [],
  infrastructure: [
    ["name", "Cluster"],
    ["region", "Region"],
    ["provider", "Provider"],
    ["status", "Health"],
    ["carbon_intensity", "Carbon gCO₂/kWh"],
    ["power_limit_kw", "Power limit kW"],
  ],
  nodes: [
    ["name", "Node"],
    ["status", "State"],
    ["gpu_count", "GPUs"],
    ["allocated_gpus", "Allocated"],
    ["temperature_c", "Temp °C"],
    ["memory_gb", "Memory GB"],
  ],
  workloads: [
    ["name", "Workload"],
    ["workload_type", "Type"],
    ["status", "State"],
    ["priority", "Priority"],
    ["requested_gpus", "GPUs"],
    ["remaining_minutes", "Remaining"],
    ["cost_accrued", "Cost"],
  ],
  forecasting: [
    ["metric", "Metric"],
    ["prediction", "Prediction"],
    ["lower_bound", "Lower"],
    ["upper_bound", "Upper"],
    ["confidence", "Confidence"],
    ["model_name", "Model"],
  ],
  risks: [
    ["severity", "Severity"],
    ["risk_type", "Type"],
    ["title", "Risk"],
    ["probability", "Probability"],
    ["horizon_minutes", "Horizon"],
    ["status", "State"],
  ],
  decisions: [
    ["title", "Decision"],
    ["status", "State"],
    ["action_type", "Action"],
    ["confidence", "Confidence"],
    ["requires_approval", "Approval"],
    ["created_at", "Created"],
  ],
  simulation: [
    ["incident_type", "Incident"],
    ["severity", "Severity"],
    ["status", "State"],
    ["title", "Title"],
    ["detected_minute", "Detected"],
    ["recovered_minute", "Recovered"],
  ],
  experiments: [
    ["name", "Experiment"],
    ["status", "State"],
    ["winner", "Winner"],
    ["seed", "Seed"],
    ["created_at", "Created"],
  ],
  replay: [
    ["created_at", "Timestamp"],
    ["actor_email", "Actor"],
    ["action", "Action"],
    ["target_type", "Target"],
    ["outcome", "Outcome"],
  ],
  policies: [
    ["name", "Policy"],
    ["version", "Version"],
    ["preset", "Preset"],
    ["is_active", "Active"],
    ["description", "Description"],
  ],
  models: [
    ["name", "Model"],
    ["task", "Task"],
    ["algorithm", "Algorithm"],
    ["version", "Version"],
    ["status", "State"],
    ["updated_at", "Updated"],
  ],
  audit: [
    ["created_at", "Timestamp"],
    ["actor_email", "Actor"],
    ["action", "Action"],
    ["target_type", "Target"],
    ["target_id", "Target ID"],
    ["outcome", "Outcome"],
  ],
  settings: [],
};

function asRecords(value: unknown): DataRecord[] {
  return Array.isArray(value)
    ? value.filter(
        (item): item is DataRecord =>
          typeof item === "object" && item !== null,
      )
    : [];
}

function display(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") {
    return Number.isInteger(value)
      ? value.toLocaleString()
      : value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  if (typeof value === "string") {
    if (/^\d{4}-\d{2}-\d{2}T/.test(value)) {
      return new Date(value).toLocaleString();
    }
    return value.replaceAll("_", " ");
  }
  return JSON.stringify(value);
}

function tone(value: unknown): string {
  const normalized = String(value).toLowerCase();
  if (["critical", "failed", "rejected", "open"].includes(normalized)) {
    return "danger";
  }
  if (["high", "pending", "queued", "pending approval"].includes(normalized)) {
    return "warning";
  }
  if (
    ["healthy", "ready", "running", "completed", "active", "executed", "resolved"].includes(
      normalized,
    )
  ) {
    return "success";
  }
  return "neutral";
}

function DataTable({
  kind,
  records,
}: {
  kind: ControlPageKind;
  records: DataRecord[];
}) {
  const fields = tableFields[kind];
  if (!records.length) {
    return (
      <div className="empty-state">
        <Sparkles size={22} />
        <strong>No records yet</strong>
        <p>Run the simulation or the page action to produce backed results.</p>
      </div>
    );
  }
  return (
    <div className="data-table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {fields.map(([, label]) => (
              <th key={label}>{label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {records.map((record, index) => (
            <tr key={String(record.id ?? index)}>
              {fields.map(([field], fieldIndex) => {
                const value = record[field];
                const content =
                  kind === "infrastructure" && field === "name" && record.id ? (
                    <Link
                      className="table-link"
                      href={`/infrastructure/${String(record.id)}`}
                    >
                      {display(value)} <ArrowRight size={13} />
                    </Link>
                  ) : (
                    display(value)
                  );
                return (
                  <td key={field}>
                    {fieldIndex === 0 ||
                    ["status", "severity", "is_active", "outcome"].includes(field) ? (
                      <span className={`data-pill tone-${tone(value)}`}>
                        {content}
                      </span>
                    ) : (
                      content
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Kpi({
  label,
  value,
  detail,
  icon: Icon,
  accent = "cyan",
}: {
  label: string;
  value: string;
  detail: string;
  icon: typeof Gauge;
  accent?: "cyan" | "acid" | "orange";
}) {
  return (
    <article className={`ops-kpi accent-${accent}`}>
      <div>
        <span>{label}</span>
        <Icon size={18} />
      </div>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function PlatformSkeleton() {
  return (
    <section className="ops-skeleton" aria-label="Loading verified platform state">
      <div className="skeleton-line skeleton-line-short" />
      <div className="skeleton-line skeleton-line-title" />
      <div className="skeleton-line skeleton-line-copy" />
      <div className="skeleton-card-grid" aria-hidden="true">
        {Array.from({ length: 4 }, (_, index) => (
          <div className="skeleton-card" key={index}>
            <span />
            <strong />
            <small />
          </div>
        ))}
      </div>
      <span className="sr-only">Loading verified platform state</span>
    </section>
  );
}

export function ControlPage({ kind }: { kind: ControlPageKind }) {
  const config = pageConfig[kind];
  const router = useRouter();
  const queryClient = useQueryClient();
  const { token, user, hydrated, hydrate, clearSession } = useAuthStore();
  const [notice, setNotice] = useState<{
    tone: "success" | "error";
    message: string;
  } | null>(null);
  const liveState = useLiveUpdates(kind, token);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (hydrated && !token) router.replace("/login");
  }, [hydrated, router, token]);

  const primary = useQuery({
    queryKey: ["control", config.primary, token],
    queryFn: () => getPlatformData<unknown>(config.primary, token as string),
    enabled: Boolean(token),
    refetchInterval: kind === "dashboard" || kind === "simulation" ? 5_000 : 20_000,
  });
  const secondary = useQuery({
    queryKey: ["control", config.secondary, token],
    queryFn: () =>
      getPlatformData<unknown>(config.secondary as string, token as string),
    enabled: Boolean(token && config.secondary),
    refetchInterval: kind === "dashboard" ? 5_000 : 30_000,
  });

  useEffect(() => {
    if (
      primary.error instanceof ApiError &&
      [401, 403].includes(primary.error.status)
    ) {
      clearSession();
      router.replace("/login");
    }
  }, [clearSession, primary.error, router]);

  const action = useMutation({
    mutationFn: async ({
      path,
      body,
      method = "post",
    }: {
      path: string;
      body?: Record<string, unknown>;
      method?: "post" | "patch";
    }) =>
      method === "patch"
        ? patchPlatformAction<unknown>(path, token as string, body)
        : postPlatformAction<unknown>(path, token as string, body),
    onSuccess: async () => {
      setNotice({
        tone: "success",
        message: "Action completed and the control plane has refreshed.",
      });
      await queryClient.invalidateQueries({ queryKey: ["control"] });
    },
    onError: (error) => {
      setNotice({
        tone: "error",
        message: error instanceof Error ? error.message : "The action failed.",
      });
    },
  });

  const primaryRecords = useMemo(() => asRecords(primary.data), [primary.data]);
  const secondaryRecords = useMemo(
    () => asRecords(secondary.data),
    [secondary.data],
  );

  if (!hydrated || !token || !user) {
    return (
      <main className="dashboard-loading">
        <span className="brand-mark">A</span>
        <div className="session-loader" aria-hidden="true">
          <i />
          <i />
          <i />
        </div>
        <p>Establishing the governed session…</p>
      </main>
    );
  }

  const summary =
    kind === "dashboard" && primary.data && !Array.isArray(primary.data)
      ? (primary.data as Summary)
      : kind === "simulation" && primary.data && !Array.isArray(primary.data)
        ? (primary.data as Summary)
        : null;
  const settings =
    kind === "settings" && primary.data && !Array.isArray(primary.data)
      ? (primary.data as DataRecord)
      : null;
  const isBusy = primary.isLoading || action.isPending;

  function renderActions() {
    if (kind === "forecasting") {
      return (
        <button
          className="ops-action primary"
          disabled={action.isPending}
          onClick={() => action.mutate({ path: "/forecasts/run" })}
        >
          <Bot size={16} /> Run forecast pipeline
        </button>
      );
    }
    if (kind === "decisions") {
      return (
        <button
          className="ops-action primary"
          disabled={action.isPending}
          onClick={() => action.mutate({ path: "/optimization/generate" })}
        >
          <Sparkles size={16} /> Generate alternatives
        </button>
      );
    }
    if (kind === "experiments") {
      return (
        <button
          className="ops-action primary"
          disabled={action.isPending}
          onClick={() =>
            action.mutate({
              path: "/experiments",
              body: { name: `Twin benchmark ${new Date().toLocaleTimeString()}` },
            })
          }
        >
          <Play size={16} /> Run scheduler benchmark
        </button>
      );
    }
    if (kind === "workloads") {
      const team = secondaryRecords[0];
      return (
        <button
          className="ops-action primary"
          disabled={!team || action.isPending}
          onClick={() =>
            action.mutate({
              path: "/workloads",
              body: {
                name: "Interactive fine-tuning request",
                workload_type: "fine_tuning",
                team_id: team?.id,
                requested_gpus: 2,
                min_gpu_memory_gb: 48,
                duration_minutes: 90,
                priority: 80,
              },
            })
          }
        >
          <Zap size={16} /> Submit workload
        </button>
      );
    }
    if (kind === "dashboard") {
      return (
        <button
          className="ops-action primary"
          disabled={action.isPending}
          onClick={() =>
            action.mutate({ path: "/simulation/tick?minutes=10" })
          }
        >
          <StepForward size={16} /> Advance 10 minutes
        </button>
      );
    }
    return null;
  }

  return (
    <AppShell user={user}>
      <main
        className="ops-page"
        aria-busy={primary.isLoading || action.isPending}
      >
        <section className="ops-hero">
          <div>
            <span className="eyebrow">{config.eyebrow}</span>
            <h1>{config.title}</h1>
            <p>{config.description}</p>
          </div>
          <div className="ops-hero-actions">
            <span className={`stream-status ${liveState}`}>
              <i />
              {liveState === "live" ? "Event stream live" : "Reconnecting"}
            </span>
            {renderActions()}
            <button
              className="ops-action"
              disabled={primary.isFetching || action.isPending}
              onClick={() => {
                void primary.refetch();
                void secondary.refetch();
              }}
            >
              <RefreshCw size={15} /> Refresh
            </button>
          </div>
        </section>

        {notice ? (
          <div
            className={`ops-notice ${notice.tone}`}
            role={notice.tone === "error" ? "alert" : "status"}
          >
            {notice.tone === "error" ? (
              <AlertTriangle size={17} />
            ) : (
              <CheckCircle2 size={17} />
            )}
            <span>{notice.message}</span>
            <button type="button" onClick={() => setNotice(null)}>
              Dismiss
            </button>
          </div>
        ) : null}

        {primary.error ? (
          <div className="ops-error" role="alert">
            <AlertTriangle size={20} />
            <div>
              <strong>Operational data is unavailable</strong>
              <p>
                {primary.error instanceof Error
                  ? primary.error.message
                  : "Verify the API and retry."}
              </p>
            </div>
            <button onClick={() => void primary.refetch()}>Retry</button>
          </div>
        ) : null}

        {isBusy && !primary.data ? (
          <PlatformSkeleton />
        ) : null}

        {summary ? (
          <>
            <section className="ops-kpi-grid">
              <Kpi
                label="GPU utilization"
                value={`${summary.gpu_utilization}%`}
                detail={`${summary.allocated_gpus} / ${summary.gpu_capacity} GPUs allocated`}
                icon={Gauge}
                accent="acid"
              />
              <Kpi
                label="Queue pressure"
                value={String(summary.workloads.queued)}
                detail={`${summary.workloads.running} running · ${summary.workloads.completed} complete`}
                icon={Clock3}
                accent="cyan"
              />
              <Kpi
                label="SLA success"
                value={`${summary.sla_success}%`}
                detail={`${summary.open_risks} open risks · ${summary.critical_risks} critical`}
                icon={ShieldCheck}
                accent="acid"
              />
              <Kpi
                label="Simulated spend"
                value={`$${summary.cost.toLocaleString()}`}
                detail={`${summary.energy_kwh.toLocaleString()} kWh consumed`}
                icon={CircleDollarSign}
                accent="orange"
              />
            </section>

            {kind === "dashboard" ? (
              <section className="ops-grid-two">
                <article className="ops-panel chart-panel">
                  <div className="panel-title">
                    <div>
                      <span>LIVE TELEMETRY</span>
                      <h2>GPU utilization timeline</h2>
                    </div>
                    <span className="live-badge">
                      <i /> TWIN MINUTE {display(summary.simulation.current_minute)}
                    </span>
                  </div>
                  <div className="ops-chart">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={secondaryRecords}>
                        <CartesianGrid stroke="rgba(255,255,255,.07)" vertical={false} />
                        <XAxis dataKey="minute" stroke="#70857d" fontSize={11} />
                        <YAxis domain={[0, 100]} stroke="#70857d" fontSize={11} />
                        <Tooltip
                          contentStyle={{
                            background: "#12131c",
                            border: "1px solid rgba(139,92,246,.38)",
                            borderRadius: "12px",
                          }}
                        />
                        <Line
                          type="monotone"
                          dataKey="value"
                          stroke="#8b5cf6"
                          strokeWidth={2}
                          dot={false}
                          name="GPU utilization %"
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </article>
                <article className="ops-panel decision-feed">
                  <div className="panel-title">
                    <div>
                      <span>DECISION FEED</span>
                      <h2>Recent governed actions</h2>
                    </div>
                    <Bot size={20} />
                  </div>
                  {summary.recent_decisions.length ? (
                    summary.recent_decisions.map((decision) => (
                      <div className="decision-row" key={String(decision.id)}>
                        <span className={`severity-line tone-${tone(decision.status)}`} />
                        <div>
                          <strong>{display(decision.title)}</strong>
                          <small>{display(decision.rationale)}</small>
                        </div>
                        <span className={`data-pill tone-${tone(decision.status)}`}>
                          {display(decision.status)}
                        </span>
                      </div>
                    ))
                  ) : (
                    <div className="empty-state compact">
                      <Activity size={18} />
                      <p>Advance the twin to generate the first decision.</p>
                    </div>
                  )}
                </article>
              </section>
            ) : null}
          </>
        ) : null}

        {kind === "simulation" && summary ? (
          <section className="simulation-controls">
            <button
              disabled={action.isPending}
              onClick={() =>
                action.mutate({ path: "/simulation/control", body: { action: "start" } })
              }
            >
              <Play size={16} /> Start
            </button>
            <button
              disabled={action.isPending}
              onClick={() =>
                action.mutate({ path: "/simulation/control", body: { action: "pause" } })
              }
            >
              <Square size={15} /> Pause
            </button>
            <button
              disabled={action.isPending}
              onClick={() =>
                action.mutate({ path: "/simulation/control", body: { action: "step" } })
              }
            >
              <StepForward size={16} /> Step
            </button>
            <button
              disabled={action.isPending}
              onClick={() =>
                action.mutate({
                  path: "/simulation/control",
                  body: { action: "speed", speed: 8 },
                })
              }
            >
              <Zap size={16} /> 8× speed
            </button>
            <button
              disabled={action.isPending}
              onClick={() =>
                action.mutate({ path: "/simulation/control", body: { action: "reset" } })
              }
            >
              <RefreshCw size={16} /> Reset
            </button>
            <span className="control-divider" />
            {["demand_spike", "urgent_workload", "cost_spike", "node_failure"].map(
              (incident) => (
                <button
                  className="incident-action"
                  disabled={action.isPending}
                  key={incident}
                  onClick={() =>
                    action.mutate({
                      path: "/simulation/incidents",
                      body: { incident_type: incident },
                    })
                  }
                >
                  <AlertTriangle size={15} /> {incident.replaceAll("_", " ")}
                </button>
              ),
            )}
          </section>
        ) : null}

        {kind === "settings" && settings ? (
          <section className="settings-grid">
            {(
              (settings.available_deployment_modes as string[] | undefined) ?? []
            ).map((mode) => {
              const organization = settings.organization as DataRecord;
              const active = organization.deployment_mode === mode;
              return (
                <article className={active ? "active" : ""} key={mode}>
                  <ShieldCheck size={20} />
                  <h2>{mode.replaceAll("_", " ")}</h2>
                  <p>
                    {mode === "simulation"
                      ? "Actions affect only the deterministic digital twin."
                      : mode === "recommendation"
                        ? "ARVA recommends actions without executing them."
                        : mode === "approval"
                          ? "An authorized operator must approve each action."
                          : "Policy-allowlisted low-risk actions may execute automatically."}
                  </p>
                  <button
                    disabled={active || action.isPending}
                    onClick={() =>
                      action.mutate({
                        path: `/settings/deployment-mode?mode=${mode}`,
                        method: "patch",
                      })
                    }
                  >
                    {active ? "Current mode" : "Activate"}
                  </button>
                </article>
              );
            })}
          </section>
        ) : null}

        {!summary && kind !== "settings" && !primary.isLoading ? (
          <section className="ops-panel table-panel">
            <div className="panel-title">
              <div>
                <span>VERIFIED DATA</span>
                <h2>{config.title}</h2>
              </div>
              <span className="record-count">{primaryRecords.length} records</span>
            </div>
            <DataTable kind={kind} records={primaryRecords} />
          </section>
        ) : null}

        {kind === "decisions" && primaryRecords.length ? (
          <section className="record-actions-grid">
            {primaryRecords.slice(0, 6).map((decision) => (
              <article key={String(decision.id)}>
                <div>
                  <span className={`data-pill tone-${tone(decision.status)}`}>
                    {display(decision.status)}
                  </span>
                  <small>{Math.round(Number(decision.confidence ?? 0) * 100)}% confidence</small>
                </div>
                <h2>{display(decision.title)}</h2>
                <p>{display(decision.rationale)}</p>
                <div>
                  {decision.status === "pending_approval" ? (
                    <button
                      disabled={action.isPending}
                      onClick={() =>
                        action.mutate({
                          path: `/decisions/${String(decision.id)}/action`,
                          body: { action: "approve" },
                        })
                      }
                    >
                      <CheckCircle2 size={14} /> Approve
                    </button>
                  ) : null}
                  {["approved", "recommended"].includes(String(decision.status)) ? (
                    <button
                      className="primary"
                      disabled={action.isPending}
                      onClick={() =>
                        action.mutate({
                          path: `/decisions/${String(decision.id)}/action`,
                          body: { action: "execute" },
                        })
                      }
                    >
                      <Play size={14} /> Execute
                    </button>
                  ) : null}
                  {!["executed", "rejected"].includes(String(decision.status)) ? (
                    <button
                      disabled={action.isPending}
                      onClick={() =>
                        action.mutate({
                          path: `/decisions/${String(decision.id)}/action`,
                          body: { action: "reject" },
                        })
                      }
                    >
                      Reject
                    </button>
                  ) : null}
                </div>
              </article>
            ))}
          </section>
        ) : null}

        {kind === "policies" && primaryRecords.length ? (
          <section className="record-actions-grid policies-actions">
            {primaryRecords.map((policy) => (
              <article className={policy.is_active ? "active" : ""} key={String(policy.id)}>
                <div>
                  <span className={`data-pill tone-${policy.is_active ? "success" : "neutral"}`}>
                    {policy.is_active ? "Active policy" : `Version ${display(policy.version)}`}
                  </span>
                </div>
                <h2>{display(policy.name)}</h2>
                <p>{display(policy.description)}</p>
                <pre>{JSON.stringify(policy.rules, null, 2)}</pre>
                <button
                  disabled={Boolean(policy.is_active) || action.isPending}
                  onClick={() =>
                    action.mutate({
                      path: `/policies/${String(policy.id)}/activate`,
                    })
                  }
                >
                  <ShieldCheck size={14} />
                  {policy.is_active ? "Governing decisions" : "Activate policy"}
                </button>
              </article>
            ))}
          </section>
        ) : null}

        {kind === "simulation" && secondaryRecords.length ? (
          <section className="record-actions-grid incident-actions-grid">
            {secondaryRecords.slice(0, 8).map((incident) => (
              <article key={String(incident.id)}>
                <div>
                  <span className={`data-pill tone-${tone(incident.severity)}`}>
                    {display(incident.severity)}
                  </span>
                  <small>Twin minute {display(incident.detected_minute)}</small>
                </div>
                <h2>{display(incident.title)}</h2>
                <p>{display(incident.details)}</p>
                <button
                  disabled={incident.status === "resolved" || action.isPending}
                  onClick={() =>
                    action.mutate({
                      path: `/incidents/${String(incident.id)}/recover`,
                    })
                  }
                >
                  <RefreshCw size={14} />
                  {incident.status === "resolved" ? "Recovered" : "Recover and replan"}
                </button>
              </article>
            ))}
          </section>
        ) : null}

        {kind === "forecasting" && secondaryRecords.length ? (
          <section className="ops-panel chart-panel wide">
            <div className="panel-title">
              <div>
                <span>QUEUE HISTORY</span>
                <h2>Observed pressure before the forecast horizon</h2>
              </div>
              <Leaf size={20} />
            </div>
            <div className="ops-chart">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={secondaryRecords}>
                  <CartesianGrid stroke="rgba(255,255,255,.07)" vertical={false} />
                  <XAxis dataKey="minute" stroke="#70857d" />
                  <YAxis stroke="#70857d" />
                  <Tooltip
                    contentStyle={{
                      background: "#12131c",
                      border: "1px solid rgba(34,211,238,.35)",
                      borderRadius: "12px",
                    }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="value"
                    name="Queue depth"
                    stroke="#45e6c5"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </section>
        ) : null}

        {kind === "experiments" && primaryRecords.length ? (
          <section className="experiment-results">
            {primaryRecords.slice(0, 2).map((experiment) => (
              <article className="ops-panel" key={String(experiment.id)}>
                <div className="panel-title">
                  <div>
                    <span>MEASURED COMPARISON</span>
                    <h2>{display(experiment.name)}</h2>
                  </div>
                  <span className="winner-badge">
                    Winner · {display(experiment.winner)}
                  </span>
                </div>
                <div className="experiment-metrics">
                  {asRecords(experiment.results).map((result) => (
                    <div key={String(result.scheduler)}>
                      <strong>{display(result.scheduler)}</strong>
                      <span>Score {display(result.score)}</span>
                      <small>
                        {display(result.jobs_placed)} placed · $
                        {display(result.estimated_cost)} · {display(result.energy_kwh)} kWh
                      </small>
                    </div>
                  ))}
                </div>
              </article>
            ))}
          </section>
        ) : null}

        <footer className="ops-footer">
          <span>
            <Server size={14} /> Organization scope: {user.organization.name}
          </span>
          <span>
            <Cpu size={14} /> Simulation-first execution boundary
          </span>
          <span>
            <ShieldCheck size={14} /> Policy governed
          </span>
        </footer>
      </main>
    </AppShell>
  );
}
