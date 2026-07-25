"use client";

import { useQuery } from "@tanstack/react-query";
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
import { EmptyState, PageHeader, Panel, SimulatedBadge } from "@/components/AppShell";
import { KpiCard } from "@/components/KpiCard";
import { PredictionLedger } from "@/components/PredictionLedger";
import { api } from "@/lib/api";
import { useBuildingId } from "@/lib/hooks";
import { formatNumber, formatPct } from "@/lib/utils";

export default function AnalyticsPage() {
  const buildingId = useBuildingId();

  const summary = useQuery({
    queryKey: ["analytics-summary", buildingId],
    queryFn: () => api.analyticsSummary(buildingId!),
    enabled: Boolean(buildingId),
  });

  const series = useQuery({
    queryKey: ["analytics-series", buildingId],
    queryFn: () => api.analyticsTimeseries(buildingId!),
    enabled: Boolean(buildingId),
  });

  const ledger = useQuery({
    queryKey: ["ledger", buildingId],
    queryFn: () => api.ledger(buildingId!),
    enabled: Boolean(buildingId),
  });

  const points = (series.data?.points || []).map((p, idx) => ({
    idx,
    power: Number(p.power_kw ?? 0),
    baseline: Number(p.baseline_power_kw ?? 0),
    comfort: Number(p.comfort_compliance ?? 0),
    carbon: Number(p.carbon_intensity ?? 0),
  }));

  const s = summary.data || {};

  return (
    <div>
      <PageHeader
        title="Analytics"
        description="Savings, comfort, and prediction ledger from analytics API endpoints."
        actions={
          <div className="flex gap-2">
            <SimulatedBadge label={String(s.label || series.data?.label || "Simulated")} />
            <button
              type="button"
              disabled={!buildingId}
              onClick={async () => {
                const file = await api.analyticsExport(buildingId!);
                const blob = new Blob([file.csv], { type: "text/csv" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = file.filename;
                a.click();
                URL.revokeObjectURL(url);
              }}
              className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-muted hover:text-foreground disabled:opacity-50"
            >
              Export CSV
            </button>
          </div>
        }
      />

      {summary.error ? (
        <EmptyState>
          {summary.error instanceof Error ? summary.error.message : "Failed to load analytics"}
        </EmptyState>
      ) : null}

      <div className="mb-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label="Energy usage"
          value={formatNumber(Number(s.energy_usage_kwh))}
          unit="kWh"
          tone="live"
          simulated
        />
        <KpiCard
          label="Estimated savings"
          value={formatPct(Number(s.estimated_savings_pct))}
          tone="savings"
          simulated
        />
        <KpiCard
          label="Cost saved"
          value={formatNumber(Number(s.cost_saved))}
          unit="$"
          tone="savings"
          simulated
        />
        <KpiCard
          label="Carbon avoided"
          value={formatNumber(Number(s.carbon_avoided_kg))}
          unit="kg"
          tone="savings"
          simulated
        />
      </div>

      <Panel className="mb-6 p-4">
        <h2 className="mb-3 text-sm font-semibold">Timeseries</h2>
        {points.length ? (
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={points}>
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
                <XAxis dataKey="idx" hide />
                <YAxis yAxisId="left" stroke="var(--muted)" fontSize={11} />
                <YAxis yAxisId="right" orientation="right" stroke="var(--muted)" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                  }}
                />
                <Legend />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="power"
                  stroke="#22d3ee"
                  dot={false}
                  name="Twin kW"
                />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="baseline"
                  stroke="#8490a1"
                  strokeDasharray="4 4"
                  dot={false}
                  name="Baseline kW"
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="comfort"
                  stroke="#34d399"
                  dot={false}
                  name="Comfort %"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <EmptyState>No analytics timeseries points yet.</EmptyState>
        )}
      </Panel>

      <h2 className="mb-3 text-sm font-semibold">Prediction ledger</h2>
      <PredictionLedger entries={ledger.data || []} />
    </div>
  );
}
