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

export function formatRelative(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  const seconds = Math.round((Date.now() - d.getTime()) / 1000);
  if (seconds < 10) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return formatTs(d.toISOString());
}

export function confidenceScore(
  confidence: number | { score?: number; [key: string]: number | undefined } | null | undefined,
): number {
  if (typeof confidence === "number") return Math.max(0, Math.min(1, confidence));
  if (!confidence) return 0;
  if (typeof confidence.score === "number") return Math.max(0, Math.min(1, confidence.score));
  const values = Object.values(confidence).filter((v): v is number => typeof v === "number");
  if (!values.length) return 0;
  const avg = values.reduce((a, b) => a + b, 0) / values.length;
  return Math.max(0, Math.min(1, avg));
}

export function severityColor(severity: string): string {
  switch (severity.toUpperCase()) {
    case "CRITICAL":
      return "#F87171";
    case "HIGH":
    case "WARNING":
      return "#FBBF24";
    case "INFO":
    case "LOW":
      return "#22D3EE";
    default:
      return "#8B98A8";
  }
}
