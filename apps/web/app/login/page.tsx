"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Leaf, ShieldCheck, Thermometer, Zap } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { DEMO_ACCOUNTS } from "@/lib/types";
import { cn } from "@/lib/utils";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  const router = useRouter();
  const setTokens = useAuthStore((s) => s.setTokens);
  const setUser = useAuthStore((s) => s.setUser);
  const setBuilding = useAuthStore((s) => s.setBuilding);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      email: DEMO_ACCOUNTS[0].email,
      password: DEMO_ACCOUNTS[0].password,
    },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    setLoading(true);
    setError(null);
    try {
      const tokens = await api.login(values.email, values.password);
      setTokens(tokens.access_token, tokens.refresh_token);
      const me = await api.me();
      setUser(me);
      const buildings = await api.listBuildings();
      if (buildings[0]) setBuilding(buildings[0]);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  });

  return (
    <div className="relative min-h-screen overflow-hidden bg-graphite-950 text-foreground">
      <div className="pointer-events-none absolute inset-0 bg-hero-glow" />
      <div className="pointer-events-none absolute inset-0 bg-grid-faint bg-[size:32px_32px] opacity-50" />

      <div className="relative mx-auto grid min-h-screen max-w-6xl items-center gap-10 px-6 py-12 lg:grid-cols-[1.1fr_0.9fr] lg:px-8">
        <section className="animate-fade-up">
          <div className="font-mono text-xs uppercase tracking-[0.35em] text-live">
            TwinPilot
          </div>
          <h1 className="mt-4 max-w-xl text-5xl font-semibold tracking-tight text-balance sm:text-6xl">
            TwinPilot
          </h1>
          <p className="mt-4 max-w-lg text-lg text-graphite-300">
            Autonomous optimization you can verify.
          </p>
          <p className="mt-3 max-w-lg text-sm text-muted">
            Industrial control for buildings — live telemetry, Safety Shield
            validation, and prediction ledgers that show what the twin expected
            versus what happened.
          </p>

          <div className="mt-10 grid gap-3 sm:grid-cols-2">
            {[
              {
                icon: Zap,
                label: "Energy",
                copy: "Live load & verified savings trails",
                tone: "text-live",
              },
              {
                icon: Leaf,
                label: "Carbon",
                copy: "Grid intensity–aware plan scoring",
                tone: "text-savings",
              },
              {
                icon: Thermometer,
                label: "Comfort",
                copy: "Zone bands enforced before apply",
                tone: "text-warning",
              },
              {
                icon: ShieldCheck,
                label: "Safety",
                copy: "Independent shield + rollback path",
                tone: "text-critical",
              },
            ].map((item) => (
              <div
                key={item.label}
                className="rounded-lg border border-border/80 bg-graphite-900/70 p-4 backdrop-blur"
              >
                <item.icon className={cn("mb-2 h-4 w-4", item.tone)} />
                <div className="text-sm font-medium">{item.label}</div>
                <div className="mt-1 text-xs text-muted">{item.copy}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="animate-fade-up rounded-xl border border-border bg-graphite-900/85 p-6 shadow-panel backdrop-blur sm:p-8">
          <h2 className="text-xl font-semibold">Sign in</h2>
          <p className="mt-1 text-sm text-muted">
            Demo credentials are for local development only.
          </p>

          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <label className="block text-sm">
              <span className="mb-1.5 block text-muted">Email</span>
              <input
                type="email"
                autoComplete="username"
                className="w-full rounded-md border border-border bg-graphite-950 px-3 py-2 text-foreground outline-none ring-live/40 focus:ring-2"
                {...form.register("email")}
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1.5 block text-muted">Password</span>
              <input
                type="password"
                autoComplete="current-password"
                className="w-full rounded-md border border-border bg-graphite-950 px-3 py-2 text-foreground outline-none ring-live/40 focus:ring-2"
                {...form.register("password")}
              />
            </label>

            <div>
              <div className="mb-2 text-xs uppercase tracking-wider text-muted">
                Demo account
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                {DEMO_ACCOUNTS.map((account) => {
                  const active = form.watch("email") === account.email;
                  return (
                    <button
                      key={account.email}
                      type="button"
                      onClick={() => {
                        form.setValue("email", account.email);
                        form.setValue("password", account.password);
                      }}
                      className={cn(
                        "rounded-md border px-3 py-2 text-left text-xs transition",
                        active
                          ? "border-live/50 bg-live/10 text-foreground"
                          : "border-border bg-graphite-950 text-muted hover:text-foreground",
                      )}
                    >
                      <div className="font-medium text-foreground">{account.role}</div>
                      <div className="mt-0.5 truncate font-mono">{account.email}</div>
                    </button>
                  );
                })}
              </div>
            </div>

            {error ? (
              <div className="rounded-md border border-critical/40 bg-critical/10 px-3 py-2 text-sm text-critical">
                {error}
              </div>
            ) : null}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-md bg-live px-4 py-2.5 text-sm font-semibold text-graphite-950 transition hover:brightness-110 disabled:opacity-60"
            >
              {loading ? "Signing in…" : "Enter control room"}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
