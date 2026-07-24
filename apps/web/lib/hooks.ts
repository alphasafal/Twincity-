"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "./api";
import { useAuthStore } from "./auth-store";
import type { BuildingStatus } from "./types";
import { createBuildingSocket } from "./ws";

export function useRequireAuth() {
  const hydrated = useAuthStore((s) => s.hydrated);
  const accessToken = useAuthStore((s) => s.accessToken);
  const user = useAuthStore((s) => s.user);
  return { hydrated, isAuthenticated: Boolean(hydrated && accessToken), user };
}

export function useBuildingId() {
  return useAuthStore((s) => s.buildingId);
}

export function useBuildingStatus(buildingId?: string | null) {
  return useQuery({
    queryKey: ["building-status", buildingId],
    queryFn: () => api.getBuildingStatus(buildingId!),
    enabled: Boolean(buildingId),
    refetchInterval: 15_000,
  });
}

export function useLiveBuilding(buildingId?: string | null) {
  const queryClient = useQueryClient();
  const statusQuery = useBuildingStatus(buildingId);
  const [socketStatus, setSocketStatus] = useState<
    "connecting" | "open" | "closed" | "polling"
  >("closed");

  useEffect(() => {
    if (!buildingId) return;
    const socket = createBuildingSocket({
      buildingId,
      onStatus: setSocketStatus,
      pollFn: async () => {
        const status = await api.getBuildingStatus(buildingId);
        queryClient.setQueryData(["building-status", buildingId], status);
        return status as unknown as Record<string, unknown>;
      },
      onEvent: (event) => {
        const payload = event.payload as { state?: unknown } | undefined;
        if (!payload) return;
        queryClient.setQueryData(
          ["building-status", buildingId],
          (prev: BuildingStatus | undefined) => {
            if (!prev) return prev;
            if (event.event_type === "telemetry.poll") {
              return payload as unknown as BuildingStatus;
            }
            return {
              ...prev,
              state: (payload.state as BuildingStatus["state"]) ?? prev.state,
              live_total_load_kw:
                ((payload.state as { total_building_power_kw?: number } | undefined)
                  ?.total_building_power_kw ?? prev.live_total_load_kw),
            };
          },
        );
      },
    });
    return () => socket.disconnect();
  }, [buildingId, queryClient]);

  return { ...statusQuery, socketStatus };
}

export function useZones(buildingId?: string | null) {
  return useQuery({
    queryKey: ["zones", buildingId],
    queryFn: () => api.listZones(buildingId!),
    enabled: Boolean(buildingId),
  });
}
