"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export default function StatusPage() {
  const health = useQuery({
    queryKey: ["public-health"],
    queryFn: () => api.health(),
    refetchInterval: 15000,
  });

  const ok = health.data?.status === "ok";
  const components = (health.data?.components || {}) as Record<string, string>;

  return (
    <div className="min-h-screen bg-[#061018] text-white">
      <header className="mx-auto flex max-w-3xl items-center justify-between px-6 py-5">
        <Link href="/" className="font-display text-lg font-semibold">
          TwinPilot
        </Link>
        <Link href="/signup" className="text-sm text-cyan-300">
          Start trial
        </Link>
      </header>
      <main className="mx-auto max-w-3xl px-6 py-10">
        <h1 className="font-display text-3xl font-semibold">Service status</h1>
        <p className="mt-3 text-sm text-white/60">
          Live health from this TwinPilot deployment.
        </p>
        <div
          className={`mt-8 border px-4 py-3 text-sm ${
            ok ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-200" : "border-warning/40 bg-warning/10 text-warning"
          }`}
        >
          {health.isLoading ? "Checking…" : ok ? "All systems operational" : "Degraded or unreachable"}
        </div>
        <ul className="mt-6 space-y-2 text-sm">
          {Object.entries(components).map(([key, value]) => (
            <li
              key={key}
              className="flex items-center justify-between border-b border-white/10 py-2"
            >
              <span className="capitalize text-white/70">{key}</span>
              <span className="font-mono text-xs text-white/90">{value}</span>
            </li>
          ))}
        </ul>
      </main>
    </div>
  );
}
