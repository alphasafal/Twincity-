"use client";

import { AlertTriangle, Info, ShieldAlert } from "lucide-react";
import { cn } from "@/lib/utils";

const COPY: Record<
  string,
  { title: string; body: string; tone: string; icon: typeof Info }
> = {
  GUARDED: {
    title: "Guarded autonomy",
    body: "TwinPilot may propose and apply low-risk actions, but the Safety Shield still blocks high-risk changes.",
    tone: "border-live/40 bg-live/10 text-live",
    icon: Info,
  },
  ADVISORY: {
    title: "Advisory mode",
    body: "Plans require explicit human approval before apply. No autonomous control writes in this mode.",
    tone: "border-warning/40 bg-warning/10 text-warning",
    icon: AlertTriangle,
  },
  FALLBACK: {
    title: "Fallback mode",
    body: "Autonomy is restricted. Critical alerts or service degradation may be blocking normal optimization.",
    tone: "border-critical/40 bg-critical/10 text-critical",
    icon: ShieldAlert,
  },
};

export function ModeBanner({ mode }: { mode?: string | null }) {
  const key = (mode || "").toUpperCase();
  const cfg = COPY[key];
  if (!cfg) return null;
  const Icon = cfg.icon;
  return (
    <div
      className={cn(
        "mb-5 flex items-start gap-3 rounded-lg border px-4 py-3 text-sm animate-fade-up",
        cfg.tone,
      )}
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0" />
      <div>
        <div className="font-semibold">{cfg.title}</div>
        <p className="mt-0.5 opacity-90">{cfg.body}</p>
      </div>
    </div>
  );
}
