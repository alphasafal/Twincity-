"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
  EmptyState,
  PageHeader,
  Panel,
  SettingsSubnav,
  SimulatedBadge,
} from "@/components/AppShell";
import { OperatingModeBadge } from "@/components/OperatingModeBadge";
import { api, ApiError } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useBuildingId } from "@/lib/hooks";

export default function BuildingSettingsPage() {
  const buildingId = useBuildingId();
  const role = useAuthStore((s) => s.user?.role);
  const canEdit = role === "ADMINISTRATOR";
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["building", buildingId],
    queryFn: () => api.getBuilding(buildingId!),
    enabled: Boolean(buildingId),
  });

  const [name, setName] = useState("");
  const [location, setLocation] = useState("");
  const [timezone, setTimezone] = useState("");
  const [area, setArea] = useState("");
  const [buildingType, setBuildingType] = useState("");
  const [reason, setReason] = useState("Updated building metadata");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!data) return;
    setName(data.name);
    setLocation(data.location);
    setTimezone(data.timezone);
    setArea(String(data.area_m2));
    setBuildingType(data.building_type);
  }, [data]);

  const save = useMutation({
    mutationFn: () =>
      api.updateBuilding(buildingId!, {
        name,
        location,
        timezone,
        area_m2: Number(area),
        building_type: buildingType,
        reason,
      }),
    onSuccess: async () => {
      setMessage("Building updated and audited.");
      await qc.invalidateQueries({ queryKey: ["building", buildingId] });
      await qc.invalidateQueries({ queryKey: ["buildings"] });
    },
    onError: (err) => {
      setMessage(err instanceof ApiError ? String(err.message) : "Save failed");
    },
  });

  return (
    <div>
      <PageHeader
        title="Building settings"
        description="Identity and configuration from /api/v1/buildings/{id}."
        actions={data?.is_demo ? <SimulatedBadge label="Demo building" /> : null}
      />
      <SettingsSubnav />

      {isLoading ? <EmptyState>Loading building…</EmptyState> : null}
      {error ? (
        <EmptyState>{error instanceof Error ? error.message : "Failed to load"}</EmptyState>
      ) : null}

      {data ? (
        <Panel className="p-4">
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-semibold">{data.name}</h2>
            <OperatingModeBadge mode={data.current_mode} />
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Name" value={name} onChange={setName} disabled={!canEdit} />
            <Field label="Location" value={location} onChange={setLocation} disabled={!canEdit} />
            <Field label="Timezone" value={timezone} onChange={setTimezone} disabled={!canEdit} />
            <Field label="Area m²" value={area} onChange={setArea} disabled={!canEdit} />
            <Field
              label="Building type"
              value={buildingType}
              onChange={setBuildingType}
              disabled={!canEdit}
            />
            <Field label="Audit reason" value={reason} onChange={setReason} disabled={!canEdit} />
          </div>

          {!canEdit ? (
            <p className="mt-4 text-xs text-muted">
              Editing requires the ADMINISTRATOR role. Current view is read-only.
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
            {save.isPending ? "Saving…" : "Save building details"}
          </button>
          {message ? <p className="mt-2 text-xs text-muted">{message}</p> : null}
        </Panel>
      ) : null}
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block text-[10px] uppercase tracking-wider text-muted">{label}</span>
      <input
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-xs disabled:opacity-60"
      />
    </label>
  );
}
