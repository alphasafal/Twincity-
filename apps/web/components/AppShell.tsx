"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Bot,
  Building2,
  ChartLine,
  CircuitBoard,
  ClipboardList,
  Gauge,
  LayoutDashboard,
  Map,
  Moon,
  Settings,
  Shield,
  Sun,
  Target,
  Users,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/digital-twin", label: "Digital Twin", icon: CircuitBoard },
  { href: "/zones", label: "Zones", icon: Map },
  { href: "/optimization", label: "Optimization", icon: Target },
  { href: "/simulator", label: "Simulator", icon: Activity },
  { href: "/live-demo", label: "Live Demo", icon: Gauge },
  { href: "/decisions", label: "Decisions", icon: ClipboardList },
  { href: "/alerts", label: "Alerts", icon: AlertTriangle },
  { href: "/analytics", label: "Analytics", icon: ChartLine },
  { href: "/assistant", label: "Assistant", icon: Bot },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/audit", label: "Audit", icon: Shield },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { hydrated, accessToken, user, building, logout } = useAuthStore();
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    const saved = localStorage.getItem("twinpilot-theme") as "dark" | "light" | null;
    const next = saved || "dark";
    setTheme(next);
    document.documentElement.classList.toggle("dark", next === "dark");
    document.documentElement.classList.toggle("light", next === "light");
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    if (!accessToken && pathname !== "/login") {
      router.replace("/login");
    }
  }, [hydrated, accessToken, pathname, router]);

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    localStorage.setItem("twinpilot-theme", next);
    document.documentElement.classList.toggle("dark", next === "dark");
    document.documentElement.classList.toggle("light", next === "light");
  };

  if (pathname === "/login") {
    return <>{children}</>;
  }

  if (!hydrated || !accessToken) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background text-muted">
        Loading TwinPilot…
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="flex min-h-screen">
        <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col border-r border-border bg-graphite-900/95 backdrop-blur">
          <div className="border-b border-border px-5 py-5">
            <Link href="/dashboard" className="block">
              <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-live">
                TwinPilot
              </div>
              <div className="mt-1 text-sm text-muted">
                {building?.name || "No building"}
              </div>
            </Link>
          </div>
          <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
            {NAV.map((item) => {
              const active =
                pathname === item.href || pathname.startsWith(`${item.href}/`);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                    active
                      ? "bg-surface-elevated text-foreground"
                      : "text-muted hover:bg-surface hover:text-foreground",
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0 opacity-80" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="border-t border-border p-3">
            <div className="mb-2 truncate px-1 text-xs text-muted">
              {user?.name} · {user?.role}
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={toggleTheme}
                className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-md border border-border bg-surface px-2 py-1.5 text-xs text-muted hover:text-foreground"
              >
                {theme === "dark" ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
                {theme === "dark" ? "Light" : "Dark"}
              </button>
              <button
                type="button"
                onClick={async () => {
                  try {
                    await api.logout();
                  } catch {
                    // ignore
                  }
                  logout();
                  router.replace("/login");
                }}
                className="inline-flex flex-1 items-center justify-center rounded-md border border-border bg-surface px-2 py-1.5 text-xs text-muted hover:text-foreground"
              >
                Sign out
              </button>
            </div>
          </div>
        </aside>
        <main className="relative min-w-0 flex-1">
          <div className="pointer-events-none absolute inset-0 bg-hero-glow opacity-70" />
          <div className="pointer-events-none absolute inset-0 bg-grid-faint bg-[size:28px_28px] opacity-40" />
          <div className="relative px-6 py-6 lg:px-8">{children}</div>
        </main>
      </div>
    </div>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4 animate-fade-up">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
        {description ? (
          <p className="mt-1 max-w-2xl text-sm text-muted">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function SimulatedBadge({ label = "Simulated data" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded border border-warning/40 bg-warning/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-warning">
      <Gauge className="h-3 w-3" />
      {label}
    </span>
  );
}

export function Panel({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cn(
        "rounded-lg border border-border bg-surface/80 shadow-panel backdrop-blur-sm",
        className,
      )}
    >
      {children}
    </section>
  );
}

export function EmptyState({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-border bg-surface/40 px-4 py-8 text-center text-sm text-muted">
      {children}
    </div>
  );
}

export function SettingsSubnav() {
  const pathname = usePathname();
  const items = [
    { href: "/settings", label: "Overview", icon: Settings },
    { href: "/settings/building", label: "Building", icon: Building2 },
    { href: "/settings/constraints", label: "Constraints", icon: Shield },
    { href: "/settings/users", label: "Users", icon: Users },
  ];
  return (
    <div className="mb-6 flex flex-wrap gap-2">
      {items.map((item) => {
        const active = pathname === item.href;
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm",
              active
                ? "border-live/40 bg-live/10 text-live"
                : "border-border bg-surface text-muted hover:text-foreground",
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {item.label}
          </Link>
        );
      })}
    </div>
  );
}
