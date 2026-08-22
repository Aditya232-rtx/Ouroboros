"use client";

import type { Finding, Severity } from "@/lib/types";

const SEVERITY_COLORS: Record<Severity, { border: string; badge: string; dot: string }> = {
  critical: { border: "#ff1a40", badge: "bg-[#ff1a40]/20 text-[#ff4466]", dot: "bg-[#ff1a40]" },
  high:     { border: "#ff6b35", badge: "bg-[#ff6b35]/20 text-[#ff8c55]", dot: "bg-[#ff6b35]" },
  medium:   { border: "#ffcc00", badge: "bg-[#ffcc00]/20 text-[#ffcc00]", dot: "bg-[#ffcc00]" },
  low:      { border: "#00ccff", badge: "bg-[#00ccff]/20 text-[#00ccff]", dot: "bg-[#00ccff]" },
  info:     { border: "#6b6b8a", badge: "bg-[#6b6b8a]/20 text-[#9b9bb0]", dot: "bg-[#6b6b8a]" },
};

interface FindingCardProps {
  finding: Finding;
  index: number;
}

export function FindingCard({ finding, index }: FindingCardProps) {
  const sev = finding.severity ?? "info";
  const colors = SEVERITY_COLORS[sev] ?? SEVERITY_COLORS.info;
  const isFixed = finding.status === "fixed";
  const isEscalated = finding.status === "escalated";

  return (
    <div
      className="animate-slide-in rounded border p-4 transition-all"
      style={{
        animationDelay: `${index * 60}ms`,
        borderColor: isFixed ? "#00ff88" : isEscalated ? "#ffcc00" : colors.border,
        background: "var(--surface)",
        opacity: isFixed ? 0.7 : 1,
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className="inline-block w-2 h-2 rounded-full shrink-0 mt-1"
            style={{ background: colors.border }}
          />
          <span className="text-sm font-medium truncate" style={{ color: "var(--text)" }}>
            {finding.title}
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {isFixed && (
            <span className="text-xs px-2 py-0.5 rounded" style={{ background: "#00ff8820", color: "#00ff88" }}>
              FIXED
            </span>
          )}
          {isEscalated && (
            <span className="text-xs px-2 py-0.5 rounded" style={{ background: "#ffcc0020", color: "#ffcc00" }}>
              ESCALATED
            </span>
          )}
          <span className={`text-xs px-2 py-0.5 rounded uppercase font-bold ${colors.badge}`}>
            {sev}
          </span>
        </div>
      </div>

      <p className="mt-2 text-xs leading-relaxed" style={{ color: "var(--text-dim)" }}>
        {finding.description}
      </p>

      <div className="mt-2 flex flex-wrap gap-3 text-xs" style={{ color: "var(--text-dim)" }}>
        {finding.cve && (
          <span className="font-mono" style={{ color: "var(--cyan)" }}>{finding.cve}</span>
        )}
        {finding.cwe && (
          <span className="font-mono" style={{ color: "var(--yellow)" }}>{finding.cwe}</span>
        )}
        {finding.url && (
          <span className="truncate max-w-xs" style={{ color: "var(--text-dim)" }}>{finding.url}</span>
        )}
      </div>
    </div>
  );
}
