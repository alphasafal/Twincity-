"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
  EmptyState,
  PageHeader,
  Panel,
  SettingsSubnav,
} from "@/components/AppShell";
import { api, ApiError } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useBuildingId } from "@/lib/hooks";
import type { ConstraintPolicy } from "@/lib/types";

const FIELDS: Array<{ key: keyof ConstraintPolicy; label: string }> = [
  { key: "min_cooling_setpoint", label: "Min cooling SP (°C)" },
  { key: "max_cooling_setpoint", label: "Max cooling SP (°C)" },
  { key: "min_heating_setpoint", label: "Min heating SP (°C)" },
  { key: "max_heating_setpoint", label: "Max heating SP (°C)" },
  { key: "max_setpoint_change_per_interval", label: "Max SP change / interval (°C)" },
  { key: "minimum_ventilation", label: "Min ventilation (0-1)" },
  { key: "maximum_control_duration", label: "Max control duration (min)" },
  { key: "minimum_confidence_for_autonomy", label: "Min autonomy confidence" },
  { key: "maximum_data_age_seconds", label: "Max data age (s)" },
];

export default function ConstraintsSettingsPage() {
  const buildingId = useBuildingId();
  const role = useAuthStore((s) => s.user?.role);
  const canEdit = role === "ADMINISTRATOR";
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["constraints", buildingId],
    queryFn: () => api.getConstraints(buildingId!),
    enabled: Boolean(buildingId),
  });

  const [form, setForm] = useState<Partial<ConstraintPolicy>>({});
  const [reason, setReason] = useState("Updated Safety Shield constraint policy");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (data) setForm(data);
  }, [data]);

  const save = useMutation({
    mutationFn: () =>
      api.updateConstraints(buildingId!, {
        ...form,
        reason,
      }),
    onSuccess: async () => {
      setMessage("Constraints updated. Safety Shield will use the new limits.");
      await qc.invalidateQueries({ queryKey: ["constraints", buildingId] });
    },
    onError: (err) => {
      setMessage(err instanceof ApiError ? String(err.message) : "Save failed");
    },
  });

  return (
    <div>
      <PageHeader
        title="Constraint policy"
        description="Hard limits enforced by the Safety Shield before any control write."
      />
      <SettingsSubnav />

      {isLoading ? <EmptyState>Loading constraints…</EmptyState> : null}
      {error ? (
        <EmptyState>{error instanceof Error ? error.message : "Failed to load"}</EmptyState>
      ) : null}

      {data ? (
        <Panel className="p-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {FIELDS.map(({ key, label }) => (
              <label key={String(key)} className="block text-sm">
                <span className="mb-1 block text-[10px] uppercase tracking-wider text-muted">
                  {label}
                </span>
                <input
                  type="number"
                  step="any"
                  disabled={!canEdit}
                  value={form[key] ?? ""}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      [key]: e.target.value === "" ? undefined : Number(e.target.value),
                    }))
                  }
                  className="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-xs disabled:opacity-60"
                />
              </label>
            ))}
          </div>

          <label className="mt-4 block text-sm">
            <span className="mb-1 block text-[10px] uppercase tracking-wider text-muted">
              Audit reason
            </span>
            <input
              disabled={!canEdit}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm disabled:opacity-60"
            />
          </label>

          {!canEdit ? (
            <p className="mt-3 text-xs text-muted">
              Constraint modification requires the ADMINISTRATOR role.
            </p>
          ) : null}

          <button
            type="button"
            disabled={!canEdit || save.isPending || reason.trim().length < 3}
            onClick={() => {
              setMessage(null);
              save.mutate();
            }}
            className="mt-4 rounded-md bg-live px-3 py-2 text-sm font-semibold text-graphite-950 disabled:opacity-50"
          >
            {save.isPending ? "Saving…" : "Save constraints"}
          </button>
          {message ? <p className="mt-2 text-xs text-muted">{message}</p> : null}
        </Panel>
      ) : null}
    </div>
  );
}
