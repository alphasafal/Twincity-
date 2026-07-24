"use client";

import Link from "next/link";
import { EmptyState, PageHeader, SimulatedBadge } from "@/components/AppShell";
import { ZoneMap } from "@/components/ZoneMap";
import { useBuildingId, useLiveBuilding, useZones } from "@/lib/hooks";
import { formatNumber } from "@/lib/utils";

export default function ZonesPage() {
  const buildingId = useBuildingId();
  const { data: zones = [], isLoading, error } = useZones(buildingId);
  const { data: status } = useLiveBuilding(buildingId);
  const liveZones = status?.state?.zones || {};

  return (
    <div>
      <PageHeader
        title="Zones"
        description="Building zones from /api/v1/buildings/{id}/zones with live comfort overlay."
        actions={status?.simulated ? <SimulatedBadge /> : null}
      />

      {error ? (
        <EmptyState>{error instanceof Error ? error.message : "Failed to load zones"}</EmptyState>
      ) : null}
      {isLoading ? <EmptyState>Loading zones…</EmptyState> : null}

      {zones.length ? (
        <div className="grid gap-6 xl:grid-cols-[1.2fr_1fr]">
          <ZoneMap zones={zones} liveZones={liveZones} />
          <div className="space-y-2">
            {zones.map((zone) => {
              const live = liveZones[zone.external_key];
              return (
                <Link
                  key={zone.id}
                  href={`/zones/${zone.id}`}
                  className="block rounded-lg border border-border bg-surface/70 px-4 py-3 transition hover:border-live/40"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="font-medium">{zone.name}</div>
                      <div className="text-xs text-muted">
                        Floor {zone.floor} · {formatNumber(zone.area_m2, 0)} m² · cap{" "}
                        {zone.capacity}
                      </div>
                    </div>
                    <div className="text-right font-mono text-sm text-live">
                      {formatNumber(live?.temperature)}°C
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}
