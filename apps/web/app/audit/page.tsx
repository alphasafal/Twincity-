"use client";

import { useQuery } from "@tanstack/react-query";
import { EmptyState, PageHeader, Panel, SimulatedBadge } from "@/components/AppShell";
import { api } from "@/lib/api";
import { useBuildingId } from "@/lib/hooks";
import { formatTs } from "@/lib/utils";

export default function AuditPage() {
  const buildingId = useBuildingId();
  const { data = [], isLoading, error } = useQuery({
    queryKey: ["audit", buildingId],
    queryFn: () => api.audit(buildingId!),
    enabled: Boolean(buildingId),
  });

  return (
    <div>
      <PageHeader
        title="Audit log"
        description="Immutable event trail from /api/v1/buildings/{id}/audit."
        actions={<SimulatedBadge label="Demo environment" />}
      />

      {isLoading ? <EmptyState>Loading audit events…</EmptyState> : null}
      {error ? (
        <EmptyState>{error instanceof Error ? error.message : "Failed to load audit"}</EmptyState>
      ) : null}

      {!isLoading && !error && !data.length ? (
        <EmptyState>No audit events for this building yet.</EmptyState>
      ) : null}

      {data.length ? (
        <Panel className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-surface-muted/50 text-[11px] uppercase tracking-wider text-muted">
              <tr>
                <th className="px-3 py-2">Time</th>
                <th className="px-3 py-2">Event</th>
                <th className="px-3 py-2">Entity</th>
                <th className="px-3 py-2">Reason</th>
                <th className="px-3 py-2">User</th>
              </tr>
            </thead>
            <tbody>
              {data.map((event) => (
                <tr key={event.id} className="border-t border-border align-top">
                  <td className="px-3 py-2.5 whitespace-nowrap text-xs text-muted">
                    {formatTs(event.timestamp)}
                  </td>
                  <td className="px-3 py-2.5 font-mono text-xs">{event.event_type}</td>
                  <td className="px-3 py-2.5 text-xs">
                    <div>{event.entity_type}</div>
                    <div className="font-mono text-muted">{event.entity_id || "—"}</div>
                  </td>
                  <td className="px-3 py-2.5 max-w-sm text-xs text-muted">
                    {event.reason || "—"}
                  </td>
                  <td className="px-3 py-2.5 font-mono text-[11px] text-muted">
                    {event.user_id || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      ) : null}
    </div>
  );
}
