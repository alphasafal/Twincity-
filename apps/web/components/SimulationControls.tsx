"use client";

import { Pause, Play, RotateCcw, SkipForward } from "lucide-react";

export function SimulationControls({
  speed,
  onSpeed,
  onPlayback,
  busy,
  label,
}: {
  speed: number;
  onSpeed: (speed: number) => void;
  onPlayback: (action: "pause" | "resume" | "step" | "reset") => void;
  busy?: boolean;
  label?: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface/80 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Simulation playback</h3>
          <p className="text-xs text-muted">
            {label || "Controls the demo simulator via /api/v1/demo/*"}
          </p>
        </div>
        <span className="rounded border border-warning/40 bg-warning/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-warning">
          Simulated
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={() => onPlayback("pause")}
          className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-sm text-foreground disabled:opacity-50"
        >
          <Pause className="h-3.5 w-3.5" /> Pause
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => onPlayback("resume")}
          className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-sm text-foreground disabled:opacity-50"
        >
          <Play className="h-3.5 w-3.5" /> Resume
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => onPlayback("step")}
          className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-sm text-foreground disabled:opacity-50"
        >
          <SkipForward className="h-3.5 w-3.5" /> Step
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => onPlayback("reset")}
          className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-sm text-foreground disabled:opacity-50"
        >
          <RotateCcw className="h-3.5 w-3.5" /> Reset
        </button>
      </div>
      <div className="mt-4">
        <label className="mb-1 block text-xs uppercase tracking-wider text-muted">
          Speed ×{speed}
        </label>
        <input
          type="range"
          min={1}
          max={20}
          step={1}
          value={speed}
          disabled={busy}
          onChange={(e) => onSpeed(Number(e.target.value))}
          className="w-full accent-cyan-400"
        />
      </div>
    </div>
  );
}
