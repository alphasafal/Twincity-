"use client";

import type { ServiceHealth } from "@/lib/types";
import { cn } from "@/lib/utils";

function normalize(entry: ServiceHealth[string]): {
  label: string;
  ok: boolean;
  detail?: string;
} {
  if (typeof entry === "boolean") {
    return { label: entry ? "healthy" : "degraded", ok: entry };
  }
  if (typeof entry === "string") {
    const ok = ["ok", "healthy", "up", "ready"].includes(entry.toLowerCase());
    return { label: entry, ok };
  }
  if (entry && typeof entry === "object") {
    const status = String(entry.status ?? (entry.healthy ? "healthy" : "unknown"));
    const ok =
      Boolean(entry.healthy) ||
      ["ok", "healthy", "up", "ready"].includes(status.toLowerCase());
    return {
      label: status,
      ok,
      detail: entry.detail ? String(entry.detail) : undefined,
    };
  }
  return { label: "unknown", ok: false };
}

export function ServiceHealthPanel({
  health,
  socketStatus,
}: {
  health?: ServiceHealth | null;
  socketStatus?: string;
}) {
  const entries = Object.entries(health || {});

  return (
    <div className="rounded-lg border border-border bg-surface/80 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Service health</h3>
        {socketStatus ? (
          <span className="font-mono text-[10px] uppercase tracking-wider text-muted">
            WS: {socketStatus}
          </span>
        ) : null}
      </div>
      {!entries.length ? (
        <p className="text-sm text-muted">No service health payload from status API.</p>
      ) : (
        <ul className="space-y-2">
          {entries.map(([name, value]) => {
            const n = normalize(value);
            return (
              <li
                key={name}
                className="flex items-center justify-between gap-3 rounded border border-border/70 bg-background/40 px-3 py-2 text-sm"
              >
                <div>
                  <div className="capitalize text-foreground">{name.replaceAll("_", " ")}</div>
                  {n.detail ? <div className="text-xs text-muted">{n.detail}</div> : null}
                </div>
                <span
                  className={cn(
                    "rounded border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider",
                    n.ok
                      ? "border-savings/40 text-savings"
                      : "border-critical/40 text-critical",
                  )}
                >
                  {n.label}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
