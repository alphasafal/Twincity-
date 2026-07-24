import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        surface: {
          DEFAULT: "var(--surface)",
          elevated: "var(--surface-elevated)",
          muted: "var(--surface-muted)",
        },
        border: "var(--border)",
        muted: "var(--muted)",
        accent: {
          DEFAULT: "var(--accent)",
          soft: "var(--accent-soft)",
        },
        live: "var(--live)",
        savings: "var(--savings)",
        warning: "var(--warning)",
        critical: "var(--critical)",
        ai: "var(--ai)",
        graphite: {
          950: "#0b0d10",
          900: "#12151a",
          850: "#171b22",
          800: "#1c222b",
          700: "#2a3340",
          600: "#3a4556",
          500: "#5a677a",
          400: "#8490a1",
          300: "#b0b8c4",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
        display: ["var(--font-display)", "var(--font-sans)", "ui-sans-serif"],
      },
      boxShadow: {
        panel: "0 1px 0 rgba(255,255,255,0.04), 0 12px 40px rgba(0,0,0,0.35)",
      },
      backgroundImage: {
        "grid-faint":
          "linear-gradient(to right, rgba(132,144,161,0.08) 1px, transparent 1px), linear-gradient(to bottom, rgba(132,144,161,0.08) 1px, transparent 1px)",
        "hero-glow":
          "radial-gradient(ellipse 80% 60% at 70% 20%, rgba(34,211,238,0.12), transparent 55%), radial-gradient(ellipse 50% 40% at 20% 80%, rgba(52,211,153,0.08), transparent 50%)",
      },
      keyframes: {
        "pulse-live": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.45" },
        },
        "fade-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "draw-in": {
          from: { strokeDashoffset: "100" },
          to: { strokeDashoffset: "0" },
        },
        "hero-drift": {
          "0%, 100%": { transform: "translate3d(0,0,0) scale(1)" },
          "50%": { transform: "translate3d(1.5%, -1%, 0) scale(1.03)" },
        },
        "rise-in": {
          from: { opacity: "0", transform: "translateY(18px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "pulse-live": "pulse-live 2s ease-in-out infinite",
        "fade-up": "fade-up 0.45s ease-out both",
        "draw-in": "draw-in 1.2s ease-out both",
        "hero-drift": "hero-drift 18s ease-in-out infinite",
        "rise-in": "rise-in 0.7s cubic-bezier(0.22,1,0.36,1) both",
      },
    },
  },
  plugins: [],
};

export default config;
