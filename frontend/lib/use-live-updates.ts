"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { API_BASE_URL } from "@/lib/api";

const channelByPage: Record<string, string> = {
  dashboard: "telemetry",
  infrastructure: "telemetry",
  nodes: "telemetry",
  workloads: "telemetry",
  forecasting: "metrics",
  risks: "risks",
  decisions: "decisions",
  simulation: "simulation",
  experiments: "experiments",
  replay: "decisions",
  policies: "decisions",
  models: "metrics",
  audit: "decisions",
  settings: "telemetry",
};

export type LiveConnectionState = "connecting" | "live" | "reconnecting";

export function useLiveUpdates(page: string, token: string | null) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<LiveConnectionState>("connecting");

  useEffect(() => {
    if (!token || typeof WebSocket === "undefined") return;

    const accessToken = token;
    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let stopped = false;
    let retries = 0;
    const channel = channelByPage[page] ?? "telemetry";
    const wsBaseUrl = API_BASE_URL.replace(/^http/, "ws");

    function connect() {
      if (stopped) return;
      setState(retries ? "reconnecting" : "connecting");
      socket = new WebSocket(
        `${wsBaseUrl}/ws/${channel}?token=${encodeURIComponent(accessToken)}`,
      );

      socket.onopen = () => {
        retries = 0;
        setState("live");
      };
      socket.onmessage = (message) => {
        try {
          const payload = JSON.parse(String(message.data)) as { type?: string };
          if (payload.type === "event") {
            void queryClient.invalidateQueries({ queryKey: ["control"] });
          }
        } catch {
          // A malformed live message must not break the REST polling fallback.
        }
      };
      socket.onclose = () => {
        if (stopped) return;
        retries += 1;
        setState("reconnecting");
        retryTimer = setTimeout(connect, Math.min(1_000 * 2 ** retries, 15_000));
      };
      socket.onerror = () => socket?.close();
    }

    connect();
    return () => {
      stopped = true;
      if (retryTimer) clearTimeout(retryTimer);
      socket?.close();
    };
  }, [page, queryClient, token]);

  return state;
}
