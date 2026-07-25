"use client";

import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

type Tone = "live" | "savings" | "warning" | "critical" | "neutral" | "ai";

const TONE: Record<Tone, string> = {
  live: "text-live",
  savings: "text-savings",
  warning: "text-warning",
  critical: "text-critical",
  ai: "text-ai",
  neutral: "text-foreground",
};

export function KpiCard({
  label,
  value,
  unit,
  hint,
  icon: Icon,
  tone = "neutral",
  simulated,
  className,
}: {
  label: string;
  value: string;
  unit?: string;
  hint?: string;
  icon?: LucideIcon;
  tone?: Tone;
  simulated?: boolean;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-surface/80 p-4 shadow-panel animate-fade-up",
        className,
      )}
    >
      <div className="mb-3 flex items-start justify-between gap-2">
        <div className="text-xs uppercase tracking-wider text-muted">{label}</div>
        {Icon ? <Icon className={cn("h-4 w-4", TONE[tone])} /> : null}
      </div>
      <div className="flex items-baseline gap-1.5">
        <span className={cn("font-mono text-2xl font-semibold tabular-nums", TONE[tone])}>
          {value}
        </span>
        {unit ? <span className="text-sm text-muted">{unit}</span> : null}
      </div>
      {(hint || simulated) && (
        <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-muted">
          {hint ? <span>{hint}</span> : null}
          {simulated ? (
            <span className="rounded border border-warning/30 bg-warning/10 px-1.5 py-0.5 font-mono uppercase tracking-wider text-warning">
              Simulated
            </span>
          ) : null}
        </div>
      )}
    </div>
  );
}
