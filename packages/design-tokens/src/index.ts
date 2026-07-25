/**
 * Minimal TwinPilot design tokens.
 * Apps may define richer themes locally; these are shared primitives.
 */

export const colors = {
  ink: "#0F1C2E",
  slate: "#334155",
  mist: "#E8EEF5",
  sky: "#1F6FEB",
  teal: "#0F766E",
  amber: "#B45309",
  danger: "#B91C1C",
  success: "#15803D",
  surface: "#F7FAFC",
} as const;

export const fonts = {
  sans: '"Source Sans 3", "Segoe UI", sans-serif',
  display: '"Fraunces", "Iowan Old Style", serif',
  mono: '"IBM Plex Mono", ui-monospace, monospace',
} as const;

export const space = {
  xs: "0.25rem",
  sm: "0.5rem",
  md: "1rem",
  lg: "1.5rem",
  xl: "2.5rem",
} as const;

export const radii = {
  sm: "0.25rem",
  md: "0.5rem",
  lg: "0.75rem",
} as const;

export type ColorToken = keyof typeof colors;
