"use client";

import { useQuery } from "@tanstack/react-query";
import { EmptyState, PageHeader, SimulatedBadge } from "@/components/AppShell";
import { DecisionTimeline } from "@/components/DecisionTimeline";
import { api } from "@/lib/api";
import { useBuildingId } from "@/lib/hooks";

export default function DecisionsPage() {
  const buildingId = useBuildingId();
  const { data = [], isLoading, error } = useQuery({
    queryKey: ["decisions", buildingId],
    queryFn: () => api.listDecisions(buildingId!),
    enabled: Boolean(buildingId),
    refetchInterval: 20_000,
  });

  return (
    <div>
      <PageHeader
        title="Decisions"
        description="Execution history from /api/v1/buildings/{id}/decisions."
        actions={<SimulatedBadge label="Predictions may be simulated" />}
      />
      {error ? (
        <EmptyState>{error instanceof Error ? error.message : "Failed to load"}</EmptyState>
      ) : null}
      {isLoading ? <EmptyState>Loading decisions…</EmptyState> : null}
      {!isLoading && !error ? <DecisionTimeline decisions={data} /> : null}
    </div>
  );
}
