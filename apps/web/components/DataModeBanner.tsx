"use client";

import { Database, FlaskConical } from "lucide-react";

export function DataModeBanner({
  dataMode,
  dataSourceVisible,
  syntheticMultiplierApplied,
}: {
  dataMode?: string | null;
  dataSourceVisible?: string | null;
  syntheticMultiplierApplied?: boolean | null;
}) {
  const mode = (dataMode || "unknown").toLowerCase();
  const isEp = mode === "energyplus";
  return (
    <div
      className={
        isEp
          ? "mb-4 flex items-start gap-3 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-4 py-3"
          : "mb-4 flex items-start gap-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3"
      }
    >
      {isEp ? (
        <FlaskConical className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" />
      ) : (
        <Database className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />
      )}
      <div className="min-w-0">
        <div className="font-mono text-[11px] uppercase tracking-[0.18em] text-foreground">
          DATA_MODE={mode}
        </div>
        <p className="mt-1 text-sm text-muted">
          {dataSourceVisible ||
            (isEp
              ? "EnergyPlus experiment results (results/*)"
              : "Mock digital twin")}
          {syntheticMultiplierApplied
            ? " · WARNING: synthetic multiplier active"
            : " · No synthetic ×1.12 multiplier"}
        </p>
      </div>
    </div>
  );
}
