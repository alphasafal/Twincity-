"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { DataModeBanner } from "@/components/DataModeBanner";
import { EmptyState, PageHeader, Panel } from "@/components/AppShell";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/utils";

type Frame = {
  timestamp?: string;
  zone_temperatures_c?: Record<string, number>;
  occupancy?: Record<string, number | null>;
  weather_outdoor_c?: number;
  current_setpoint_c?: number;
  proposed_setpoint_c?: number | null;
  controller_mode?: string;
  safety_shield_result?: Record<string, unknown> | string;
  executed_action?: string;
  next_simulation_state?: Record<string, unknown> | string;
};

export default function LiveDemoPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["experiment-stream"],
    queryFn: () => api.experimentStream("default", 500),
    refetchInterval: 30_000,
  });
  const frames = (data?.frames || []) as Frame[];
  const [idx, setIdx] = useState(0);
  const [playing, setPlaying] = useState(true);

  // ~3 minute demo: advance so full stream completes in ~180s
  const intervalMs = useMemo(() => {
    if (!frames.length) return 1000;
    return Math.max(200, Math.floor(180_000 / frames.length));
  }, [frames.length]);

  useEffect(() => {
    if (!playing || frames.length === 0) return;
    const t = window.setInterval(() => {
      setIdx((i) => (i + 1) % frames.length);
    }, intervalMs);
    return () => window.clearInterval(t);
  }, [playing, frames.length, intervalMs]);

  const frame = frames[idx];
  const zones = frame?.zone_temperatures_c || {};
  const safety =
    typeof frame?.safety_shield_result === "object"
      ? JSON.stringify(frame?.safety_shield_result)
      : String(frame?.safety_shield_result ?? "—");

  return (
    <div>
      <PageHeader
        title="Live demo stream (playback)"
        description="Accelerated replay of a recorded EnergyPlus control stream — not a live physical building or live BMS."
        actions={
          <div className="flex gap-2">
            <button
              type="button"
              className="rounded border border-border px-3 py-1 text-sm"
              onClick={() => setPlaying((p) => !p)}
            >
              {playing ? "Pause" : "Play"}
            </button>
            <button
              type="button"
              className="rounded border border-border px-3 py-1 text-sm"
              onClick={() => setIdx(0)}
            >
              Restart
            </button>
          </div>
        }
      />
      <DataModeBanner
        dataMode="energyplus"
        dataSourceVisible="Playback of results/agent/stream.json (recorded Path A agent run)"
        syntheticMultiplierApplied={false}
        variant="playback"
      />

      {error ? (
        <EmptyState>
          Stream unavailable — run ./scripts/run_agent.sh to generate stream.json
        </EmptyState>
      ) : null}
      {isLoading ? <EmptyState>Loading stream…</EmptyState> : null}

      {frame ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <Panel className="space-y-2 p-4 font-mono text-sm">
            <div>timestamp: {frame.timestamp}</div>
            <div>weather outdoor: {formatNumber(frame.weather_outdoor_c)} °C</div>
            <div>current setpoint: {formatNumber(frame.current_setpoint_c)} °C</div>
            <div>proposed setpoint: {formatNumber(frame.proposed_setpoint_c)} °C</div>
            <div>controller: {frame.controller_mode}</div>
            <div>SafetyShield: {safety}</div>
            <div>executed: {frame.executed_action}</div>
            <div>
              next state:{" "}
              {typeof frame.next_simulation_state === "object"
                ? JSON.stringify(frame.next_simulation_state)
                : String(frame.next_simulation_state)}
            </div>
            <div className="pt-2 text-muted">
              frame {idx + 1}/{frames.length} · step {intervalMs}ms
            </div>
          </Panel>
          <Panel className="p-4">
            <h2 className="mb-3 text-sm font-semibold">Zone temperatures / occupancy</h2>
            <div className="space-y-2">
              {Object.entries(zones).map(([z, t]) => (
                <div key={z} className="flex justify-between border-b border-border/60 py-1 text-sm">
                  <span>{z}</span>
                  <span>
                    {formatNumber(t)} °C · occ {formatNumber(frame.occupancy?.[z] ?? 0, 0)}
                  </span>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      ) : null}
    </div>
  );
}
