"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { EmptyState, PageHeader, Panel, SimulatedBadge } from "@/components/AppShell";
import { SimulationControls } from "@/components/SimulationControls";
import { ZoneMap } from "@/components/ZoneMap";
import { api } from "@/lib/api";
import { useBuildingId, useLiveBuilding, useZones } from "@/lib/hooks";
import { formatNumber } from "@/lib/utils";

export default function DigitalTwinPage() {
  const buildingId = useBuildingId();
  const queryClient = useQueryClient();
  const { data: status, isLoading, error } = useLiveBuilding(buildingId);
  const { data: zones = [] } = useZones(buildingId);
  const [speed, setSpeed] = useState(4);

  const playback = useMutation({
    mutationFn: (action: "pause" | "resume" | "step" | "reset") =>
      api.demoPlayback(action),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["building-status", buildingId] });
    },
  });

  const speedMut = useMutation({
    mutationFn: (value: number) => api.demoSpeed(value),
    onSuccess: (_, value) => setSpeed(value),
  });

  const liveZones = status?.state?.zones || {};

  return (
    <div>
      <PageHeader
        title="Digital twin"
        description="Interactive five-zone layout color-coded by comfort status from live simulator state."
        actions={<SimulatedBadge label="Simulated twin" />}
      />

      {error ? (
        <EmptyState>
          {error instanceof Error ? error.message : "Failed to load twin state"}
        </EmptyState>
      ) : null}

      {isLoading && !status ? <EmptyState>Loading twin state…</EmptyState> : null}

      <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
        <Panel className="p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-semibold">Zone comfort map</h2>
              <p className="text-xs text-muted">
                Outdoor {formatNumber(status?.state?.outdoor_temperature)}°C · Building load{" "}
                {formatNumber(status?.live_total_load_kw)} kW
              </p>
            </div>
            <span className="font-mono text-[10px] uppercase tracking-wider text-muted">
              {status?.state?.timestamp_iso || "no timestamp"}
            </span>
          </div>
          {zones.length ? (
            <ZoneMap zones={zones} liveZones={liveZones} />
          ) : (
            <EmptyState>No zones returned from the API.</EmptyState>
          )}
        </Panel>

        <div className="space-y-4">
          <SimulationControls
            speed={speed}
            busy={playback.isPending || speedMut.isPending}
            onSpeed={(value) => speedMut.mutate(value)}
            onPlayback={(action) => playback.mutate(action)}
          />
          <Panel className="p-4">
            <h3 className="mb-2 text-sm font-semibold">Live signals</h3>
            <dl className="space-y-2 text-sm">
              <Row label="Tariff" value={`${formatNumber(status?.state?.electricity_tariff)} $/kWh`} />
              <Row
                label="Grid carbon"
                value={`${formatNumber(status?.state?.grid_carbon_intensity, 0)} g/kWh`}
              />
              <Row label="Active scenario" value={status?.active_scenario || "none"} />
              <Row
                label="Healthy sensors"
                value={`${formatNumber(status?.healthy_sensors_pct)}%`}
              />
            </dl>
          </Panel>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded border border-border/70 bg-background/40 px-3 py-2">
      <dt className="text-muted">{label}</dt>
      <dd className="font-mono text-foreground">{value}</dd>
    </div>
  );
}
