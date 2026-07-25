/** Shared TwinPilot frontend config helpers. */

export const DEFAULT_API_URL = "http://localhost:8000";

export function resolveApiUrl(envValue?: string | null): string {
  const raw = (envValue ?? DEFAULT_API_URL).trim();
  return raw.replace(/\/$/, "");
}

export function resolveWsUrl(apiUrl: string, buildingId: string): string {
  const base = apiUrl.replace(/^http/i, (m) => (m.toLowerCase() === "https" ? "wss" : "ws"));
  return `${base.replace(/\/$/, "")}/ws/buildings/${buildingId}`;
}

export const APP_NAME = "TwinPilot";
export const APP_TAGLINE = "Autonomous optimization you can verify.";
