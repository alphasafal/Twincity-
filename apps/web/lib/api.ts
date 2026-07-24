"use client";

import {
  getStoredAccessToken,
  getStoredRefreshToken,
  useAuthStore,
} from "./auth-store";
import type {
  Alert,
  AssistantAnswer,
  AuditEvent,
  Building,
  BuildingStatus,
  ConnectorProfile,
  ConstraintPolicy,
  ControlPlan,
  Decision,
  DemoScenario,
  GoalProfile,
  LedgerEntry,
  MvReport,
  Organization,
  PointMapping,
  SubscriptionInfo,
  TokenResponse,
  User,
  Zone,
} from "./types";

const DEFAULT_API_URL = "http://localhost:8000";

export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL;
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
        useAuthStore.getState().logout();
        return null;
      }
      const data = (await res.json()) as TokenResponse;
      useAuthStore.getState().setTokens(data.access_token, data.refresh_token);
      return data.access_token;
    } catch {
      useAuthStore.getState().logout();
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
  getBuilding(buildingId: string) {
    return apiFetch<Building>(`/api/v1/buildings/${buildingId}`);
  },
  getBuildingStatus(buildingId: string) {
    return apiFetch<BuildingStatus>(`/api/v1/buildings/${buildingId}/status`);
  },
  patchMode(buildingId: string, mode: string, reason: string) {
    return apiFetch<Building>(`/api/v1/buildings/${buildingId}/mode`, {
      method: "PATCH",
      body: JSON.stringify({ mode, reason }),
    });
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
  zoneOverride(
    zoneId: string,
    payload: {
      value: number;
      duration_minutes: number;
      reason: string;
      confirm: boolean;
    },
  ) {
    return apiFetch<Record<string, unknown>>(`/api/v1/zones/${zoneId}/override`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  telemetryLatest(buildingId: string) {
    return apiFetch<{ building_id: string; state: unknown; simulated: boolean }>(
      `/api/v1/buildings/${buildingId}/telemetry/latest`,
    );
  },
  telemetryHistory(buildingId: string, metric = "total_building_power_kw", limit = 200) {
    return apiFetch<
      Array<{ timestamp: string; value: number; unit: string; quality: string }>
    >(
      `/api/v1/buildings/${buildingId}/telemetry/history?metric=${encodeURIComponent(metric)}&limit=${limit}`,
    );
  },
  generateOptimization(
    buildingId: string,
    weights: Record<string, number | boolean | null | undefined>,
  ) {
    return apiFetch<{ plans: ControlPlan[]; weights: Record<string, number>; simulated: boolean }>(
      `/api/v1/buildings/${buildingId}/optimization/generate`,
      { method: "POST", body: JSON.stringify(weights) },
    );
  },
  getPlan(planId: string) {
    return apiFetch<ControlPlan>(`/api/v1/control-plans/${planId}`);
  },
  simulatePlan(planId: string) {
    return apiFetch<Record<string, unknown>>(`/api/v1/control-plans/${planId}/simulate`, {
      method: "POST",
    });
  },
  validatePlan(planId: string) {
    return apiFetch<Record<string, unknown>>(`/api/v1/control-plans/${planId}/validate`, {
      method: "POST",
    });
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
  applyPlan(planId: string) {
    return apiFetch<Record<string, unknown>>(`/api/v1/control-plans/${planId}/apply`, {
      method: "POST",
    });
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
  alertNotes(alertId: string, note: string, assign_to?: string) {
    return apiFetch<{ status: string; notes: unknown[] }>(
      `/api/v1/alerts/${alertId}/notes`,
      { method: "POST", body: JSON.stringify({ note, assign_to }) },
    );
  },
  analyticsSummary(buildingId: string) {
    return apiFetch<Record<string, unknown>>(
      `/api/v1/buildings/${buildingId}/analytics/summary`,
    );
  },
  analyticsTimeseries(buildingId: string) {
    return apiFetch<{ building_id: string; points: Array<Record<string, unknown>>; label: string }>(
      `/api/v1/buildings/${buildingId}/analytics/timeseries`,
    );
  },
  analyticsExport(buildingId: string) {
    return apiFetch<{ filename: string; csv: string }>(
      `/api/v1/buildings/${buildingId}/analytics/export`,
    );
  },
  ledger(buildingId: string) {
    return apiFetch<LedgerEntry[]>(`/api/v1/buildings/${buildingId}/ledger`);
  },
  audit(buildingId: string) {
    return apiFetch<AuditEvent[]>(`/api/v1/buildings/${buildingId}/audit`);
  },
  demoScenarios() {
    return apiFetch<DemoScenario[]>("/api/v1/demo/scenarios");
  },
  startScenario(scenarioId: string) {
    return apiFetch<Record<string, unknown>>(`/api/v1/demo/scenarios/${scenarioId}/start`, {
      method: "POST",
    });
  },
  resetScenarios() {
    return apiFetch<Record<string, unknown>>("/api/v1/demo/scenarios/reset", {
      method: "POST",
    });
  },
  demoSpeed(speed: number) {
    return apiFetch<{ speed: number }>("/api/v1/demo/speed", {
      method: "POST",
      body: JSON.stringify({ speed }),
    });
  },
  demoPlayback(action: "pause" | "resume" | "step" | "reset") {
    return apiFetch<{ action: string; state?: unknown }>(
      `/api/v1/demo/playback/${action}`,
      { method: "POST" },
    );
  },
  whatIf(buildingId: string, payload: Record<string, unknown>) {
    return apiFetch<Record<string, unknown>>(
      `/api/v1/buildings/${buildingId}/what-if`,
      { method: "POST", body: JSON.stringify(payload) },
    );
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
  listConversations() {
    return apiFetch<Array<{ id: string; title: string; building_id: string }>>(
      "/api/v1/assistant/conversations",
    );
  },
  getConversation(conversationId: string) {
    return apiFetch<{ id: string; title: string; messages: unknown[] }>(
      `/api/v1/assistant/conversations/${conversationId}`,
    );
  },
  getConstraints(buildingId: string) {
    return apiFetch<ConstraintPolicy>(`/api/v1/buildings/${buildingId}/constraints`);
  },
  updateConstraints(
    buildingId: string,
    body: Partial<ConstraintPolicy> & { reason: string },
  ) {
    return apiFetch<ConstraintPolicy>(`/api/v1/buildings/${buildingId}/constraints`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  },
  updateBuilding(
    buildingId: string,
    body: Partial<
      Pick<Building, "name" | "location" | "timezone" | "area_m2" | "building_type">
    > & { reason: string },
  ) {
    return apiFetch<Building>(`/api/v1/buildings/${buildingId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  },
  getGoals(buildingId: string) {
    return apiFetch<GoalProfile>(`/api/v1/buildings/${buildingId}/goals`);
  },
  updateGoals(
    buildingId: string,
    body: Partial<GoalProfile> & { reason: string },
  ) {
    return apiFetch<GoalProfile>(`/api/v1/buildings/${buildingId}/goals`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  },
  listUsers() {
    return apiFetch<User[]>("/api/v1/users");
  },
  createUser(body: {
    name: string;
    email: string;
    password: string;
    role: string;
    reason: string;
  }) {
    return apiFetch<User>("/api/v1/users", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  updateUser(
    userId: string,
    body: { name?: string; role?: string; is_active?: boolean; reason: string },
  ) {
    return apiFetch<User>(`/api/v1/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  },
  health() {
    return apiFetch<Record<string, unknown>>("/health", { auth: false });
  },
  listOrganizations() {
    return apiFetch<Organization[]>("/api/v1/organizations");
  },
  getSubscription(organizationId: string) {
    return apiFetch<SubscriptionInfo>(
      `/api/v1/organizations/${organizationId}/subscription`,
    );
  },
  listBillingPlans() {
    return apiFetch<{ plans: Record<string, Record<string, unknown>> }>(
      "/api/v1/billing/plans",
    );
  },
  checkout(organizationId: string, plan_code: string) {
    return apiFetch<{ mode: string; checkout_url?: string; message?: string }>(
      `/api/v1/organizations/${organizationId}/billing/checkout`,
      { method: "POST", body: JSON.stringify({ plan_code }) },
    );
  },
  billingPortal(organizationId: string) {
    return apiFetch<{ mode: string; portal_url?: string }>(
      `/api/v1/organizations/${organizationId}/billing/portal`,
      { method: "POST" },
    );
  },
  listOrgMembers(organizationId: string) {
    return apiFetch<
      Array<{
        id: string;
        organization_id: string;
        user_id: string;
        org_role: string;
        is_active: boolean;
        user?: User | null;
      }>
    >(`/api/v1/organizations/${organizationId}/members`);
  },
  inviteMember(
    organizationId: string,
    body: { email: string; org_role: string; reason: string },
  ) {
    return apiFetch<{ id: string; token?: string; email: string; status: string }>(
      `/api/v1/organizations/${organizationId}/invitations`,
      { method: "POST", body: JSON.stringify(body) },
    );
  },
  listConnectors(buildingId: string) {
    return apiFetch<ConnectorProfile[]>(
      `/api/v1/buildings/${buildingId}/connectors`,
    );
  },
  createConnector(
    buildingId: string,
    body: {
      building_id: string;
      adapter_type: string;
      name: string;
      config_json?: Record<string, unknown>;
      secret?: string;
    },
  ) {
    return apiFetch<ConnectorProfile>(
      `/api/v1/buildings/${buildingId}/connectors`,
      { method: "POST", body: JSON.stringify(body) },
    );
  },
  discoverPoints(buildingId: string, connectorId: string) {
    return apiFetch<{
      adapter_type: string;
      points: Array<Record<string, unknown>>;
      health: Record<string, unknown>;
    }>(`/api/v1/buildings/${buildingId}/connectors/${connectorId}/discover`, {
      method: "POST",
    });
  },
  listPointMappings(buildingId: string) {
    return apiFetch<PointMapping[]>(
      `/api/v1/buildings/${buildingId}/point-mappings`,
    );
  },
  upsertPointMappings(
    buildingId: string,
    mappings: Array<{
      external_point_id: string;
      external_point_name?: string;
      zone_id?: string | null;
      twinpilot_metric: string;
      direction?: string;
      unit?: string;
      enabled?: boolean;
    }>,
  ) {
    return apiFetch<PointMapping[]>(
      `/api/v1/buildings/${buildingId}/point-mappings`,
      { method: "PUT", body: JSON.stringify(mappings) },
    );
  },
  pollConnector(buildingId: string) {
    return apiFetch<Record<string, unknown>>(
      `/api/v1/buildings/${buildingId}/connectors/poll`,
      { method: "POST" },
    );
  },
  getCertification(buildingId: string) {
    return apiFetch<Record<string, unknown>>(
      `/api/v1/buildings/${buildingId}/certification`,
    );
  },
  updateCertification(
    buildingId: string,
    body: {
      checklist_json?: Record<string, unknown>;
      shadow_mode_complete?: boolean;
      guarded_pilot_complete?: boolean;
      autonomy_approved?: boolean;
      notes?: string;
      reason: string;
    },
  ) {
    return apiFetch<Record<string, unknown>>(
      `/api/v1/buildings/${buildingId}/certification`,
      { method: "PUT", body: JSON.stringify(body) },
    );
  },
  setOnboardingStage(
    buildingId: string,
    stage: string,
    reason: string,
  ) {
    return apiFetch<Record<string, unknown>>(
      `/api/v1/buildings/${buildingId}/onboarding`,
      { method: "PATCH", body: JSON.stringify({ stage, reason }) },
    );
  },
  getMvReport(buildingId: string) {
    return apiFetch<MvReport>(`/api/v1/buildings/${buildingId}/mv/report`);
  },
  exportOrgAudit(organizationId: string) {
    return apiFetch<{ count: number; events: unknown[] }>(
      `/api/v1/organizations/${organizationId}/audit/export`,
    );
  },
};
