"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

const ORDER = ["starter", "optimize", "autonomy", "enterprise"] as const;

const FALLBACK: Record<
  string,
  { label: string; description: string; price: string; highlights: string[] }
> = {
  starter: {
    label: "Starter",
    description: "Read-only monitoring for one building",
    price: "$499/mo",
    highlights: ["1 building", "BACnet read", "Assistant (deterministic)", "Audit trail"],
  },
  optimize: {
    label: "Optimize",
    description: "Guarded write + multi-site optimization",
    price: "$1,499/mo",
    highlights: ["5 buildings", "Guarded BMS write", "Honeywell path", "M&V reporting"],
  },
  autonomy: {
    label: "Autonomy",
    description: "Certified autonomous control for portfolios",
    price: "$4,999/mo",
    highlights: ["25 buildings", "Certified Autonomous", "Write-ack safety", "Priority onboarding"],
  },
  enterprise: {
    label: "Enterprise",
    description: "SSO, custom connectors, unlimited scale",
    price: "Custom",
    highlights: ["1000 buildings", "SSO / custom connectors", "SLA + compliance pack", "Dedicated CSM"],
  },
};

export default function PricingPage() {
  const plans = useQuery({
    queryKey: ["billing-plans-public"],
    queryFn: () => api.listBillingPlans(),
    retry: 0,
  });

  return (
    <div className="min-h-screen bg-[#061018] text-white">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5 lg:px-8">
        <Link href="/" className="font-display text-lg font-semibold">
          TwinPilot
        </Link>
        <div className="flex gap-4 text-sm">
          <Link href="/login" className="text-white/70 hover:text-white">
            Sign in
          </Link>
          <Link
            href="/signup"
            className="rounded-md bg-cyan-300 px-3 py-1.5 font-medium text-graphite-950"
          >
            Start trial
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-16 lg:px-8">
        <h1 className="font-display text-4xl font-semibold tracking-tight sm:text-5xl">
          Pricing that matches how buildings adopt autonomy
        </h1>
        <p className="mt-4 max-w-2xl text-white/60">
          Start with monitoring. Upgrade when write safety and M&V are proven. No unsupervised
          Autonomous writes on uncertified sites — that is the product advantage.
        </p>

        <div className="mt-12 grid gap-5 lg:grid-cols-4">
          {ORDER.map((code) => {
            const remote = plans.data?.plans?.[code];
            const local = FALLBACK[code];
            return (
              <div
                key={code}
                className="flex flex-col border border-white/15 bg-white/[0.03] p-5"
              >
                <div className="font-display text-xl font-semibold">
                  {String(remote?.label || local.label)}
                </div>
                <p className="mt-2 text-sm text-white/55">
                  {String(remote?.description || local.description)}
                </p>
                <div className="mt-6 font-display text-3xl font-semibold text-cyan-300">
                  {local.price}
                </div>
                <ul className="mt-5 flex-1 space-y-2 text-sm text-white/70">
                  {(local.highlights || []).map((h) => (
                    <li key={h}>· {h}</li>
                  ))}
                </ul>
                <Link
                  href={`/signup?plan=${code}`}
                  className="mt-6 inline-flex justify-center rounded-md bg-cyan-300 px-3 py-2 text-sm font-semibold text-graphite-950 hover:bg-cyan-200"
                >
                  {code === "enterprise" ? "Contact sales" : "Start trial"}
                </Link>
              </div>
            );
          })}
        </div>

        <p className="mt-10 text-xs text-white/40">
          Trial includes a sandbox building. Live BMS write requires Optimize+ and site
          certification. Prices are list rates for commercial packaging; enterprise is quote-based.
        </p>
      </main>
    </div>
  );
}
