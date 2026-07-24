"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

function MarketingNav() {
  return (
    <header className="absolute inset-x-0 top-0 z-20">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5 lg:px-8">
        <Link href="/" className="font-display text-lg font-semibold tracking-tight text-white">
          TwinPilot
        </Link>
        <nav className="flex items-center gap-5 text-sm text-white/75">
          <Link href="/pricing" className="hidden sm:inline hover:text-white">
            Pricing
          </Link>
          <Link href="/status" className="hidden sm:inline hover:text-white">
            Status
          </Link>
          <Link href="/login" className="hover:text-white">
            Sign in
          </Link>
          <Link
            href="/signup"
            className="rounded-md bg-cyan-300 px-3 py-1.5 font-medium text-graphite-950 transition hover:bg-cyan-200"
          >
            Start free trial
          </Link>
        </nav>
      </div>
    </header>
  );
}

export default function MarketingHomePage() {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setReady(true));
    return () => cancelAnimationFrame(id);
  }, []);

  return (
    <div className="min-h-screen bg-[#061018] text-white">
      {/* Hero: one composition, brand first, full-bleed atmosphere */}
      <section className="relative min-h-[100svh] overflow-hidden">
        <div
          aria-hidden
          className="absolute inset-0 animate-hero-drift bg-[radial-gradient(ellipse_90%_70%_at_70%_15%,rgba(34,211,238,0.22),transparent_55%),radial-gradient(ellipse_60%_50%_at_15%_85%,rgba(16,185,129,0.16),transparent_50%),linear-gradient(160deg,#040a10_0%,#0b1a24_45%,#07141c_100%)]"
        />
        <div
          aria-hidden
          className="absolute inset-0 opacity-40 bg-[linear-gradient(rgba(148,163,184,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(148,163,184,0.08)_1px,transparent_1px)] bg-[size:48px_48px]"
        />
        <div
          aria-hidden
          className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-[#061018] to-transparent"
        />
        <MarketingNav />

        <div className="relative z-10 mx-auto flex min-h-[100svh] max-w-6xl flex-col justify-end px-6 pb-16 pt-28 lg:px-8 lg:pb-24">
          <div className={ready ? "animate-rise-in" : "opacity-0"}>
            <p className="font-display text-5xl font-semibold tracking-tight text-white sm:text-7xl lg:text-8xl">
              TwinPilot
            </p>
            <h1 className="mt-5 max-w-2xl text-2xl font-medium tracking-tight text-white/90 sm:text-3xl">
              Autonomous building optimization you can verify.
            </h1>
            <p className="mt-4 max-w-xl text-base text-white/65 sm:text-lg">
              Cut energy cost without blind AI control. TwinPilot proposes, the Safety Shield
              validates, and your operators approve — with a ledger that proves what happened.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link
                href="/signup"
                className="rounded-md bg-cyan-300 px-5 py-2.5 text-sm font-semibold text-graphite-950 transition hover:bg-cyan-200"
              >
                Start 14-day trial
              </Link>
              <Link
                href="/pricing"
                className="rounded-md border border-white/25 bg-white/5 px-5 py-2.5 text-sm font-medium text-white backdrop-blur transition hover:bg-white/10"
              >
                View pricing
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="border-t border-white/10 px-6 py-20 lg:px-8">
        <div className="mx-auto max-w-6xl">
          <h2 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">
            How TwinPilot sells and operates
          </h2>
          <p className="mt-3 max-w-2xl text-white/60">
            One job per stage — from trusted monitoring to certified autonomy.
          </p>
          <ol className="mt-10 grid gap-8 md:grid-cols-3">
            {[
              {
                step: "01",
                title: "Connect any BMS",
                copy: "BACnet/IP, Modbus TCP, or Honeywell Niagara. Map points once. Shadow mode recommends without writing.",
              },
              {
                step: "02",
                title: "Guard every write",
                copy: "Independent Safety Shield, HMAC validation tokens, and write acknowledgement before anything is marked applied.",
              },
              {
                step: "03",
                title: "Prove the savings",
                copy: "Prediction ledger + IPMVP-style M&V. Sell outcomes with labeled estimates until meters and baselines are live.",
              },
            ].map((item, index) => (
              <li
                key={item.step}
                className="animate-rise-in border-t border-cyan-300/30 pt-5"
                style={{ animationDelay: `${0.1 + index * 0.08}s` }}
              >
                <div className="font-mono text-xs tracking-[0.2em] text-cyan-300">{item.step}</div>
                <h3 className="mt-3 font-display text-xl font-semibold">{item.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-white/60">{item.copy}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="border-t border-white/10 bg-[#08151d] px-6 py-20 lg:px-8">
        <div className="mx-auto max-w-6xl">
          <h2 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">
            Built to be the safest optimizer in the category
          </h2>
          <p className="mt-3 max-w-2xl text-white/60">
            Competitors pitch autonomy. TwinPilot ships autonomy you can audit.
          </p>
          <ul className="mt-10 grid gap-6 sm:grid-cols-2">
            {[
              "Multi-tenant orgs, RBAC, and Stripe subscription entitlements",
              "Guarded → certified Autonomous path — no unsupervised writes on uncertified sites",
              "Vendor-agnostic connectors + Honeywell certified adapter path",
              "Immutable audit export for compliance and incident review",
            ].map((line) => (
              <li key={line} className="flex gap-3 text-sm text-white/75">
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />
                {line}
              </li>
            ))}
          </ul>
          <div className="mt-10">
            <Link
              href="/signup"
              className="inline-flex rounded-md bg-emerald-400 px-5 py-2.5 text-sm font-semibold text-graphite-950 transition hover:bg-emerald-300"
            >
              Create your organization
            </Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-white/10 px-6 py-8 text-sm text-white/45 lg:px-8">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4">
          <span className="font-display text-white/70">TwinPilot</span>
          <div className="flex gap-4">
            <Link href="/terms" className="hover:text-white">
              Terms
            </Link>
            <Link href="/privacy" className="hover:text-white">
              Privacy
            </Link>
            <Link href="/status" className="hover:text-white">
              Status
            </Link>
            <Link href="/login" className="hover:text-white">
              Operator console
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
