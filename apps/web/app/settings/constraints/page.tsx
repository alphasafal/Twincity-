"use client";

import { useQuery } from "@tanstack/react-query";
import {
  EmptyState,
  PageHeader,
  Panel,
  SettingsSubnav,
} from "@/components/AppShell";
import { api } from "@/lib/api";
import { useBuildingId } from "@/lib/hooks";
import { formatNumber } from "@/lib/utils";

export default function ConstraintsSettingsPage() {
  const buildingId = useBuildingId();
  const { data, isLoading, error } = useQuery({
    queryKey: ["constraints", buildingId],
    queryFn: () => api.getConstraints(buildingId!),
    enabled: Boolean(buildingId),
  });

  return (
    <div>
      <PageHeader
        title="Constraint policy"
        description="Hard limits enforced by the Safety Shield before any control write."
      />
      <SettingsSubnav />

      {isLoading ? <EmptyState>Loading constraints…</EmptyState> : null}
      {error ? (
        <EmptyState>{error instanceof Error ? error.message : "Failed to load"}</EmptyState>
      ) : null}

      {data ? (
        <Panel className="p-4">
          <dl className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            <Row label="Min cooling SP" value={`${formatNumber(data.min_cooling_setpoint)} °C`} />
            <Row label="Max cooling SP" value={`${formatNumber(data.max_cooling_setpoint)} °C`} />
            <Row label="Min heating SP" value={`${formatNumber(data.min_heating_setpoint)} °C`} />
            <Row label="Max heating SP" value={`${formatNumber(data.max_heating_setpoint)} °C`} />
            <Row
              label="Max SP change / interval"
              value={`${formatNumber(data.max_setpoint_change_per_interval)} °C`}
            />
            <Row label="Min ventilation" value={formatNumber(data.minimum_ventilation)} />
            <Row
              label="Max control duration"
              value={`${formatNumber(data.maximum_control_duration, 0)} min`}
            />
            <Row
              label="Min autonomy confidence"
              value={formatNumber(data.minimum_confidence_for_autonomy, 2)}
            />
            <Row
              label="Max data age"
              value={`${formatNumber(data.maximum_data_age_seconds, 0)} s`}
            />
          </dl>
          <p className="mt-4 text-xs text-muted">
            Constraint updates are not exposed by a PATCH endpoint yet. Values are read-only in
            this UI.
          </p>
          <button
            type="button"
            disabled
            className="mt-3 cursor-not-allowed rounded-md border border-border px-3 py-2 text-sm text-muted opacity-50"
          >
            Save constraints (unavailable)
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
