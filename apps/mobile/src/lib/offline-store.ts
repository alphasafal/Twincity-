import { create } from "zustand";
import type { BuildingStatus } from "./types";

interface OfflineState {
  isOnline: boolean;
  lastUpdatedAt: string | null;
  cachedStatus: BuildingStatus | null;
  setOnline: (online: boolean) => void;
  cacheStatus: (status: BuildingStatus) => void;
}

export const useOfflineStore = create<OfflineState>((set) => ({
  isOnline: true,
  lastUpdatedAt: null,
  cachedStatus: null,
  setOnline: (online) => set({ isOnline: online }),
  cacheStatus: (status) =>
    set({
      cachedStatus: status,
      lastUpdatedAt: new Date().toISOString(),
    }),
}));
