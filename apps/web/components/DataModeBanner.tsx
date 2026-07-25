"use client";

import { Database, FlaskConical } from "lucide-react";

export function DataModeBanner({
  dataMode,
  dataSourceVisible,
  syntheticMultiplierApplied,
  lastGeneratedAt,
  variant = "experiment",
}: {
  dataMode?: string | null;
  dataSourceVisible?: string | null;
  syntheticMultiplierApplied?: boolean | null;
  lastGeneratedAt?: string | null;
  /** experiment = Path A measured results; playback = recorded stream replay */
  variant?: "experiment" | "playback";
}) {
  const mode = (dataMode || "unknown").toLowerCase();
  const isEp = mode === "energyplus";
  const isPlayback = variant === "playback";
  return (
    <div
      className={
        isPlayback
          ? "mb-4 flex items-start gap-3 rounded-lg border border-sky-500/40 bg-sky-500/10 px-4 py-3"
          : isEp
            ? "mb-4 flex items-start gap-3 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-4 py-3"
            : "mb-4 flex items-start gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3"
      }
    >
      {isEp || isPlayback ? (
        <FlaskConical className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" />
      ) : (
        <Database className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />
      )}
      <div className="min-w-0">
        <div className="font-mono text-[11px] uppercase tracking-[0.18em] text-foreground">
          {isPlayback ? "LIVE-DEMO PLAYBACK (NOT A PHYSICAL BUILDING)" : `DATA_MODE=${mode}`}
        </div>
        <p className="mt-1 text-sm text-muted">
          {isPlayback
            ? "Recorded EnergyPlus control stream replay from results/agent/stream.json — not a live BMS."
            : dataSourceVisible ||
              (isEp
                ? "Data source: EnergyPlus experiment results (results/*)"
                : "Mock digital twin")}
          {!isPlayback &&
            (syntheticMultiplierApplied
              ? " · WARNING: synthetic multiplier active"
              : " · No synthetic ×1.12 multiplier")}
        </p>
        {!isPlayback && lastGeneratedAt ? (
          <p className="mt-1 font-mono text-xs text-foreground/80">
            Experiment results · Last generated: {lastGeneratedAt}
          </p>
        ) : null}
        {!isPlayback && isEp ? (
          <p className="mt-1 text-xs text-muted">
            Opening this page does not rerun EnergyPlus; it displays the latest
            generated Path A experiment artifacts.
          </p>
        ) : null}
        {isEp &&
        (dataSourceVisible || "")
          .toLowerCase()
          .includes("no energyplus experiment results") ? (
          <p className="mt-2 text-sm font-medium text-amber-200">
            No EnergyPlus experiment results found. Run the baseline and agent
            experiment scripts first.
          </p>
        ) : null}
      </div>
    </div>
  );
}
