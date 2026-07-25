"use client";

import type { LedgerEntry } from "@/lib/types";
import { formatNumber, formatPct, formatTs } from "@/lib/utils";

export function PredictionLedger({ entries }: { entries: LedgerEntry[] }) {
  if (!entries.length) {
    return (
      <div className="rounded-lg border border-dashed border-border px-4 py-8 text-center text-sm text-muted">
        Prediction ledger is empty for this building.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {entries.map((entry) => (
        <article
          key={entry.id}
          className="rounded-lg border border-border bg-surface/70 p-4"
        >
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <div className="font-mono text-[11px] uppercase tracking-wider text-muted">
              {formatTs(entry.created_at)}
            </div>
            <div className="flex gap-2 text-xs text-muted">
              <span>
                Conf {formatPct((entry.confidence_before ?? 0) * 100, 0)}
                {entry.confidence_after != null
                  ? ` → ${formatPct(entry.confidence_after * 100, 0)}`
                  : ""}
              </span>
              {entry.rollback_required ? (
                <span className="text-critical">Rollback flagged</span>
              ) : null}
            </div>
          </div>
          <p className="text-sm text-foreground">
            {entry.explanation || "No ledger explanation."}
          </p>
          <div className="mt-3 grid gap-2 text-xs sm:grid-cols-3">
            <JsonBlock title="Predicted" data={entry.predicted_json} />
            <JsonBlock title="Realized" data={entry.realized_json} />
            <JsonBlock title="Error" data={entry.error_json} />
          </div>
        </article>
      ))}
    </div>
  );
}

function JsonBlock({
  title,
  data,
}: {
  title: string;
  data?: Record<string, unknown> | null;
}) {
  return (
    <div className="rounded border border-border bg-background/50 p-2">
      <div className="mb-1 text-[10px] uppercase tracking-wider text-muted">{title}</div>
      {data && Object.keys(data).length ? (
        <ul className="space-y-0.5 font-mono text-[11px] text-foreground">
          {Object.entries(data)
            .slice(0, 6)
            .map(([k, v]) => (
              <li key={k} className="flex justify-between gap-2">
                <span className="truncate text-muted">{k}</span>
                <span>
                  {typeof v === "number" ? formatNumber(v) : String(v ?? "—")}
                </span>
              </li>
            ))}
        </ul>
      ) : (
        <div className="text-muted">Not yet available</div>
      )}
    </div>
  );
}
