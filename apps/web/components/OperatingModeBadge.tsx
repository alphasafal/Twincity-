"use client";

import { cn } from "@/lib/utils";

const MODE_STYLES: Record<string, string> = {
  AUTONOMOUS: "border-savings/40 bg-savings/10 text-savings",
  GUARDED: "border-live/40 bg-live/10 text-live",
  ADVISORY: "border-warning/40 bg-warning/10 text-warning",
  FALLBACK: "border-critical/40 bg-critical/10 text-critical",
  MANUAL: "border-border bg-surface-muted text-muted",
};

export function OperatingModeBadge({
  mode,
  className,
}: {
  mode?: string | null;
  className?: string;
}) {
  const value = (mode || "UNKNOWN").toUpperCase();
  return (
    <span
      className={cn(
        "inline-flex items-center rounded border px-2 py-0.5 font-mono text-[11px] uppercase tracking-wider",
        MODE_STYLES[value] || "border-border bg-surface text-muted",
        className,
      )}
    >
      {value}
    </span>
  );
}
