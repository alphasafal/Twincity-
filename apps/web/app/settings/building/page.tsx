"use client";

import { useQuery } from "@tanstack/react-query";
import {
  EmptyState,
  PageHeader,
  Panel,
  SettingsSubnav,
  SimulatedBadge,
} from "@/components/AppShell";
import { OperatingModeBadge } from "@/components/OperatingModeBadge";
import { api } from "@/lib/api";
import { useBuildingId } from "@/lib/hooks";
import { formatNumber } from "@/lib/utils";

export default function BuildingSettingsPage() {
  const buildingId = useBuildingId();
  const { data, isLoading, error } = useQuery({
    queryKey: ["building", buildingId],
    queryFn: () => api.getBuilding(buildingId!),
    enabled: Boolean(buildingId),
  });

  return (
    <div>
      <PageHeader
        title="Building settings"
        description="Identity and configuration from /api/v1/buildings/{id}."
        actions={data?.is_demo ? <SimulatedBadge label="Demo building" /> : null}
      />
      <SettingsSubnav />

      {isLoading ? <EmptyState>Loading building…</EmptyState> : null}
      {error ? (
        <EmptyState>{error instanceof Error ? error.message : "Failed to load"}</EmptyState>
      ) : null}

      {data ? (
        <Panel className="p-4">
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-semibold">{data.name}</h2>
            <OperatingModeBadge mode={data.current_mode} />
          </div>
          <dl className="grid gap-2 sm:grid-cols-2">
            <Row label="Location" value={data.location} />
            <Row label="Timezone" value={data.timezone} />
            <Row label="Type" value={data.building_type} />
            <Row label="Area" value={`${formatNumber(data.area_m2, 0)} m²`} />
            <Row label="Confidence" value={formatNumber(data.confidence, 2)} />
            <Row label="Building ID" value={data.id} />
          </dl>
          <p className="mt-4 text-xs text-muted">
            Building metadata edits are not available through the current API — display only.
          </p>
          <button
            type="button"
            disabled
            className="mt-3 cursor-not-allowed rounded-md border border-border px-3 py-2 text-sm text-muted opacity-50"
            title="Not implemented by API"
          >
            Edit building details (unavailable)
          </button>
        </Panel>
      ) : null}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-border/70 bg-background/40 px-3 py-2 text-sm">
      <dt className="text-[10px] uppercase tracking-wider text-muted">{label}</dt>
      <dd className="font-mono text-xs">{value}</dd>
    </div>
  );
}
