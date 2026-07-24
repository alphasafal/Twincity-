"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { EmptyState, PageHeader, Panel, SettingsSubnav } from "@/components/AppShell";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useBuildingId } from "@/lib/hooks";

const STAGES = [
  "connect",
  "map_points",
  "shadow",
  "guarded_pilot",
  "autonomy_review",
  "autonomy",
] as const;

export default function OnboardingSettingsPage() {
  const buildingId = useBuildingId();
  const building = useAuthStore((s) => s.building);
  const setBuilding = useAuthStore((s) => s.setBuilding);
  const queryClient = useQueryClient();
  const [message, setMessage] = useState<string | null>(null);

  const cert = useQuery({
    queryKey: ["certification", buildingId],
    queryFn: () => api.getCertification(buildingId!),
    enabled: Boolean(buildingId),
  });
  const mv = useQuery({
    queryKey: ["mv-report", buildingId],
    queryFn: () => api.getMvReport(buildingId!),
    enabled: Boolean(buildingId),
  });

  const setStage = useMutation({
    mutationFn: (stage: string) =>
      api.setOnboardingStage(buildingId!, stage, `Advance onboarding to ${stage}`),
    onSuccess: async () => {
      const updated = await api.getBuilding(buildingId!);
      setBuilding(updated);
      setMessage(`Onboarding stage → ${updated.onboarding_stage}`);
    },
    onError: (err) =>
      setMessage(err instanceof Error ? err.message : "Stage update failed"),
  });

  const certify = useMutation({
    mutationFn: () =>
      api.updateCertification(buildingId!, {
        checklist_json: {
          point_map_complete: true,
          telemetry_fresh: true,
          failsafe_tested: true,
        },
        shadow_mode_complete: true,
        guarded_pilot_complete: true,
        autonomy_approved: true,
        notes: "Operator completed certification checklist",
        reason: "Site certification from onboarding wizard",
      }),
    onSuccess: (result) => {
      setMessage(
        result.site_certified
          ? "Site certified — ready for autonomy review"
          : "Certification updated",
      );
      void queryClient.invalidateQueries({ queryKey: ["certification", buildingId] });
    },
    onError: (err) =>
      setMessage(err instanceof Error ? err.message : "Certification failed"),
  });

  if (!buildingId) {
    return (
      <div>
        <PageHeader title="Onboarding" />
        <SettingsSubnav />
        <EmptyState>Select a building first.</EmptyState>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Site onboarding"
        description="Connect → map points → shadow (recommend only) → guarded pilot → autonomy review. Autonomous write requires certification + plan entitlement."
      />
      <SettingsSubnav />

      <Panel className="mb-4 p-4">
        <h2 className="text-sm font-semibold">Current stage</h2>
        <p className="mt-2 text-sm">
          {building?.onboarding_stage || "unknown"} · shadow={String(building?.shadow_mode)} ·
          certified={String(building?.site_certified)} · write={String(building?.write_enabled)}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {STAGES.map((stage) => (
            <button
              key={stage}
              type="button"
              className="rounded-md border border-border px-3 py-1.5 text-xs hover:border-live/40 hover:text-live"
              onClick={() => setStage.mutate(stage)}
            >
              {stage}
            </button>
          ))}
        </div>
      </Panel>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel className="p-4">
          <h2 className="mb-2 text-sm font-semibold">Certification checklist</h2>
          <pre className="max-h-48 overflow-auto font-mono text-[11px] text-muted">
            {JSON.stringify(cert.data || {}, null, 2)}
          </pre>
          <button
            type="button"
            className="mt-3 rounded-md border border-live/40 bg-live/10 px-3 py-1.5 text-xs text-live"
            onClick={() => certify.mutate()}
          >
            Mark checklist complete
          </button>
        </Panel>
        <Panel className="p-4">
          <h2 className="mb-2 text-sm font-semibold">M&amp;V / ROI</h2>
          {mv.data ? (
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-muted">Energy savings</dt>
                <dd>{mv.data.savings_energy_kwh} kWh</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-muted">Cost savings</dt>
                <dd>${mv.data.savings_cost}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-muted">Carbon avoided</dt>
                <dd>{mv.data.savings_carbon_kg} kg</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-muted">Labeled estimate</dt>
                <dd>{String(mv.data.labeled_estimate)}</dd>
              </div>
              <p className="text-xs text-muted">{mv.data.notes}</p>
            </dl>
          ) : (
            <p className="text-sm text-muted">Loading M&amp;V report…</p>
          )}
        </Panel>
      </div>
      {message ? <p className="mt-4 text-sm text-muted">{message}</p> : null}
    </div>
  );
}
