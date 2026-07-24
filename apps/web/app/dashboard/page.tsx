"use client";

import {
  AlertTriangle,
  Leaf,
  PlugZap,
  ThermometerSun,
  Wallet,
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
import { KpiCard } from "@/components/KpiCard";
import { ModeBanner } from "@/components/ModeBanner";
import { OperatingModeBadge } from "@/components/OperatingModeBadge";
import { ServiceHealthPanel } from "@/components/ServiceHealthPanel";
import { EmptyState, PageHeader, Panel, SimulatedBadge } from "@/components/AppShell";
import { useBuildingId, useLiveBuilding } from "@/lib/hooks";
import { formatNumber, formatPct } from "@/lib/utils";

export default function DashboardPage() {
  const buildingId = useBuildingId();
  const { data, isLoading, error, socketStatus } = useLiveBuilding(buildingId);

  const history = (data?.kpi_history || []).map((p, idx) => ({
    idx,
    power: Number(p.power_kw ?? 0),
    baseline: Number(p.baseline_power_kw ?? 0),
    comfort: Number(p.comfort_compliance ?? 0),
    ts: String(p.timestamp || idx),
  }));

  return (
    <div>
      <PageHeader
        title="Operations dashboard"
        description="Live building status from /api/v1/buildings/{id}/status — not static demo theater."
        actions={
          <div className="flex items-center gap-2">
            {data?.simulated ? <SimulatedBadge /> : null}
            <OperatingModeBadge mode={data?.mode} />
          </div>
        }
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
              />
              <KpiCard
                label="Cost saved today"
                value={formatNumber(data.cost_saved_today)}
                unit="$"
                tone="savings"
                icon={Wallet}
                simulated={data.simulated}
              />
              <KpiCard
                label="Carbon avoided"
                value={formatNumber(data.carbon_avoided_today_kg)}
                unit="kg"
                tone="savings"
                icon={Leaf}
                simulated={data.simulated}
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
                <h2 className="text-sm font-semibold">Power vs baseline</h2>
                <span className="font-mono text-[10px] uppercase tracking-wider text-muted">
                  kpi_history
                </span>
              </div>
              {history.length ? (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={history}>
                      <defs>
                        <linearGradient id="powerFill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.35} />
                          <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
                        </linearGradient>
                      </defs>
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
                        dataKey="baseline"
                        stroke="#8490a1"
                        fill="transparent"
                        strokeDasharray="4 4"
                        name="Baseline kW"
                      />
                      <Area
                        type="monotone"
                        dataKey="power"
                        stroke="#22d3ee"
                        fill="url(#powerFill)"
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
      ) : null}
    </div>
  );
}
