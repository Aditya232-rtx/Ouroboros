"use client";

import type { ScanStatus } from "@/lib/types";

interface ScanProgressProps {
  status: ScanStatus;
  url: string;
  findingsCount: number;
}

const STATUS_LABELS: Record<ScanStatus, string> = {
  idle: "",
  starting: "Initializing Fang agents...",
  running: "Scanning target — agents active",
  completed: "Scan complete",
  failed: "Scan failed",
};

export function ScanProgress({ status, url, findingsCount }: ScanProgressProps) {
  if (status === "idle") return null;

  const isActive = status === "starting" || status === "running";

  return (
    <div
      className="w-full max-w-2xl mx-auto rounded p-4 animate-fade-in"
      style={{ border: "1px solid var(--border)", background: "var(--surface)" }}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {isActive && (
            <span
              className="w-2 h-2 rounded-full animate-pulse-green"
              style={{ background: "var(--green)" }}
            />
          )}
          {status === "completed" && (
            <span className="text-xs" style={{ color: "var(--green)" }}>✓</span>
          )}
          {status === "failed" && (
            <span className="text-xs" style={{ color: "var(--red)" }}>✗</span>
          )}
          <span
            className="text-xs uppercase tracking-widest"
            style={{ color: isActive ? "var(--green)" : status === "completed" ? "var(--green)" : "var(--red)" }}
          >
            {STATUS_LABELS[status]}
          </span>
        </div>
        {findingsCount > 0 && (
          <span className="text-xs font-bold" style={{ color: "var(--yellow)" }}>
            {findingsCount} finding{findingsCount !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      <div className="flex items-center gap-2 text-xs" style={{ color: "var(--text-dim)" }}>
        <span className="font-mono truncate">{url}</span>
      </div>

      {isActive && (
        <div className="mt-3 h-px w-full overflow-hidden rounded" style={{ background: "var(--border)" }}>
          <div
            className="h-full rounded"
            style={{
              width: status === "starting" ? "15%" : "60%",
              background: "linear-gradient(90deg, var(--green-dim), var(--green))",
              transition: "width 2s ease",
              boxShadow: "0 0 8px var(--green)",
            }}
          />
        </div>
      )}
    </div>
  );
}
