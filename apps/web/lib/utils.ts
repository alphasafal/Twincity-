import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toLocaleString(undefined, {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  });
}

export function formatPct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${formatNumber(value, digits)}%`;
}

export function formatTs(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

export function comfortColor(status?: string | null): string {
  switch ((status || "").toLowerCase()) {
    case "ok":
    case "comfortable":
    case "within_band":
      return "var(--savings)";
    case "warning":
    case "near_limit":
      return "var(--warning)";
    case "violation":
    case "critical":
    case "out_of_band":
      return "var(--critical)";
    default:
      return "var(--live)";
  }
}
