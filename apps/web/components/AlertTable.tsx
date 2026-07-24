"use client";

import type { Alert } from "@/lib/types";
import { cn, formatTs } from "@/lib/utils";

const SEVERITY: Record<string, string> = {
  INFORMATIONAL: "text-muted border-border",
  WARNING: "text-warning border-warning/40",
  HIGH: "text-warning border-warning/50",
  CRITICAL: "text-critical border-critical/50",
};

export function AlertTable({
  alerts,
  onAcknowledge,
  onResolve,
  busyId,
}: {
  alerts: Alert[];
  onAcknowledge?: (id: string) => void;
  onResolve?: (id: string) => void;
  busyId?: string | null;
}) {
  if (!alerts.length) {
    return (
      <div className="rounded-lg border border-dashed border-border px-4 py-8 text-center text-sm text-muted">
        No alerts from `/api/v1/.../alerts`.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-surface-muted/60 text-[11px] uppercase tracking-wider text-muted">
          <tr>
            <th className="px-3 py-2 font-medium">Severity</th>
            <th className="px-3 py-2 font-medium">Title</th>
            <th className="px-3 py-2 font-medium">Status</th>
            <th className="px-3 py-2 font-medium">Created</th>
            <th className="px-3 py-2 font-medium">Actions</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((alert) => (
            <tr key={alert.id} className="border-t border-border/80 bg-surface/40">
              <td className="px-3 py-2.5">
                <span
                  className={cn(
                    "rounded border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider",
                    SEVERITY[alert.severity] || SEVERITY.INFORMATIONAL,
                  )}
                >
                  {alert.severity}
                </span>
              </td>
              <td className="px-3 py-2.5">
                <div className="font-medium text-foreground">{alert.title}</div>
                <div className="mt-0.5 max-w-md text-xs text-muted">{alert.message}</div>
              </td>
              <td className="px-3 py-2.5 font-mono text-xs text-muted">{alert.status}</td>
              <td className="px-3 py-2.5 text-xs text-muted">{formatTs(alert.created_at)}</td>
              <td className="px-3 py-2.5">
                <div className="flex flex-wrap gap-1.5">
                  <button
                    type="button"
                    disabled={
                      alert.status !== "OPEN" || busyId === alert.id || !onAcknowledge
                    }
                    onClick={() => onAcknowledge?.(alert.id)}
                    className="rounded border border-border px-2 py-1 text-xs text-muted enabled:hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
                    title={!onAcknowledge ? "Acknowledge unavailable" : undefined}
                  >
                    Ack
                  </button>
                  <button
                    type="button"
                    disabled={
                      alert.status === "RESOLVED" || busyId === alert.id || !onResolve
                    }
                    onClick={() => onResolve?.(alert.id)}
                    className="rounded border border-border px-2 py-1 text-xs text-muted enabled:hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Resolve
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
