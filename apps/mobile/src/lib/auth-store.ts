import * as SecureStore from "expo-secure-store";
import { create } from "zustand";
import type { Building, User } from "./types";

const ACCESS_KEY = "twinpilot_access_token";
const REFRESH_KEY = "twinpilot_refresh_token";
const USER_KEY = "twinpilot_user";
const BUILDING_KEY = "twinpilot_building";

async function saveJson(key: string, value: unknown | null) {
  if (value == null) {
    await SecureStore.deleteItemAsync(key);
    return;
  }
  await SecureStore.setItemAsync(key, JSON.stringify(value));
}

async function readJson<T>(key: string): Promise<T | null> {
  const raw = await SecureStore.getItemAsync(key);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  buildingId: string | null;
  building: Building | null;
  hydrated: boolean;
  setTokens: (access: string, refresh: string) => Promise<void>;
  setUser: (user: User | null) => Promise<void>;
  setBuilding: (building: Building | null) => Promise<void>;
  hydrate: () => Promise<void>;
  logout: () => Promise<void>;
  getAccessToken: () => string | null;
  getRefreshToken: () => string | null;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: null,
  refreshToken: null,
  user: null,
  buildingId: null,
  building: null,
  hydrated: false,
  setTokens: async (access, refresh) => {
    await SecureStore.setItemAsync(ACCESS_KEY, access);
    await SecureStore.setItemAsync(REFRESH_KEY, refresh);
    set({ accessToken: access, refreshToken: refresh });
  },
  setUser: async (user) => {
    await saveJson(USER_KEY, user);
    set({ user });
  },
  setBuilding: async (building) => {
    await saveJson(BUILDING_KEY, building);
    set({ building, buildingId: building?.id ?? null });
  },
  hydrate: async () => {
    const [accessToken, refreshToken, user, building] = await Promise.all([
      SecureStore.getItemAsync(ACCESS_KEY),
      SecureStore.getItemAsync(REFRESH_KEY),
      readJson<User>(USER_KEY),
      readJson<Building>(BUILDING_KEY),
    ]);
    set({
      accessToken,
      refreshToken,
      user,
      building,
      buildingId: building?.id ?? null,
      hydrated: true,
    });
  },
  logout: async () => {
    await Promise.all([
      SecureStore.deleteItemAsync(ACCESS_KEY),
      SecureStore.deleteItemAsync(REFRESH_KEY),
      SecureStore.deleteItemAsync(USER_KEY),
      SecureStore.deleteItemAsync(BUILDING_KEY),
    ]);
    set({
      accessToken: null,
      refreshToken: null,
      user: null,
      building: null,
      buildingId: null,
    });
  },
  getAccessToken: () => get().accessToken,
  getRefreshToken: () => get().refreshToken,
}));

export function getStoredAccessToken(): string | null {
  return useAuthStore.getState().getAccessToken();
}

export function getStoredRefreshToken(): string | null {
  return useAuthStore.getState().getRefreshToken();
}
