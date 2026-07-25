import NetInfo from "@react-native-community/netinfo";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { api } from "./api";
import { useAuthStore } from "./auth-store";
import { useOfflineStore } from "./offline-store";

export function useRequireAuth() {
  const hydrated = useAuthStore((s) => s.hydrated);
  const accessToken = useAuthStore((s) => s.accessToken);
  const user = useAuthStore((s) => s.user);
  return { hydrated, isAuthenticated: Boolean(hydrated && accessToken), user };
}

export function useBuildingId() {
  return useAuthStore((s) => s.buildingId);
}

export function useNetworkMonitor() {
  const setOnline = useOfflineStore((s) => s.setOnline);

  useEffect(() => {
    const unsub = NetInfo.addEventListener((state) => {
      const online = Boolean(state.isConnected && state.isInternetReachable !== false);
      setOnline(online);
    });
    return () => unsub();
  }, [setOnline]);
}

export function useBuildingStatus(buildingId?: string | null) {
  const isOnline = useOfflineStore((s) => s.isOnline);
  const cacheStatus = useOfflineStore((s) => s.cacheStatus);
  const cachedStatus = useOfflineStore((s) => s.cachedStatus);

  const query = useQuery({
    queryKey: ["building-status", buildingId],
    queryFn: async () => {
      const status = await api.getBuildingStatus(buildingId!);
      cacheStatus(status);
      return status;
    },
    enabled: Boolean(buildingId) && isOnline,
    refetchInterval: isOnline ? 15_000 : false,
    placeholderData: cachedStatus ?? undefined,
  });

  return {
    ...query,
    data: isOnline ? query.data ?? cachedStatus : cachedStatus ?? query.data,
  };
}

export function useZones(buildingId?: string | null) {
  const isOnline = useOfflineStore((s) => s.isOnline);
  return useQuery({
    queryKey: ["zones", buildingId],
    queryFn: () => api.listZones(buildingId!),
    enabled: Boolean(buildingId) && isOnline,
  });
}

export function useAlerts(buildingId?: string | null) {
  const isOnline = useOfflineStore((s) => s.isOnline);
  return useQuery({
    queryKey: ["alerts", buildingId],
    queryFn: () => api.listAlerts(buildingId!),
    enabled: Boolean(buildingId) && isOnline,
    refetchInterval: isOnline ? 20_000 : false,
  });
}

export function useDecisions(buildingId?: string | null, status?: string) {
  const isOnline = useOfflineStore((s) => s.isOnline);
  return useQuery({
    queryKey: ["decisions", buildingId, status],
    queryFn: () => api.listDecisions(buildingId!, status),
    enabled: Boolean(buildingId) && isOnline,
    refetchInterval: isOnline ? 20_000 : false,
  });
}

export function useInvalidateBuilding() {
  const queryClient = useQueryClient();
  return (buildingId?: string | null) => {
    if (!buildingId) return;
    void queryClient.invalidateQueries({ queryKey: ["building-status", buildingId] });
    void queryClient.invalidateQueries({ queryKey: ["decisions", buildingId] });
    void queryClient.invalidateQueries({ queryKey: ["alerts", buildingId] });
  };
}
