"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  Cpu,
  Database,
  Gauge,
  MapPin,
  RefreshCw,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { AppShell } from "@/components/app-shell";
import { getPlatformData } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

interface ClusterDetailData {
  id: string;
  name: string;
  region: string;
  provider: string;
  status: string;
  carbon_intensity: number;
  power_limit_kw: number;
  nodes: Array<{
    id: string;
    name: string;
    status: string;
    gpu_count: number;
    allocated_gpus: number;
    temperature_c: number;
    memory_gb: number;
  }>;
}

export function ClusterDetail({ clusterId }: { clusterId: string }) {
  const router = useRouter();
  const { token, user, hydrated, hydrate } = useAuthStore();

  useEffect(() => hydrate(), [hydrate]);
  useEffect(() => {
    if (hydrated && !token) router.replace("/login");
  }, [hydrated, router, token]);

  const query = useQuery({
    queryKey: ["cluster", clusterId, token],
    queryFn: () =>
      getPlatformData<ClusterDetailData>(`/clusters/${clusterId}`, token as string),
    enabled: Boolean(token),
  });

  if (!hydrated || !user || !token) {
    return (
      <main className="dashboard-loading">
        <span className="brand-mark">A</span>
        <div className="session-loader" aria-hidden="true">
          <i />
          <i />
          <i />
        </div>
        <p>Loading cluster…</p>
      </main>
    );
  }

  return (
    <AppShell user={user}>
      <main className="ops-page">
        <Link className="back-link" href="/infrastructure">
          <ArrowLeft size={15} /> All clusters
        </Link>
        {query.isLoading ? (
          <section
            className="node-card-grid node-card-skeletons"
            aria-label="Loading cluster nodes"
          >
            {Array.from({ length: 6 }, (_, index) => (
              <article className="node-card skeleton-card" key={index}>
                <span />
                <strong />
                <small />
              </article>
            ))}
          </section>
        ) : query.data ? (
          <>
            <section className="ops-hero cluster-hero">
              <div>
                <span className="eyebrow">Cluster detail / {query.data.status}</span>
                <h1>{query.data.name}</h1>
                <p>
                  {query.data.provider} capacity in {query.data.region}, bounded by a{" "}
                  {query.data.power_limit_kw} kW simulated power envelope.
                </p>
              </div>
              <div className="cluster-facts">
                <span>
                  <MapPin size={16} /> {query.data.region}
                </span>
                <span>
                  <Database size={16} /> {query.data.nodes.length} nodes
                </span>
                <span>
                  <Gauge size={16} /> {query.data.carbon_intensity} gCO₂/kWh
                </span>
              </div>
            </section>
            <section className="node-card-grid">
              {query.data.nodes.map((node) => {
                const utilization = Math.round(
                  (100 * node.allocated_gpus) / Math.max(node.gpu_count, 1),
                );
                return (
                  <article className="node-card" key={node.id}>
                    <div>
                      <span className={`data-pill tone-${node.status === "ready" ? "success" : "danger"}`}>
                        {node.status}
                      </span>
                      <Cpu size={19} />
                    </div>
                    <h2>{node.name}</h2>
                    <p>
                      {node.allocated_gpus}/{node.gpu_count} GPUs allocated ·{" "}
                      {node.temperature_c}°C
                    </p>
                    <div className="capacity-bar">
                      <i style={{ width: `${utilization}%` }} />
                    </div>
                    <small>{utilization}% accelerator utilization</small>
                  </article>
                );
              })}
            </section>
          </>
        ) : (
          <div className="ops-error" role="alert">
            <AlertTriangle size={20} />
            <div>
              <strong>The cluster could not be loaded</strong>
              <p>Check the API connection and retry this request.</p>
            </div>
            <button type="button" onClick={() => void query.refetch()}>
              <RefreshCw size={14} /> Retry
            </button>
          </div>
        )}
      </main>
    </AppShell>
  );
}
