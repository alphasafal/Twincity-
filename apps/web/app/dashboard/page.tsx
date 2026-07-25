"use client";

import {
  AlertTriangle,
  Leaf,
  PlugZap,
  ShieldCheck,
  ThermometerSun,
  Zap,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ConfidenceGauge } from "@/components/ConfidenceGauge";
import { DataModeBanner } from "@/components/DataModeBanner";
import { KpiCard } from "@/components/KpiCard";
import { ModeBanner } from "@/components/ModeBanner";
import { OperatingModeBadge } from "@/components/OperatingModeBadge";
import { ServiceHealthPanel } from "@/components/ServiceHealthPanel";
import { EmptyState, PageHeader, Panel, SimulatedBadge } from "@/components/AppShell";
import { useBuildingId, useLiveBuilding } from "@/lib/hooks";
import { formatNumber, formatPct } from "@/lib/utils";

type ExperimentBlock = {
  available?: boolean;
  generated_at_utc?: string;
  baseline_generated_at_utc?: string;
  agent_generated_at_utc?: string;
  rerun_note?: string;
  baseline?: {
    total_energy_kwh?: number;
    hvac_energy_kwh?: number;
    peak_power_kw?: number;
    occupied_comfort_violation_hours?: number;
  };
  agent?: {
    total_energy_kwh?: number;
    hvac_energy_kwh?: number;
    peak_power_kw?: number;
    occupied_comfort_violation_hours?: number;
  };
  reductions?: {
    total_energy_pct?: number | null;
    hvac_energy_pct?: number | null;
    peak_power_pct?: number | null;
  };
  action_counts?: {
    approved?: number;
    rejected?: number;
    fallback?: number;
  };
};

export default function DashboardPage() {
  const buildingId = useBuildingId();
  const { data, isLoading, error, socketStatus } = useLiveBuilding(buildingId);
  const experiment = (data?.experiment || null) as ExperimentBlock | null;
  const isEnergyPlus = data?.data_mode === "energyplus" && experiment?.available;
  const energyPlusNoData =
    data?.data_mode === "energyplus" && !experiment?.available;

  const history = (data?.kpi_history || []).map((p, idx) => ({
    idx,
    power: Number(p.power_kw ?? 0),
    baseline: Number(p.baseline_power_kw ?? 0),
    comfort: Number(p.comfort_compliance ?? 0),
    ts: String(p.timestamp || idx),
  }));

  const comparisonBars = isEnergyPlus
    ? [
        {
          name: "Total",
          baseline: Number(experiment?.baseline?.total_energy_kwh ?? 0),
          agent: Number(experiment?.agent?.total_energy_kwh ?? 0),
        },
        {
          name: "HVAC",
          baseline: Number(experiment?.baseline?.hvac_energy_kwh ?? 0),
          agent: Number(experiment?.agent?.hvac_energy_kwh ?? 0),
        },
        {
          name: "Peak kW",
          baseline: Number(experiment?.baseline?.peak_power_kw ?? 0),
          agent: Number(experiment?.agent?.peak_power_kw ?? 0),
        },
      ]
    : [];

  return (
    <div>
      <PageHeader
        title="Operations dashboard"
        description={
          isEnergyPlus
            ? "Measured EnergyPlus baseline-vs-agent experiment results."
            : "Building status from /api/v1/buildings/{id}/status."
        }
        actions={
          <div className="flex items-center gap-2">
            {data?.simulated ? <SimulatedBadge /> : null}
            <OperatingModeBadge mode={data?.mode} />
          </div>
        }
      />

      <DataModeBanner
        dataMode={data?.data_mode}
        dataSourceVisible={
          data?.data_source_visible ||
          (isEnergyPlus ? "Data source: EnergyPlus experiment results" : undefined)
        }
        syntheticMultiplierApplied={data?.synthetic_multiplier_applied}
        lastGeneratedAt={
          experiment?.generated_at_utc ||
          experiment?.agent_generated_at_utc ||
          experiment?.baseline_generated_at_utc
        }
        variant="experiment"
      />

      <ModeBanner mode={data?.mode} />

      {error ? (
        <EmptyState>
          Failed to load status: {error instanceof Error ? error.message : "Unknown error"}
        </EmptyState>
      ) : null}

      {isLoading && !data ? (
        <EmptyState>Loading building status…</EmptyState>
      ) : null}

      {data ? (
        <>
          {energyPlusNoData ? (
            <EmptyState>
              No EnergyPlus experiment results found. Run the baseline and agent
              experiment scripts first.
            </EmptyState>
          ) : null}
          {isEnergyPlus ? (
            <>
              <div className="mb-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <KpiCard
                  label="Baseline total energy"
                  value={formatNumber(experiment?.baseline?.total_energy_kwh)}
                  unit="kWh"
                  tone="neutral"
                  icon={Zap}
                  simulated={false}
                />
                <KpiCard
                  label="Agent total energy"
                  value={formatNumber(experiment?.agent?.total_energy_kwh)}
                  unit="kWh"
                  tone="live"
                  icon={Zap}
                  simulated={false}
                />
                <KpiCard
                  label="Total energy reduction"
                  value={formatPct(experiment?.reductions?.total_energy_pct)}
                  tone="savings"
                  icon={Leaf}
                  hint="(baseline − agent) / baseline"
                  simulated={false}
                />
                <KpiCard
                  label="HVAC energy reduction"
                  value={formatPct(experiment?.reductions?.hvac_energy_pct)}
                  tone="savings"
                  icon={Leaf}
                  hint={`Baseline ${formatNumber(experiment?.baseline?.hvac_energy_kwh)} → Agent ${formatNumber(experiment?.agent?.hvac_energy_kwh)} kWh`}
                  simulated={false}
                />
                <KpiCard
                  label="Peak power reduction"
                  value={formatPct(experiment?.reductions?.peak_power_pct)}
                  tone="savings"
                  icon={PlugZap}
                  hint={`Baseline ${formatNumber(experiment?.baseline?.peak_power_kw)} → Agent ${formatNumber(experiment?.agent?.peak_power_kw)} kW`}
                  simulated={false}
                />
                <KpiCard
                  label="Comfort violations"
                  value={`${formatNumber(experiment?.baseline?.occupied_comfort_violation_hours, 0)} → ${formatNumber(experiment?.agent?.occupied_comfort_violation_hours, 0)}`}
                  unit="h"
                  tone="live"
                  icon={ThermometerSun}
                  hint="Baseline → Agent occupied hours"
                  simulated={false}
                />
                <KpiCard
                  label="Approved actions"
                  value={String(experiment?.action_counts?.approved ?? 0)}
                  tone="live"
                  icon={ShieldCheck}
                  hint={`Rejected ${experiment?.action_counts?.rejected ?? 0} · Fallback ${experiment?.action_counts?.fallback ?? 0}`}
                  simulated={false}
                />
                <KpiCard
                  label="Carbon avoided (estimate)"
                  value={formatNumber(data.carbon_avoided_today_kg)}
                  unit="kg"
                  tone="savings"
                  icon={Leaf}
                  hint="Static emission factor — see docs/carbon.md"
                  simulated={false}
                />
              </div>

              <div className="mb-5 grid gap-4 xl:grid-cols-[1.6fr_1fr]">
                <Panel className="p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <h2 className="text-sm font-semibold">Baseline vs agent (measured)</h2>
                    <span className="font-mono text-[10px] uppercase tracking-wider text-muted">
                      results/comparison
                    </span>
                  </div>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={comparisonBars}>
                        <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
                        <XAxis dataKey="name" stroke="var(--muted)" fontSize={11} />
                        <YAxis stroke="var(--muted)" fontSize={11} />
                        <Tooltip
                          contentStyle={{
                            background: "var(--surface)",
                            border: "1px solid var(--border)",
                            borderRadius: 8,
                          }}
                        />
                        <Area
                          type="monotone"
                          dataKey="baseline"
                          stroke="#8490a1"
                          fill="transparent"
                          strokeDasharray="4 4"
                          name="Baseline"
                        />
                        <Area
                          type="monotone"
                          dataKey="agent"
                          stroke="#34d399"
                          fill="rgba(52,211,153,0.15)"
                          name="Agent"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </Panel>
                <ServiceHealthPanel
                  health={data.service_health}
                  socketStatus={socketStatus}
                />
              </div>
            </>
          ) : (
            <>
              <div className="mb-5 grid gap-4 lg:grid-cols-[220px_1fr]">
                <Panel className="p-4">
                  <ConfidenceGauge confidence={data.confidence} />
                </Panel>
                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                  <KpiCard
                    label="Live load"
                    value={formatNumber(data.live_total_load_kw)}
                    unit="kW"
                    tone="live"
                    icon={PlugZap}
                    hint={`Scenario: ${data.active_scenario || "normal"}`}
                    simulated={data.simulated}
                  />
                  <KpiCard
                    label="Energy saved today"
                    value={formatPct(data.energy_saved_today_pct)}
                    tone="savings"
                    icon={Leaf}
                    simulated={data.simulated}
                    hint="No synthetic multiplier in mock mode"
                  />
                  <KpiCard
                    label="Comfort compliance"
                    value={formatPct(data.comfort_compliance_pct)}
                    tone="live"
                    icon={ThermometerSun}
                  />
                  <KpiCard
                    label="Active alerts"
                    value={String(data.active_alerts ?? 0)}
                    tone={(data.active_alerts ?? 0) > 0 ? "warning" : "neutral"}
                    icon={AlertTriangle}
                    hint={`${data.pending_decisions ?? 0} pending decisions`}
                  />
                </div>
              </div>
              <div className="grid gap-4 xl:grid-cols-[1.6fr_1fr]">
                <Panel className="p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <h2 className="text-sm font-semibold">Power (mock twin)</h2>
                    <span className="font-mono text-[10px] uppercase tracking-wider text-muted">
                      kpi_history
                    </span>
                  </div>
                  {history.length ? (
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={history}>
                          <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
                          <XAxis dataKey="idx" hide />
                          <YAxis stroke="var(--muted)" fontSize={11} />
                          <Tooltip
                            contentStyle={{
                              background: "var(--surface)",
                              border: "1px solid var(--border)",
                              borderRadius: 8,
                            }}
                          />
                          <Area
                            type="monotone"
                            dataKey="power"
                            stroke="#22d3ee"
                            fill="rgba(34,211,238,0.15)"
                            name="Twin kW"
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <EmptyState>No KPI history points yet from the API.</EmptyState>
                  )}
                </Panel>
                <ServiceHealthPanel
                  health={data.service_health}
                  socketStatus={socketStatus}
                />
              </div>
            </>
          )}
        </>
      ) : null}
    </div>
  );
}
