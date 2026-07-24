/**
 * Thin typed TwinPilot REST client stubs.
 * Apps may continue using their local fetch wrappers; this package is the
 * shared surface for scripts and future consolidation.
 */

import type { OperatingMode, TokenResponse, WsEventEnvelope } from "@twinpilot/contracts";

export type TwinPilotClientOptions = {
  baseUrl?: string;
  getAccessToken?: () => string | null | undefined;
  fetchImpl?: typeof fetch;
};

export class TwinPilotApiClient {
  readonly baseUrl: string;
  private readonly getAccessToken?: () => string | null | undefined;
  private readonly fetchImpl: typeof fetch;

  constructor(options: TwinPilotClientOptions = {}) {
    this.baseUrl = (options.baseUrl ?? "http://localhost:8000").replace(/\/$/, "");
    this.getAccessToken = options.getAccessToken;
    this.fetchImpl = options.fetchImpl ?? fetch.bind(globalThis);
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    if (init.body && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    const token = this.getAccessToken?.();
    if (token) headers.set("Authorization", `Bearer ${token}`);

    const res = await this.fetchImpl(`${this.baseUrl}${path}`, { ...init, headers });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`TwinPilot API ${res.status}: ${text}`);
    }
    if (res.status === 204) return undefined as T;
    return (await res.json()) as T;
  }

  health() {
    return this.request<{ status: string; demo_mode?: boolean }>("/health");
  }

  login(email: string, password: string) {
    return this.request<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  }

  me() {
    return this.request<Record<string, unknown>>("/api/v1/auth/me");
  }

  listBuildings() {
    return this.request<Array<{ id: string; name: string; current_mode: OperatingMode | string }>>(
      "/api/v1/buildings",
    );
  }

  buildingStatus(buildingId: string) {
    return this.request<Record<string, unknown>>(`/api/v1/buildings/${buildingId}/status`);
  }

  generateOptimization(
    buildingId: string,
    body: Record<string, number | boolean | null | undefined> = {},
  ) {
    return this.request<{ plans: unknown[] }>(
      `/api/v1/buildings/${buildingId}/optimization/generate`,
      { method: "POST", body: JSON.stringify(body) },
    );
  }

  validatePlan(planId: string) {
    return this.request<Record<string, unknown>>(`/api/v1/control-plans/${planId}/validate`, {
      method: "POST",
    });
  }

  /** Helper type re-export for consumers parsing WS JSON. */
  static asWsEvent(data: unknown): WsEventEnvelope {
    return data as WsEventEnvelope;
  }
}

export function createApiClient(options?: TwinPilotClientOptions) {
  return new TwinPilotApiClient(options);
}
