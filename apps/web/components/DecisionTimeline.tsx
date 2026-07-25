"use client";

import Link from "next/link";
import type { Decision } from "@/lib/types";
import { formatPct, formatTs } from "@/lib/utils";
import { OperatingModeBadge } from "./OperatingModeBadge";

export function DecisionTimeline({ decisions }: { decisions: Decision[] }) {
  if (!decisions.length) {
    return (
      <div className="rounded-lg border border-dashed border-border px-4 py-8 text-center text-sm text-muted">
        No decisions returned from the API yet.
      </div>
    );
  }

  return (
    <ol className="relative space-y-0 border-l border-border pl-5">
      {decisions.map((d) => (
        <li key={d.id} className="relative pb-6 last:pb-0">
          <span className="absolute -left-[1.4rem] top-1.5 h-2.5 w-2.5 rounded-full border border-live bg-graphite-900" />
          <div className="rounded-lg border border-border bg-surface/70 p-4">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <OperatingModeBadge mode={d.mode} />
              <span className="font-mono text-[11px] uppercase tracking-wider text-muted">
                {d.execution_status}
              </span>
              <span className="text-xs text-muted">{formatTs(d.created_at)}</span>
            </div>
            <p className="text-sm text-foreground">
              {d.explanation || "No explanation provided."}
            </p>
            <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted">
              <span>Trigger: {d.trigger}</span>
              <span>Confidence: {formatPct(d.confidence * 100, 0)}</span>
              <span>Validation: {d.validation_status}</span>
            </div>
            <Link
              href={`/decisions/${d.id}`}
              className="mt-3 inline-block text-sm text-live hover:underline"
            >
              Open decision
            </Link>
          </div>
        </li>
      ))}
    </ol>
  );
}
