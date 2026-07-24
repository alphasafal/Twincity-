"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";

function SignupForm() {
  const router = useRouter();
  const params = useSearchParams();
  const plan = params.get("plan") || "starter";
  const setTokens = useAuthStore((s) => s.setTokens);
  const setUser = useAuthStore((s) => s.setUser);
  const setBuilding = useAuthStore((s) => s.setBuilding);
  const setOrganization = useAuthStore((s) => s.setOrganization);

  const [orgName, setOrgName] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [buildingName, setBuildingName] = useState("Headquarters");
  const [location, setLocation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await api.signup({
        organization_name: orgName,
        name,
        email,
        password,
        building_name: buildingName,
        location: location || "Unspecified",
        plan_code: plan === "enterprise" ? "starter" : plan,
      });
      setTokens(result.access_token, result.refresh_token);
      setUser(result.user);
      if (result.organization) setOrganization(result.organization);
      if (result.building) setBuilding(result.building);
      router.replace("/settings/onboarding");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#061018] text-white">
      <header className="mx-auto flex max-w-xl items-center justify-between px-6 py-5">
        <Link href="/" className="font-display text-lg font-semibold">
          TwinPilot
        </Link>
        <Link href="/login" className="text-sm text-white/70 hover:text-white">
          Sign in
        </Link>
      </header>

      <main className="mx-auto max-w-xl px-6 py-10">
        <h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">
          Start your TwinPilot trial
        </h1>
        <p className="mt-3 text-sm text-white/60">
          14-day trial · plan preference: <span className="text-cyan-300">{plan}</span>. You can
          change plans anytime in Billing.
        </p>

        <form onSubmit={onSubmit} className="mt-8 space-y-4">
          <label className="block text-xs">
            <span className="mb-1 block text-white/55">Organization</span>
            <input
              required
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              className="w-full rounded-md border border-white/15 bg-white/5 px-3 py-2 text-sm"
              placeholder="Acme Facilities"
            />
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-xs">
              <span className="mb-1 block text-white/55">Your name</span>
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-md border border-white/15 bg-white/5 px-3 py-2 text-sm"
              />
            </label>
            <label className="block text-xs">
              <span className="mb-1 block text-white/55">Work email</span>
              <input
                required
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-md border border-white/15 bg-white/5 px-3 py-2 text-sm"
              />
            </label>
          </div>
          <label className="block text-xs">
            <span className="mb-1 block text-white/55">Password</span>
            <input
              required
              type="password"
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-white/15 bg-white/5 px-3 py-2 text-sm"
            />
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-xs">
              <span className="mb-1 block text-white/55">First building</span>
              <input
                required
                value={buildingName}
                onChange={(e) => setBuildingName(e.target.value)}
                className="w-full rounded-md border border-white/15 bg-white/5 px-3 py-2 text-sm"
              />
            </label>
            <label className="block text-xs">
              <span className="mb-1 block text-white/55">Location</span>
              <input
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full rounded-md border border-white/15 bg-white/5 px-3 py-2 text-sm"
                placeholder="City, Country"
              />
            </label>
          </div>

          {error ? <p className="text-sm text-red-300">{error}</p> : null}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-cyan-300 px-4 py-2.5 text-sm font-semibold text-graphite-950 hover:bg-cyan-200 disabled:opacity-60"
          >
            {loading ? "Creating organization…" : "Create organization"}
          </button>
        </form>

        <p className="mt-6 text-xs text-white/40">
          By continuing you agree to the{" "}
          <Link href="/terms" className="text-white/70 underline">
            Terms
          </Link>{" "}
          and{" "}
          <Link href="/privacy" className="text-white/70 underline">
            Privacy Policy
          </Link>
          .
        </p>
      </main>
    </div>
  );
}

export default function SignupPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#061018] p-8 text-white">Loading…</div>}>
      <SignupForm />
    </Suspense>
  );
}
