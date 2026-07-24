"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Building, User } from "./types";

const ACCESS_KEY = "twinpilot_access_token";
const REFRESH_KEY = "twinpilot_refresh_token";

function readToken(key: string): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(key);
}

function writeToken(key: string, value: string | null) {
  if (typeof window === "undefined") return;
  if (value) localStorage.setItem(key, value);
  else localStorage.removeItem(key);
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  buildingId: string | null;
  building: Building | null;
  hydrated: boolean;
  setTokens: (access: string, refresh: string) => void;
  setUser: (user: User | null) => void;
  setBuilding: (building: Building | null) => void;
  setHydrated: (value: boolean) => void;
  logout: () => void;
  getAccessToken: () => string | null;
  getRefreshToken: () => string | null;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      buildingId: null,
      building: null,
      hydrated: false,
      setTokens: (access, refresh) => {
        writeToken(ACCESS_KEY, access);
        writeToken(REFRESH_KEY, refresh);
        set({ accessToken: access, refreshToken: refresh });
      },
      setUser: (user) => set({ user }),
      setBuilding: (building) =>
        set({ building, buildingId: building?.id ?? null }),
      setHydrated: (value) => set({ hydrated: value }),
      logout: () => {
        writeToken(ACCESS_KEY, null);
        writeToken(REFRESH_KEY, null);
        set({
          accessToken: null,
          refreshToken: null,
          user: null,
          building: null,
          buildingId: null,
        });
      },
      getAccessToken: () => get().accessToken ?? readToken(ACCESS_KEY),
      getRefreshToken: () => get().refreshToken ?? readToken(REFRESH_KEY),
    }),
    {
      name: "twinpilot-auth",
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
        buildingId: state.buildingId,
        building: state.building,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHydrated(true);
        if (state?.accessToken) writeToken(ACCESS_KEY, state.accessToken);
        if (state?.refreshToken) writeToken(REFRESH_KEY, state.refreshToken);
      },
    },
  ),
);

export function getStoredAccessToken(): string | null {
  return useAuthStore.getState().getAccessToken() ?? readToken(ACCESS_KEY);
}

export function getStoredRefreshToken(): string | null {
  return useAuthStore.getState().getRefreshToken() ?? readToken(REFRESH_KEY);
}
