"use client";

import type { ControlPlan } from "@/lib/types";
import { cn, formatNumber, formatPct } from "@/lib/utils";

export function PlanCard({
  plan,
  selected,
  onSelect,
  actions,
}: {
  plan: ControlPlan;
  selected?: boolean;
  onSelect?: () => void;
  actions?: React.ReactNode;
}) {
  const metrics = plan.predicted_metrics_json || {};
  return (
    <article
      className={cn(
        "rounded-lg border border-border bg-surface/80 p-4 shadow-panel transition",
        selected && "border-live/50 ring-1 ring-live/30",
        onSelect && "cursor-pointer hover:border-live/30",
      )}
      onClick={onSelect}
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-foreground">{plan.plan_name}</h3>
          <div className="mt-1 flex flex-wrap gap-2 font-mono text-[10px] uppercase tracking-wider text-muted">
            <span>{plan.source}</span>
            <span>{plan.status}</span>
            <span className={plan.feasibility ? "text-savings" : "text-critical"}>
              {plan.feasibility ? "Feasible" : "Infeasible"}
            </span>
          </div>
        </div>
        <div className="text-right">
          <div className="font-mono text-lg text-live">{formatNumber(plan.objective_score, 3)}</div>
          <div className="text-[10px] uppercase tracking-wider text-muted">Score</div>
        </div>
      </div>
      <dl className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
        <Metric label="Energy" value={metrics.energy_kwh ?? metrics.simulated_energy_kwh} unit="kWh" />
        <Metric label="Cost" value={metrics.cost ?? metrics.simulated_cost} unit="$" />
        <Metric label="Carbon" value={metrics.carbon_kg ?? metrics.simulated_carbon_kg} unit="kg" />
        <Metric label="Confidence" value={formatPct(plan.confidence * 100, 0)} />
      </dl>
      {Array.isArray(plan.actions_json) && plan.actions_json.length > 0 ? (
        <div className="mt-3 rounded border border-border bg-surface-muted/50 px-3 py-2 text-xs text-muted">
          {plan.actions_json.length} action{plan.actions_json.length === 1 ? "" : "s"} · first:{" "}
          <span className="font-mono text-foreground">
            {String(plan.actions_json[0]?.action_type)} → {String(plan.actions_json[0]?.zone_id)} ={" "}
            {String(plan.actions_json[0]?.proposed_value)}
          </span>
        </div>
      ) : null}
      {actions ? <div className="mt-3 flex flex-wrap gap-2">{actions}</div> : null}
    </article>
  );
}

function Metric({
  label,
  value,
  unit,
}: {
  label: string;
  value: unknown;
  unit?: string;
}) {
  const display =
    typeof value === "number"
      ? `${formatNumber(value)}${unit ? ` ${unit}` : ""}`
      : typeof value === "string"
        ? value
        : "—";
  return (
    <div className="rounded border border-border/70 bg-background/40 px-2 py-1.5">
      <dt className="text-[10px] uppercase tracking-wider text-muted">{label}</dt>
      <dd className="font-mono text-foreground">{display}</dd>
    </div>
  );
}
