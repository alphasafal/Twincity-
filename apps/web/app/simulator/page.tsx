"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { EmptyState, PageHeader, Panel, SimulatedBadge } from "@/components/AppShell";
import { SimulationControls } from "@/components/SimulationControls";
import { api } from "@/lib/api";
import { useBuildingId, useLiveBuilding } from "@/lib/hooks";
import { formatNumber } from "@/lib/utils";

export default function SimulatorPage() {
  const buildingId = useBuildingId();
  const queryClient = useQueryClient();
  const { data: status } = useLiveBuilding(buildingId);
  const [speed, setSpeed] = useState(4);
  const [whatIf, setWhatIf] = useState({
    outdoor_temperature: 34,
    occupancy_level: 1.2,
    energy_saving_target: 15,
  });
  const [whatIfResult, setWhatIfResult] = useState<Record<string, unknown> | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const scenarios = useQuery({
    queryKey: ["demo-scenarios"],
    queryFn: () => api.demoScenarios(),
  });

  const playback = useMutation({
    mutationFn: (action: "pause" | "resume" | "step" | "reset") =>
      api.demoPlayback(action),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["building-status", buildingId] }),
  });

  const speedMut = useMutation({
    mutationFn: (value: number) => api.demoSpeed(value),
    onSuccess: (_, value) => setSpeed(value),
  });

  const startScenario = useMutation({
    mutationFn: (id: string) => api.startScenario(id),
    onSuccess: (res) => {
      setMessage(`Scenario started: ${JSON.stringify(res).slice(0, 120)}`);
      void queryClient.invalidateQueries({ queryKey: ["building-status", buildingId] });
    },
    onError: (err) => setMessage(err instanceof Error ? err.message : "Failed"),
  });

  const reset = useMutation({
    mutationFn: () => api.resetScenarios(),
    onSuccess: () => {
      setMessage("Demo reset complete.");
      void queryClient.invalidateQueries({ queryKey: ["building-status", buildingId] });
    },
  });

  const runWhatIf = useMutation({
    mutationFn: () => api.whatIf(buildingId!, whatIf),
    onSuccess: (res) => {
      setWhatIfResult(res);
      setMessage(String(res.label || "What-if complete"));
    },
    onError: (err) => setMessage(err instanceof Error ? err.message : "What-if failed"),
  });

  return (
    <div>
      <PageHeader
        title="Simulator"
        description="Demo scenarios, playback, and what-if exploration against the twin."
        actions={<SimulatedBadge label="All results simulated" />}
      />

      <div className="grid gap-4 xl:grid-cols-2">
        <SimulationControls
          speed={speed}
          busy={playback.isPending || speedMut.isPending}
          onSpeed={(v) => speedMut.mutate(v)}
          onPlayback={(a) => playback.mutate(a)}
        />

        <Panel className="p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Demo scenarios</h2>
            <button
              type="button"
              disabled={reset.isPending}
              onClick={() => reset.mutate()}
              className="rounded border border-border px-2 py-1 text-xs text-muted hover:text-foreground"
            >
              Reset demo
            </button>
          </div>
          {scenarios.isLoading ? <EmptyState>Loading scenarios…</EmptyState> : null}
          <div className="grid gap-2 sm:grid-cols-2">
            {(scenarios.data || []).map((s) => (
              <button
                key={s.id}
                type="button"
                disabled={startScenario.isPending}
                onClick={() => startScenario.mutate(s.id)}
                className="rounded-md border border-border bg-background/50 px-3 py-2 text-left text-sm hover:border-live/40 disabled:opacity-50"
              >
                <div className="font-medium">{s.name}</div>
                <div className="font-mono text-[10px] text-muted">{s.id}</div>
              </button>
            ))}
          </div>
          <p className="mt-3 text-xs text-muted">
            Active: {status?.active_scenario || "none"} · Load{" "}
            {formatNumber(status?.live_total_load_kw)} kW
          </p>
        </Panel>

        <Panel className="p-4 xl:col-span-2">
          <h2 className="mb-3 text-sm font-semibold">What-if explorer</h2>
          <div className="grid gap-3 md:grid-cols-4">
            <Field
              label="Outdoor °C"
              value={whatIf.outdoor_temperature}
              onChange={(v) => setWhatIf((w) => ({ ...w, outdoor_temperature: v }))}
            />
            <Field
              label="Occupancy level"
              value={whatIf.occupancy_level}
              step={0.1}
              onChange={(v) => setWhatIf((w) => ({ ...w, occupancy_level: v }))}
            />
            <Field
              label="Energy target %"
              value={whatIf.energy_saving_target}
              onChange={(v) => setWhatIf((w) => ({ ...w, energy_saving_target: v }))}
            />
            <div className="flex items-end">
              <button
                type="button"
                disabled={!buildingId || runWhatIf.isPending}
                onClick={() => runWhatIf.mutate()}
                className="w-full rounded-md bg-live px-3 py-2 text-sm font-semibold text-graphite-950 disabled:opacity-50"
              >
                {runWhatIf.isPending ? "Running…" : "Run what-if"}
              </button>
            </div>
          </div>
          {message ? <p className="mt-3 text-xs text-warning">{message}</p> : null}
          {whatIfResult ? (
            <pre className="mt-3 overflow-x-auto rounded border border-border bg-background/50 p-3 font-mono text-[11px] text-muted">
              {JSON.stringify(whatIfResult, null, 2)}
            </pre>
          ) : null}
        </Panel>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  step = 1,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
}) {
  return (
    <label className="block text-xs">
      <span className="mb-1 block text-muted">{label}</span>
      <input
        type="number"
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
      />
    </label>
  );
}
