"use client";

import type { ConfidenceBreakdown } from "@/lib/types";
import { cn, formatPct } from "@/lib/utils";

function scoreFrom(confidence: ConfidenceBreakdown | number | null | undefined): number {
  if (typeof confidence === "number") return confidence;
  if (!confidence) return 0;
  if (typeof confidence.score === "number") return confidence.score;
  const values = Object.values(confidence).filter((v): v is number => typeof v === "number");
  if (!values.length) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

export function ConfidenceGauge({
  confidence,
  size = 120,
  className,
}: {
  confidence?: ConfidenceBreakdown | number | null;
  size?: number;
  className?: string;
}) {
  const score = Math.max(0, Math.min(1, scoreFrom(confidence)));
  const pct = score * 100;
  const radius = 44;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score * circumference);
  const color =
    score >= 0.8 ? "var(--savings)" : score >= 0.55 ? "var(--warning)" : "var(--critical)";

  const breakdown =
    typeof confidence === "object" && confidence
      ? Object.entries(confidence).filter(
          ([k, v]) => k !== "score" && typeof v === "number",
        )
      : [];

  return (
    <div className={cn("flex flex-col items-center gap-3", className)}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90">
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke="var(--border)"
            strokeWidth="8"
          />
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-[stroke-dashoffset] duration-700 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-mono text-xl text-foreground">{formatPct(pct, 0)}</span>
          <span className="text-[10px] uppercase tracking-wider text-muted">Confidence</span>
        </div>
      </div>
      {breakdown.length ? (
        <dl className="grid w-full grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
          {breakdown.map(([key, value]) => (
            <div key={key} className="flex justify-between gap-2 text-muted">
              <dt className="truncate capitalize">{key.replaceAll("_", " ")}</dt>
              <dd className="font-mono text-foreground">{formatPct((value as number) * 100, 0)}</dd>
            </div>
          ))}
        </dl>
      ) : null}
    </div>
  );
}
