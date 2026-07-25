"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { EmptyState, PageHeader, SimulatedBadge } from "@/components/AppShell";
import { AlertTable } from "@/components/AlertTable";
import { api } from "@/lib/api";
import { useBuildingId } from "@/lib/hooks";

export default function AlertsPage() {
  const buildingId = useBuildingId();
  const queryClient = useQueryClient();
  const [busyId, setBusyId] = useState<string | null>(null);

  const { data = [], isLoading, error } = useQuery({
    queryKey: ["alerts", buildingId],
    queryFn: () => api.listAlerts(buildingId!),
    enabled: Boolean(buildingId),
    refetchInterval: 15_000,
  });

  const ack = useMutation({
    mutationFn: (id: string) => api.ackAlert(id),
    onMutate: (id) => setBusyId(id),
    onSettled: () => {
      setBusyId(null);
      void queryClient.invalidateQueries({ queryKey: ["alerts", buildingId] });
    },
  });

  const resolve = useMutation({
    mutationFn: (id: string) => api.resolveAlert(id),
    onMutate: (id) => setBusyId(id),
    onSettled: () => {
      setBusyId(null);
      void queryClient.invalidateQueries({ queryKey: ["alerts", buildingId] });
    },
  });

  return (
    <div>
      <PageHeader
        title="Alerts"
        description="Open and historical alerts from /api/v1/buildings/{id}/alerts."
        actions={<SimulatedBadge />}
      />
      {error ? (
        <EmptyState>{error instanceof Error ? error.message : "Failed to load alerts"}</EmptyState>
      ) : null}
      {isLoading ? <EmptyState>Loading alerts…</EmptyState> : null}
      {!isLoading && !error ? (
        <AlertTable
          alerts={data}
          busyId={busyId}
          onAcknowledge={(id) => ack.mutate(id)}
          onResolve={(id) => resolve.mutate(id)}
        />
      ) : null}
    </div>
  );
}
