"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { EmptyState, PageHeader, Panel, SettingsSubnav } from "@/components/AppShell";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";

const PLAN_ORDER = ["starter", "optimize", "autonomy", "enterprise"] as const;

export default function BillingSettingsPage() {
  const organizationId = useAuthStore((s) => s.organizationId);
  const queryClient = useQueryClient();
  const [message, setMessage] = useState<string | null>(null);

  const plans = useQuery({
    queryKey: ["billing-plans"],
    queryFn: () => api.listBillingPlans(),
  });
  const subscription = useQuery({
    queryKey: ["subscription", organizationId],
    queryFn: () => api.getSubscription(organizationId!),
    enabled: Boolean(organizationId),
  });

  const checkout = useMutation({
    mutationFn: (plan_code: string) => api.checkout(organizationId!, plan_code),
    onSuccess: (result) => {
      setMessage(
        result.mode === "mock"
          ? `Mock checkout applied (${result.message || "plan updated"})`
          : "Redirecting to Stripe…",
      );
      if (result.checkout_url && result.mode === "stripe") {
        window.location.href = result.checkout_url;
      }
      void queryClient.invalidateQueries({ queryKey: ["subscription", organizationId] });
    },
    onError: (err) =>
      setMessage(err instanceof Error ? err.message : "Checkout failed"),
  });

  if (!organizationId) {
    return (
      <div>
        <PageHeader title="Billing" />
        <SettingsSubnav />
        <EmptyState>No organization selected.</EmptyState>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Billing"
        description="Subscription plans gate buildings, write modes, and connector types. Stripe is used when configured; otherwise mock checkout updates entitlements locally."
      />
      <SettingsSubnav />

      <Panel className="mb-4 p-4">
        <h2 className="text-sm font-semibold">Current subscription</h2>
        {subscription.isLoading ? (
          <p className="mt-2 text-sm text-muted">Loading…</p>
        ) : (
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-muted">Plan</dt>
              <dd className="font-medium">{subscription.data?.plan_code}</dd>
            </div>
            <div>
              <dt className="text-muted">Status</dt>
              <dd className="font-medium">{subscription.data?.status}</dd>
            </div>
            <div className="sm:col-span-2">
              <dt className="text-muted">Entitlements</dt>
              <dd className="mt-1 font-mono text-xs text-muted">
                {JSON.stringify(subscription.data?.entitlements || {}, null, 2)}
              </dd>
            </div>
          </dl>
        )}
      </Panel>

      <div className="grid gap-4 md:grid-cols-2">
        {PLAN_ORDER.map((code) => {
          const plan = plans.data?.plans?.[code];
          if (!plan) return null;
          return (
            <Panel key={code} className="p-4">
              <h3 className="text-sm font-semibold">{String(plan.label || code)}</h3>
              <p className="mt-1 text-xs text-muted">{String(plan.description || "")}</p>
              <ul className="mt-3 space-y-1 text-xs text-muted">
                <li>Max buildings: {String(plan.max_buildings)}</li>
                <li>Guarded write: {String(plan.guarded_write)}</li>
                <li>Autonomous write: {String(plan.autonomous_write)}</li>
                <li>Connectors: {Array.isArray(plan.connector_types) ? plan.connector_types.join(", ") : ""}</li>
              </ul>
              <button
                type="button"
                className="mt-4 rounded-md border border-live/40 bg-live/10 px-3 py-1.5 text-xs text-live"
                disabled={checkout.isPending || subscription.data?.plan_code === code}
                onClick={() => checkout.mutate(code)}
              >
                {subscription.data?.plan_code === code ? "Current plan" : `Choose ${code}`}
              </button>
            </Panel>
          );
        })}
      </div>
      {message ? <p className="mt-4 text-sm text-muted">{message}</p> : null}
    </div>
  );
}
