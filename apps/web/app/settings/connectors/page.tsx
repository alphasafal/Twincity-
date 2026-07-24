"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { EmptyState, PageHeader, Panel, SettingsSubnav } from "@/components/AppShell";
import { api } from "@/lib/api";
import { useBuildingId } from "@/lib/hooks";

const ADAPTERS = ["mock", "bacnet_ip", "modbus_tcp", "honeywell_niagara"] as const;

export default function ConnectorsSettingsPage() {
  const buildingId = useBuildingId();
  const queryClient = useQueryClient();
  const [adapter, setAdapter] = useState<(typeof ADAPTERS)[number]>("bacnet_ip");
  const [name, setName] = useState("Site connector");
  const [host, setHost] = useState("127.0.0.1");
  const [message, setMessage] = useState<string | null>(null);
  const [discovered, setDiscovered] = useState<Array<Record<string, unknown>>>([]);

  const connectors = useQuery({
    queryKey: ["connectors", buildingId],
    queryFn: () => api.listConnectors(buildingId!),
    enabled: Boolean(buildingId),
  });
  const mappings = useQuery({
    queryKey: ["point-mappings", buildingId],
    queryFn: () => api.listPointMappings(buildingId!),
    enabled: Boolean(buildingId),
  });

  const create = useMutation({
    mutationFn: () =>
      api.createConnector(buildingId!, {
        building_id: buildingId!,
        adapter_type: adapter,
        name,
        config_json: {
          host,
          transport: "simulated",
          ...(adapter === "honeywell_niagara"
            ? { base_url: `https://${host}`, station: "TwinPilotDemo" }
            : {}),
        },
      }),
    onSuccess: (profile) => {
      setMessage(
        `Provisioned ${profile.adapter_type}. Site token (once): ${String(
          (profile.config_json as { site_token?: string }).site_token || "n/a",
        )}`,
      );
      void queryClient.invalidateQueries({ queryKey: ["connectors", buildingId] });
    },
    onError: (err) =>
      setMessage(err instanceof Error ? err.message : "Connector create failed"),
  });

  const discover = useMutation({
    mutationFn: (connectorId: string) => api.discoverPoints(buildingId!, connectorId),
    onSuccess: async (result, connectorId) => {
      setDiscovered(result.points || []);
      const mapped = (result.points || []).slice(0, 12).map((p) => ({
        external_point_id: String(p.external_point_id),
        external_point_name: String(p.name || ""),
        twinpilot_metric: String(p.metric_hint || "unknown"),
        direction: p.writable ? "readwrite" : "read",
        unit: String(p.unit || ""),
        enabled: true,
      }));
      await api.upsertPointMappings(buildingId!, mapped);
      setMessage(`Discovered ${result.points.length} points via ${connectorId.slice(0, 8)}…`);
      void queryClient.invalidateQueries({ queryKey: ["point-mappings", buildingId] });
    },
    onError: (err) =>
      setMessage(err instanceof Error ? err.message : "Discover failed"),
  });

  const poll = useMutation({
    mutationFn: () => api.pollConnector(buildingId!),
    onSuccess: (result) =>
      setMessage(`Polled connector — wrote ${String(result.written)} samples`),
    onError: (err) =>
      setMessage(err instanceof Error ? err.message : "Poll failed"),
  });

  if (!buildingId) {
    return (
      <div>
        <PageHeader title="Connectors" />
        <SettingsSubnav />
        <EmptyState>Select a building first.</EmptyState>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Connectors"
        description="Vendor-agnostic BMS adapters (BACnet/IP, Modbus TCP, Honeywell Niagara) with point mapping and commissioning."
      />
      <SettingsSubnav />

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel className="p-4">
          <h2 className="mb-3 text-sm font-semibold">Provision connector</h2>
          <label className="mb-2 block text-xs">
            <span className="mb-1 block text-muted">Adapter</span>
            <select
              value={adapter}
              onChange={(e) => setAdapter(e.target.value as (typeof ADAPTERS)[number])}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            >
              {ADAPTERS.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </label>
          <label className="mb-2 block text-xs">
            <span className="mb-1 block text-muted">Name</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            />
          </label>
          <label className="mb-3 block text-xs">
            <span className="mb-1 block text-muted">Host / base</span>
            <input
              value={host}
              onChange={(e) => setHost(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            />
          </label>
          <button
            type="button"
            onClick={() => create.mutate()}
            className="rounded-md border border-live/40 bg-live/10 px-3 py-1.5 text-xs text-live"
          >
            Create connector
          </button>
        </Panel>

        <Panel className="p-4">
          <h2 className="mb-3 text-sm font-semibold">Installed</h2>
          <ul className="space-y-2 text-sm">
            {(connectors.data || []).map((c) => (
              <li
                key={c.id}
                className="flex items-center justify-between gap-2 rounded border border-border px-3 py-2"
              >
                <div>
                  <div className="font-medium">{c.name}</div>
                  <div className="text-xs text-muted">
                    {c.adapter_type} · {c.status}
                  </div>
                </div>
                <button
                  type="button"
                  className="rounded border border-border px-2 py-1 text-xs"
                  onClick={() => discover.mutate(c.id)}
                >
                  Discover
                </button>
              </li>
            ))}
          </ul>
          <button
            type="button"
            className="mt-3 rounded-md border border-border px-3 py-1.5 text-xs"
            onClick={() => poll.mutate()}
          >
            Poll telemetry now
          </button>
        </Panel>
      </div>

      <Panel className="mt-4 p-4">
        <h2 className="mb-2 text-sm font-semibold">Point mappings</h2>
        <p className="mb-3 text-xs text-muted">
          {(mappings.data || []).length} mapped ·{" "}
          {discovered.length ? `${discovered.length} last discovered` : "discover to import"}
        </p>
        <div className="max-h-64 overflow-auto font-mono text-[11px] text-muted">
          <pre>{JSON.stringify(mappings.data?.slice(0, 20) || [], null, 2)}</pre>
        </div>
      </Panel>
      {message ? <p className="mt-4 text-sm text-muted">{message}</p> : null}
    </div>
  );
}
