import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Privacy Policy" };

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[#061018] text-white">
      <header className="mx-auto max-w-3xl px-6 py-5">
        <Link href="/" className="font-display text-lg font-semibold">
          TwinPilot
        </Link>
      </header>
      <main className="mx-auto max-w-3xl px-6 py-10">
        <h1 className="font-display text-3xl font-semibold">Privacy Policy</h1>
        <p className="mt-4 text-sm text-white/60">Last updated: July 24, 2026</p>
        <div className="mt-8 space-y-4 text-sm leading-relaxed text-white/75">
          <p>
            We process account data (name, email, organization), building configuration, telemetry
            needed for optimization, and audit logs required for safety and compliance.
          </p>
          <p>
            Telemetry and control history are scoped to your organization. We do not sell customer
            building data. Subprocessors (e.g. Stripe for billing, hosting providers) are used only
            to deliver the service.
          </p>
          <p>
            You may export org audit events from the console. For deletion or DPA requests, contact
            privacy@twinpilot.demo before production launch with your real contact address.
          </p>
          <p>
            Demo accounts and sandbox buildings may use simulated telemetry and are not production
            personal data stores.
          </p>
        </div>
      </main>
    </div>
  );
}
