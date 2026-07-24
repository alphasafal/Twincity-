"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { EmptyState, PageHeader, Panel, SimulatedBadge } from "@/components/AppShell";
import { api } from "@/lib/api";
import { formatNumber, formatTs } from "@/lib/utils";

export default function ZoneDetailPage() {
  const params = useParams<{ zoneId: string }>();
  const zoneId = params.zoneId;
  const queryClient = useQueryClient();
  const [setpoint, setSetpoint] = useState(24);
  const [duration, setDuration] = useState(60);
  const [reason, setReason] = useState("Manual comfort adjustment");
  const [message, setMessage] = useState<string | null>(null);

  const zoneQuery = useQuery({
    queryKey: ["zone", zoneId],
    queryFn: () => api.getZone(zoneId),
    enabled: Boolean(zoneId),
  });
  const healthQuery = useQuery({
    queryKey: ["zone-health", zoneId],
    queryFn: () => api.zoneHealth(zoneId),
    enabled: Boolean(zoneId),
    refetchInterval: 10_000,
  });
  const telemetryQuery = useQuery({
    queryKey: ["zone-telemetry", zoneId],
    queryFn: () => api.zoneTelemetry(zoneId, 120),
    enabled: Boolean(zoneId),
  });

  const overrideMut = useMutation({
    mutationFn: () =>
      api.zoneOverride(zoneId, {
        value: setpoint,
        duration_minutes: duration,
        reason,
        confirm: true,
      }),
    onSuccess: () => {
      setMessage("Override applied after Safety Shield validation.");
      void queryClient.invalidateQueries({ queryKey: ["zone-health", zoneId] });
    },
    onError: (err) => {
      setMessage(err instanceof Error ? err.message : "Override rejected");
    },
  });

  const temps = (telemetryQuery.data || [])
    .filter((p) => p.metric === "temperature" || p.metric.includes("temp"))
    .slice()
    .reverse()
    .map((p, idx) => ({ idx, value: p.value, ts: p.timestamp }));

  const zone = zoneQuery.data;
  const health = healthQuery.data;
  const live = (health?.live || {}) as Record<string, unknown>;

  return (
    <div>
      <PageHeader
        title={zone?.name || "Zone"}
        description="Telemetry and health from /api/v1/zones/{id} endpoints."
        actions={<SimulatedBadge />}
      />

      {zoneQuery.error || healthQuery.error ? (
        <EmptyState>
          {(zoneQuery.error || healthQuery.error) instanceof Error
            ? ((zoneQuery.error || healthQuery.error) as Error).message
            : "Failed to load zone"}
        </EmptyState>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[1.3fr_1fr]">
        <Panel className="p-4">
          <h2 className="mb-3 text-sm font-semibold">Temperature telemetry</h2>
          {temps.length ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={temps}>
                  <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
                  <XAxis dataKey="idx" hide />
                  <YAxis stroke="var(--muted)" fontSize={11} domain={["auto", "auto"]} />
                  <Tooltip
                    contentStyle={{
                      background: "var(--surface)",
                      border: "1px solid var(--border)",
                    }}
                    labelFormatter={(_, payload) =>
                      payload?.[0]?.payload?.ts
                        ? formatTs(String(payload[0].payload.ts))
                        : ""
                    }
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#22d3ee"
                    dot={false}
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState>
              No temperature points in zone telemetry yet. Live snapshot still shown on the right.
            </EmptyState>
          )}
        </Panel>

        <div className="space-y-4">
          <Panel className="space-y-2 p-4 text-sm">
            <h2 className="text-sm font-semibold">Live health</h2>
            <Row label="Comfort" value={String(health?.comfort_status ?? "—")} />
            <Row
              label="Sensor health"
              value={formatNumber(health?.sensor_health != null ? health.sensor_health * 100 : null)}
              unit="%"
            />
            <Row
              label="Freshness"
              value={formatNumber(health?.data_freshness_seconds)}
              unit="s"
            />
            <Row label="Temperature" value={formatNumber(Number(live.temperature))} unit="°C" />
            <Row label="Cooling SP" value={formatNumber(Number(live.cooling_setpoint))} unit="°C" />
            <Row label="CO₂" value={formatNumber(Number(live.co2), 0)} unit="ppm" />
            {health?.sensor_failed ? (
              <div className="rounded border border-critical/40 bg-critical/10 px-3 py-2 text-critical">
                Sensor fault active — values may be estimated.
              </div>
            ) : null}
          </Panel>

          <Panel className="p-4">
            <h2 className="mb-2 text-sm font-semibold">Manual override</h2>
            <p className="mb-3 text-xs text-muted">
              Calls /api/v1/zones/{`{id}`}/override — Safety Shield may reject.
            </p>
            <div className="space-y-3">
              <label className="block text-xs">
                <span className="mb-1 block text-muted">Cooling setpoint (°C)</span>
                <input
                  type="number"
                  step={0.5}
                  value={setpoint}
                  onChange={(e) => setSetpoint(Number(e.target.value))}
                  className="w-full rounded-md border border-border bg-background px-3 py-2"
                />
              </label>
              <label className="block text-xs">
                <span className="mb-1 block text-muted">Duration (minutes)</span>
                <input
                  type="number"
                  value={duration}
                  onChange={(e) => setDuration(Number(e.target.value))}
                  className="w-full rounded-md border border-border bg-background px-3 py-2"
                />
              </label>
              <label className="block text-xs">
                <span className="mb-1 block text-muted">Reason</span>
                <input
                  type="text"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  className="w-full rounded-md border border-border bg-background px-3 py-2"
                />
              </label>
              <button
                type="button"
                disabled={overrideMut.isPending || reason.trim().length < 3}
                onClick={() => overrideMut.mutate()}
                className="w-full rounded-md bg-live px-3 py-2 text-sm font-semibold text-graphite-950 disabled:opacity-50"
              >
                {overrideMut.isPending ? "Validating…" : "Apply override"}
              </button>
              {message ? <p className="text-xs text-muted">{message}</p> : null}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

function Row({
  label,
  value,
  unit,
}: {
  label: string;
  value: string;
  unit?: string;
}) {
  return (
    <div className="flex justify-between gap-3 rounded border border-border/70 bg-background/40 px-3 py-2">
      <span className="text-muted">{label}</span>
      <span className="font-mono">
        {value}
        {unit ? ` ${unit}` : ""}
      </span>
    </div>
  );
}
