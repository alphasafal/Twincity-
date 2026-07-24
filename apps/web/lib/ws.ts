"use client";

import { getApiBaseUrl } from "./api";
import { getStoredAccessToken } from "./auth-store";

export type WsEventHandler = (event: Record<string, unknown>) => void;

export interface TwinPilotSocketOptions {
  buildingId: string;
  onEvent: WsEventHandler;
  onStatus?: (status: "connecting" | "open" | "closed" | "polling") => void;
  /** Polling fallback interval when websocket is unavailable */
  pollIntervalMs?: number;
  /** Optional poll fetcher used as fallback */
  pollFn?: () => Promise<Record<string, unknown> | null>;
  maxBackoffMs?: number;
}

/**
 * WebSocket client with exponential reconnect and HTTP polling fallback.
 * Endpoint: ws(s)://{API}/ws/buildings/{buildingId}
 */
export class TwinPilotSocket {
  private ws: WebSocket | null = null;
  private closedByUser = false;
  private attempt = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pollTimer: ReturnType<typeof setInterval> | null = null;
  private readonly options: Required<
    Pick<TwinPilotSocketOptions, "pollIntervalMs" | "maxBackoffMs">
  > &
    TwinPilotSocketOptions;

  constructor(options: TwinPilotSocketOptions) {
    this.options = {
      pollIntervalMs: 5000,
      maxBackoffMs: 30000,
      ...options,
    };
  }

  connect() {
    this.closedByUser = false;
    this.stopPolling();
    this.options.onStatus?.("connecting");

    const base = getApiBaseUrl().replace(/^http/, "ws");
    const token = getStoredAccessToken();
    const url = token
      ? `${base}/ws/buildings/${this.options.buildingId}?token=${encodeURIComponent(token)}`
      : `${base}/ws/buildings/${this.options.buildingId}`;

    try {
      this.ws = new WebSocket(url);
    } catch {
      this.startPolling();
      return;
    }

    this.ws.onopen = () => {
      this.attempt = 0;
      this.options.onStatus?.("open");
      this.stopPolling();
    };

    this.ws.onmessage = (msg) => {
      try {
        const data = JSON.parse(String(msg.data)) as Record<string, unknown>;
        this.options.onEvent(data);
      } catch {
        // ignore malformed frames
      }
    };

    this.ws.onerror = () => {
      // onclose will handle reconnect / fallback
    };

    this.ws.onclose = () => {
      this.ws = null;
      if (this.closedByUser) {
        this.options.onStatus?.("closed");
        return;
      }
      this.scheduleReconnect();
    };
  }

  private scheduleReconnect() {
    this.attempt += 1;
    if (this.attempt >= 3) {
      this.startPolling();
    }
    const delay = Math.min(
      1000 * 2 ** Math.min(this.attempt, 5),
      this.options.maxBackoffMs,
    );
    this.reconnectTimer = setTimeout(() => {
      if (!this.closedByUser) this.connect();
    }, delay);
  }

  private startPolling() {
    if (this.pollTimer || !this.options.pollFn) {
      this.options.onStatus?.("polling");
      return;
    }
    this.options.onStatus?.("polling");
    const run = async () => {
      try {
        const data = await this.options.pollFn?.();
        if (data) {
          this.options.onEvent({
            event_type: "telemetry.poll",
            payload: data,
            building_id: this.options.buildingId,
          });
        }
      } catch {
        // keep trying
      }
    };
    void run();
    this.pollTimer = setInterval(() => void run(), this.options.pollIntervalMs);
  }

  private stopPolling() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }

  disconnect() {
    this.closedByUser = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.stopPolling();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.options.onStatus?.("closed");
  }
}

export function createBuildingSocket(options: TwinPilotSocketOptions) {
  const socket = new TwinPilotSocket(options);
  socket.connect();
  return socket;
}
