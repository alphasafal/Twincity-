"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  EmptyState,
  PageHeader,
  Panel,
  SettingsSubnav,
} from "@/components/AppShell";
import { OperatingModeBadge } from "@/components/OperatingModeBadge";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useBuildingId } from "@/lib/hooks";

const MODES = ["AUTONOMOUS", "GUARDED", "ADVISORY", "FALLBACK", "MANUAL"] as const;

export default function SettingsPage() {
  const buildingId = useBuildingId();
  const setBuilding = useAuthStore((s) => s.setBuilding);
  const building = useAuthStore((s) => s.building);
  const queryClient = useQueryClient();
  const [mode, setMode] = useState(building?.current_mode || "AUTONOMOUS");
  const [reason, setReason] = useState("Operator mode change from settings");
  const [message, setMessage] = useState<string | null>(null);

  const goals = useQuery({
    queryKey: ["goals", buildingId],
    queryFn: () => api.getGoals(buildingId!),
    enabled: Boolean(buildingId),
  });

  const patchMode = useMutation({
    mutationFn: () => api.patchMode(buildingId!, mode, reason),
    onSuccess: (updated) => {
      setBuilding(updated);
      setMessage(`Mode updated to ${updated.current_mode}`);
      void queryClient.invalidateQueries({ queryKey: ["building-status", buildingId] });
    },
    onError: (err) =>
      setMessage(err instanceof Error ? err.message : "Mode change failed"),
  });

  return (
    <div>
      <PageHeader
        title="Settings"
        description="Building mode and goal profile. Constraint and user management live in subpages."
      />
      <SettingsSubnav />

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel className="p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Operating mode</h2>
            <OperatingModeBadge mode={building?.current_mode} />
          </div>
          <label className="mb-3 block text-xs">
            <span className="mb-1 block text-muted">Mode</span>
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            >
              {MODES.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </label>
          <label className="mb-3 block text-xs">
            <span className="mb-1 block text-muted">Reason</span>
            <input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            />
          </label>
          <button
            type="button"
            disabled={!buildingId || reason.trim().length < 3 || patchMode.isPending}
            onClick={() => patchMode.mutate()}
            className="rounded-md bg-live px-3 py-2 text-sm font-semibold text-graphite-950 disabled:opacity-50"
          >
            {patchMode.isPending ? "Saving…" : "Update mode"}
          </button>
          {message ? <p className="mt-2 text-xs text-muted">{message}</p> : null}
        </Panel>

        <Panel className="p-4">
          <h2 className="mb-3 text-sm font-semibold">Active goal profile</h2>
          {goals.isLoading ? <EmptyState>Loading goals…</EmptyState> : null}
          {goals.error ? (
            <EmptyState>
              {goals.error instanceof Error ? goals.error.message : "Goals unavailable"}
            </EmptyState>
          ) : null}
          {goals.data ? (
            <dl className="space-y-2 text-sm">
              <div className="mb-2 font-medium">{goals.data.name}</div>
              {(
                [
                  "energy_weight",
                  "cost_weight",
                  "carbon_weight",
                  "comfort_weight",
                  "peak_weight",
                  "equipment_weight",
                ] as const
              ).map((key) => (
                <div
                  key={key}
                  className="flex justify-between rounded border border-border/70 bg-background/40 px-3 py-2"
                >
                  <dt className="capitalize text-muted">
                    {key.replace("_weight", "").replaceAll("_", " ")}
                  </dt>
                  <dd className="font-mono">{goals.data[key].toFixed(2)}</dd>
                </div>
              ))}
              <p className="pt-2 text-xs text-muted">
                Goal weight editing is not exposed by the API yet — values are read-only here.
              </p>
            </dl>
          ) : null}
        </Panel>
      </div>
    </div>
  );
}
