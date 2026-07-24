import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Terms of Service" };

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-[#061018] text-white">
      <header className="mx-auto max-w-3xl px-6 py-5">
        <Link href="/" className="font-display text-lg font-semibold">
          TwinPilot
        </Link>
      </header>
      <main className="mx-auto max-w-3xl px-6 py-10 prose-invert">
        <h1 className="font-display text-3xl font-semibold">Terms of Service</h1>
        <p className="mt-4 text-sm text-white/60">Last updated: July 24, 2026</p>
        <div className="mt-8 space-y-4 text-sm leading-relaxed text-white/75">
          <p>
            TwinPilot is a software optimization and safety layer for building systems. It is not a
            replacement for your BMS, fire/life-safety systems, or licensed engineering judgment.
          </p>
          <p>
            Autonomous write control is available only for certified sites on eligible plans.
            Customer remains responsible for site commissioning, point mapping accuracy, and
            operational overrides.
          </p>
          <p>
            Savings figures shown as labeled estimates are not warranties. Contractual savings
            commitments require agreed M&amp;V baselines and meter sources.
          </p>
          <p>
            Subscription fees are billed per plan entitlements. Trials convert only after explicit
            checkout or written order. Enterprise terms may supersede these online terms.
          </p>
          <p>
            Contact: legal@twinpilot.demo (replace with your production domain before launch).
          </p>
        </div>
      </main>
    </div>
  );
}
