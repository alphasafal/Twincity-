"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { EmptyState, PageHeader, Panel, SimulatedBadge } from "@/components/AppShell";
import { PlanCard } from "@/components/PlanCard";
import { api } from "@/lib/api";
import { useBuildingId } from "@/lib/hooks";
import type { ControlPlan } from "@/lib/types";

const DEFAULT_WEIGHTS = {
  energy_weight: 0.25,
  cost_weight: 0.2,
  carbon_weight: 0.2,
  comfort_weight: 0.2,
  peak_weight: 0.1,
  equipment_weight: 0.05,
};

export default function OptimizationPage() {
  const buildingId = useBuildingId();
  const [weights, setWeights] = useState(DEFAULT_WEIGHTS);
  const [plans, setPlans] = useState<ControlPlan[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const generate = useMutation({
    mutationFn: () => api.generateOptimization(buildingId!, weights),
    onSuccess: (data) => {
      setPlans(data.plans);
      setSelectedId(data.plans[0]?.id ?? null);
      setMessage(
        data.simulated
          ? "Plans generated from simulated twin state."
          : "Plans generated.",
      );
    },
    onError: (err) =>
      setMessage(err instanceof Error ? err.message : "Generation failed"),
  });

  const act = useMutation({
    mutationFn: async ({
      planId,
      action,
    }: {
      planId: string;
      action: "simulate" | "validate" | "approve" | "reject" | "apply";
    }) => {
      if (action === "simulate") return api.simulatePlan(planId);
      if (action === "validate") return api.validatePlan(planId);
      if (action === "approve")
        return api.approvePlan(planId, "Operator approved after review");
      if (action === "reject")
        return api.rejectPlan(planId, "Operator rejected candidate plan");
      return api.applyPlan(planId);
    },
    onSuccess: (result, vars) => {
      setMessage(`${vars.action} → ${JSON.stringify(result).slice(0, 160)}…`);
      if (selectedId) {
        void api.getPlan(selectedId).then((plan) => {
          setPlans((prev) => prev.map((p) => (p.id === plan.id ? { ...p, ...plan } : p)));
        });
      }
    },
    onError: (err) =>
      setMessage(err instanceof Error ? err.message : "Action failed"),
  });

  const selected = plans.find((p) => p.id === selectedId) || null;

  return (
    <div>
      <PageHeader
        title="Optimization"
        description="Generate candidate control plans from /api/v1/buildings/{id}/optimization/generate."
        actions={<SimulatedBadge />}
      />

      <div className="grid gap-4 xl:grid-cols-[320px_1fr]">
        <Panel className="space-y-3 p-4">
          <h2 className="text-sm font-semibold">Objective weights</h2>
          {(Object.keys(weights) as Array<keyof typeof weights>).map((key) => (
            <label key={key} className="block text-xs">
              <span className="mb-1 flex justify-between text-muted">
                <span className="capitalize">{key.replace("_weight", "").replaceAll("_", " ")}</span>
                <span className="font-mono">{weights[key].toFixed(2)}</span>
              </span>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={weights[key]}
                onChange={(e) =>
                  setWeights((w) => ({ ...w, [key]: Number(e.target.value) }))
                }
                className="w-full accent-cyan-400"
              />
            </label>
          ))}
          <button
            type="button"
            disabled={!buildingId || generate.isPending}
            onClick={() => generate.mutate()}
            className="w-full rounded-md bg-live px-3 py-2 text-sm font-semibold text-graphite-950 disabled:opacity-50"
          >
            {generate.isPending ? "Generating…" : "Generate plans"}
          </button>
          {message ? <p className="text-xs text-muted">{message}</p> : null}
        </Panel>

        <div className="space-y-3">
          {!plans.length ? (
            <EmptyState>
              No plans yet. Generate candidates from the current twin observation.
            </EmptyState>
          ) : (
            plans.map((plan) => (
              <PlanCard
                key={plan.id}
                plan={plan}
                selected={plan.id === selectedId}
                onSelect={() => setSelectedId(plan.id)}
                actions={
                  plan.id === selectedId ? (
                    <>
                      {(
                        [
                          ["simulate", "Simulate"],
                          ["validate", "Validate"],
                          ["approve", "Approve"],
                          ["reject", "Reject"],
                          ["apply", "Apply"],
                        ] as const
                      ).map(([action, label]) => (
                        <button
                          key={action}
                          type="button"
                          disabled={act.isPending}
                          onClick={(e) => {
                            e.stopPropagation();
                            act.mutate({ planId: plan.id, action });
                          }}
                          className="rounded border border-border px-2 py-1 text-xs text-muted hover:text-foreground disabled:opacity-50"
                        >
                          {label}
                        </button>
                      ))}
                    </>
                  ) : null
                }
              />
            ))
          )}

          {selected?.validation_json ? (
            <Panel className="p-4">
              <h3 className="mb-2 text-sm font-semibold">Latest validation</h3>
              <pre className="overflow-x-auto rounded bg-background/60 p-3 font-mono text-[11px] text-muted">
                {JSON.stringify(selected.validation_json, null, 2)}
              </pre>
            </Panel>
          ) : null}
        </div>
      </div>
    </div>
  );
}
