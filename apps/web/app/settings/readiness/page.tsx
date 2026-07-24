"use client";

import { useQuery } from "@tanstack/react-query";
import { EmptyState, PageHeader, Panel, SettingsSubnav } from "@/components/AppShell";
import { api } from "@/lib/api";
import { useBuildingId } from "@/lib/hooks";

export default function ReadinessPage() {
  const buildingId = useBuildingId();
  const readiness = useQuery({
    queryKey: ["readiness", buildingId],
    queryFn: () => api.getProductionReadiness(buildingId!),
    enabled: Boolean(buildingId),
  });

  if (!buildingId) {
    return (
      <div>
        <PageHeader title="Production readiness" />
        <SettingsSubnav />
        <EmptyState>Select a building first.</EmptyState>
      </div>
    );
  }

  const checks = readiness.data?.checks || [];
  const score = readiness.data?.score ?? 0;

  return (
    <div>
      <PageHeader
        title="Production readiness"
        description="Sellable go-live checklist for this building. Autonomous write stays locked until certification and plan entitlements pass."
      />
      <SettingsSubnav />

      <Panel className="mb-4 p-4">
        <div className="text-sm text-muted">Readiness score</div>
        <div className="mt-1 font-display text-3xl font-semibold text-live">{score}%</div>
        <p className="mt-2 text-xs text-muted">{readiness.data?.summary}</p>
      </Panel>

      <Panel className="p-4">
        <ul className="space-y-3">
          {checks.map((c) => (
            <li
              key={c.id}
              className="flex items-start justify-between gap-4 border-b border-border pb-3 text-sm"
            >
              <div>
                <div className="font-medium">{c.label}</div>
                <div className="mt-1 text-xs text-muted">{c.detail}</div>
              </div>
              <span
                className={
                  c.passed ? "font-mono text-xs text-savings" : "font-mono text-xs text-warning"
                }
              >
                {c.passed ? "PASS" : "TODO"}
              </span>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
