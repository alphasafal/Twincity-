"use client";

import Link from "next/link";
import type { Zone, ZoneLiveState } from "@/lib/types";
import { cn, comfortColor, formatNumber } from "@/lib/utils";

const LAYOUT: Record<string, string> = {
  north: "col-start-2 row-start-1",
  west: "col-start-1 row-start-2",
  core: "col-start-2 row-start-2",
  east: "col-start-3 row-start-2",
  south: "col-start-2 row-start-3",
};

export function ZoneMap({
  zones,
  liveZones,
  interactive = true,
  selectedKey,
  onSelect,
}: {
  zones: Zone[];
  liveZones?: Record<string, ZoneLiveState>;
  interactive?: boolean;
  selectedKey?: string | null;
  onSelect?: (zone: Zone) => void;
}) {
  return (
    <div className="grid grid-cols-3 grid-rows-3 gap-2 rounded-lg border border-border bg-graphite-950/40 p-3">
      {zones.map((zone) => {
        const live = liveZones?.[zone.external_key];
        const status = live?.comfort_status || (live?.sensor_failed ? "critical" : "ok");
        const color = comfortColor(status);
        const selected = selectedKey === zone.external_key || selectedKey === zone.id;
        const body = (
          <div
            className={cn(
              "flex h-full min-h-[96px] flex-col justify-between rounded-md border p-3 transition",
              LAYOUT[zone.external_key] || "col-span-1",
              interactive && "hover:brightness-110",
              selected && "ring-2 ring-live/60",
            )}
            style={{
              borderColor: `${color}66`,
              background: `linear-gradient(160deg, ${color}22, transparent 70%)`,
            }}
            onClick={() => onSelect?.(zone)}
            role={interactive ? "button" : undefined}
          >
            <div>
              <div className="text-sm font-medium text-foreground">{zone.name}</div>
              <div className="font-mono text-[10px] uppercase tracking-wider text-muted">
                {zone.external_key}
              </div>
            </div>
            <div className="mt-2 space-y-0.5 font-mono text-xs">
              <div className="text-live">
                {formatNumber(live?.temperature ?? live?.estimated_temperature)}°C
              </div>
              <div className="text-muted">
                SP {formatNumber(live?.cooling_setpoint)} · CO₂ {formatNumber(live?.co2, 0)}
              </div>
              {live?.sensor_failed ? (
                <div className="text-critical">Sensor fault</div>
              ) : (
                <div style={{ color }} className="capitalize">
                  {status || "unknown"}
                </div>
              )}
            </div>
          </div>
        );

        if (!interactive) return <div key={zone.id}>{body}</div>;
        if (onSelect) return <div key={zone.id}>{body}</div>;
        return (
          <Link key={zone.id} href={`/zones/${zone.id}`} className="contents">
            {body}
          </Link>
        );
      })}
    </div>
  );
}
