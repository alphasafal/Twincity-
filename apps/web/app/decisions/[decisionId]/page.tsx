"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { EmptyState, PageHeader, Panel, SimulatedBadge } from "@/components/AppShell";
import { OperatingModeBadge } from "@/components/OperatingModeBadge";
import { api } from "@/lib/api";
import { formatPct, formatTs } from "@/lib/utils";

export default function DecisionDetailPage() {
  const params = useParams<{ decisionId: string }>();
  const decisionId = params.decisionId;

  const decisionQuery = useQuery({
    queryKey: ["decision", decisionId],
    queryFn: () => api.getDecision(decisionId),
    enabled: Boolean(decisionId),
  });

  const explainQuery = useQuery({
    queryKey: ["decision-explain", decisionId],
    queryFn: () => api.explainDecision(decisionId),
    enabled: Boolean(decisionId),
  });

  const d = decisionQuery.data;

  return (
    <div>
      <PageHeader
        title="Decision detail"
        description="Full decision record and assistant explanation from the API."
        actions={<SimulatedBadge />}
      />

      {decisionQuery.error ? (
        <EmptyState>
          {decisionQuery.error instanceof Error
            ? decisionQuery.error.message
            : "Failed to load decision"}
        </EmptyState>
      ) : null}

      {decisionQuery.isLoading ? <EmptyState>Loading decision…</EmptyState> : null}

      {d ? (
        <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
          <Panel className="space-y-3 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <OperatingModeBadge mode={d.mode} />
              <span className="font-mono text-[11px] uppercase tracking-wider text-muted">
                {d.execution_status}
              </span>
              <span className="text-xs text-muted">{formatTs(d.created_at)}</span>
            </div>
            <p className="text-sm">{d.explanation || "No explanation stored."}</p>
            <dl className="grid gap-2 text-sm sm:grid-cols-2">
              <Row label="Trigger" value={d.trigger} />
              <Row label="Confidence" value={formatPct(d.confidence * 100, 0)} />
              <Row label="Validation" value={d.validation_status} />
              <Row label="Rollback" value={d.rollback_status || "—"} />
              <Row label="Plan" value={d.selected_plan_id || "—"} />
              <Row label="Executed" value={formatTs(d.executed_at)} />
            </dl>
            <div className="grid gap-2 sm:grid-cols-2">
              <Json title="Predicted" data={d.predicted_metrics_json} />
              <Json title="Realized" data={d.realized_metrics_json} />
              <Json title="Applied action" data={d.applied_action_json} />
              <Json title="Prediction error" data={d.prediction_error_json} />
            </div>
          </Panel>

          <Panel className="p-4">
            <h2 className="mb-2 text-sm font-semibold text-ai">Assistant explanation</h2>
            {explainQuery.isLoading ? (
              <p className="text-sm text-muted">Requesting explanation…</p>
            ) : explainQuery.error ? (
              <p className="text-sm text-critical">
                {explainQuery.error instanceof Error
                  ? explainQuery.error.message
                  : "Explanation unavailable"}
              </p>
            ) : (
              <div className="space-y-2 text-sm">
                {explainQuery.data?.summary ? (
                  <p className="font-medium">{String(explainQuery.data.summary)}</p>
                ) : null}
                {explainQuery.data?.explanation ? (
                  <p className="text-muted">{String(explainQuery.data.explanation)}</p>
                ) : (
                  <pre className="overflow-x-auto rounded bg-background/50 p-3 font-mono text-[11px] text-muted">
                    {JSON.stringify(explainQuery.data, null, 2)}
                  </pre>
                )}
              </div>
            )}
          </Panel>
        </div>
      ) : null}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-border/70 bg-background/40 px-3 py-2">
      <dt className="text-[10px] uppercase tracking-wider text-muted">{label}</dt>
      <dd className="font-mono text-xs">{value}</dd>
    </div>
  );
}

function Json({
  title,
  data,
}: {
  title: string;
  data?: Record<string, unknown> | null;
}) {
  return (
    <div className="rounded border border-border bg-background/40 p-3">
      <div className="mb-1 text-[10px] uppercase tracking-wider text-muted">{title}</div>
      <pre className="overflow-x-auto font-mono text-[11px] text-muted">
        {data ? JSON.stringify(data, null, 2) : "—"}
      </pre>
    </div>
  );
}
