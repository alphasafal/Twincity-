import {
  getStoredAccessToken,
  getStoredRefreshToken,
  useAuthStore,
} from "./auth-store";
import type {
  Alert,
  AssistantAnswer,
  Building,
  BuildingStatus,
  ControlPlan,
  Decision,
  TokenResponse,
  User,
  Zone,
} from "./types";

const DEFAULT_API_URL = "http://localhost:8000";

export function getApiBaseUrl(): string {
  return process.env.EXPO_PUBLIC_API_URL || DEFAULT_API_URL;
}

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown, message?: string) {
    super(message || `API error ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const refresh = getStoredRefreshToken();
    if (!refresh) return null;
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!res.ok) {
        await useAuthStore.getState().logout();
        return null;
      }
      const data = (await res.json()) as TokenResponse;
      await useAuthStore.getState().setTokens(data.access_token, data.refresh_token);
      return data.access_token;
    } catch {
      await useAuthStore.getState().logout();
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

export type ApiFetchOptions = RequestInit & {
  auth?: boolean;
  retry?: boolean;
};

export async function apiFetch<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const { auth = true, retry = true, headers, ...rest } = options;
  const url = path.startsWith("http") ? path : `${getApiBaseUrl()}${path}`;
  const finalHeaders = new Headers(headers || {});

  if (!finalHeaders.has("Content-Type") && rest.body) {
    finalHeaders.set("Content-Type", "application/json");
  }

  if (auth) {
    const token = getStoredAccessToken();
    if (token) finalHeaders.set("Authorization", `Bearer ${token}`);
  }

  let res = await fetch(url, { ...rest, headers: finalHeaders });

  if (res.status === 401 && auth && retry) {
    const next = await refreshAccessToken();
    if (next) {
      finalHeaders.set("Authorization", `Bearer ${next}`);
      res = await fetch(url, { ...rest, headers: finalHeaders });
    }
  }

  if (!res.ok) {
    let detail: unknown = null;
    try {
      detail = await res.json();
    } catch {
      detail = await res.text();
    }
    const message =
      typeof detail === "object" && detail && "detail" in detail
        ? String((detail as { detail: unknown }).detail)
        : `Request failed (${res.status})`;
    throw new ApiError(res.status, detail, message);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  login(email: string, password: string) {
    return apiFetch<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      auth: false,
      body: JSON.stringify({ email, password }),
    });
  },
  logout() {
    return apiFetch<{ status: string }>("/api/v1/auth/logout", {
      method: "POST",
    });
  },
  me() {
    return apiFetch<User>("/api/v1/auth/me");
  },
  listBuildings() {
    return apiFetch<Building[]>("/api/v1/buildings");
  },
  getBuildingStatus(buildingId: string) {
    return apiFetch<BuildingStatus>(`/api/v1/buildings/${buildingId}/status`);
  },
  listZones(buildingId: string) {
    return apiFetch<Zone[]>(`/api/v1/buildings/${buildingId}/zones`);
  },
  getZone(zoneId: string) {
    return apiFetch<Zone>(`/api/v1/zones/${zoneId}`);
  },
  zoneTelemetry(zoneId: string, limit = 100) {
    return apiFetch<
      Array<{
        metric: string;
        value: number;
        unit: string;
        timestamp: string;
        quality: string;
      }>
    >(`/api/v1/zones/${zoneId}/telemetry?limit=${limit}`);
  },
  zoneHealth(zoneId: string) {
    return apiFetch<{
      zone_id: string;
      name: string;
      sensor_health?: number;
      sensor_failed?: boolean;
      data_freshness_seconds?: number;
      comfort_status?: string;
      estimated_temperature?: number;
      live?: Record<string, unknown>;
    }>(`/api/v1/zones/${zoneId}/health`);
  },
  telemetryHistory(buildingId: string, metric = "total_building_power_kw", limit = 60) {
    return apiFetch<
      Array<{ timestamp: string; value: number; unit: string; quality: string }>
    >(
      `/api/v1/buildings/${buildingId}/telemetry/history?metric=${encodeURIComponent(metric)}&limit=${limit}`,
    );
  },
  getPlan(planId: string) {
    return apiFetch<ControlPlan>(`/api/v1/control-plans/${planId}`);
  },
  approvePlan(planId: string, reason: string) {
    return apiFetch<Record<string, unknown>>(`/api/v1/control-plans/${planId}/approve`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  },
  rejectPlan(planId: string, reason: string) {
    return apiFetch<Record<string, unknown>>(`/api/v1/control-plans/${planId}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  },
  requestRevisedPlan(planId: string, reason: string) {
    return api.rejectPlan(planId, `Request revised plan: ${reason}`);
  },
  rollback(buildingId: string, reason: string) {
    return apiFetch<Record<string, unknown>>(`/api/v1/buildings/${buildingId}/rollback`, {
      method: "POST",
      body: JSON.stringify({ reason, target_safe_policy: "default_safe_policy" }),
    });
  },
  listDecisions(buildingId: string, status?: string) {
    const q = status ? `?status=${encodeURIComponent(status)}` : "";
    return apiFetch<Decision[]>(`/api/v1/buildings/${buildingId}/decisions${q}`);
  },
  getDecision(decisionId: string) {
    return apiFetch<Decision>(`/api/v1/decisions/${decisionId}`);
  },
  explainDecision(decisionId: string) {
    return apiFetch<AssistantAnswer>(`/api/v1/decisions/${decisionId}/explanation`);
  },
  listAlerts(buildingId: string) {
    return apiFetch<Alert[]>(`/api/v1/buildings/${buildingId}/alerts`);
  },
  ackAlert(alertId: string) {
    return apiFetch<{ status: string }>(`/api/v1/alerts/${alertId}/acknowledge`, {
      method: "PATCH",
    });
  },
  resolveAlert(alertId: string) {
    return apiFetch<{ status: string }>(`/api/v1/alerts/${alertId}/resolve`, {
      method: "PATCH",
    });
  },
  assistantChat(buildingId: string, message: string, conversationId?: string) {
    return apiFetch<{
      conversation_id: string;
      answer: AssistantAnswer;
      evidence: Record<string, unknown>;
    }>("/api/v1/assistant/chat", {
      method: "POST",
      body: JSON.stringify({
        building_id: buildingId,
        message,
        conversation_id: conversationId,
      }),
    });
  },
  health() {
    return apiFetch<Record<string, unknown>>("/health", { auth: false });
  },
};
