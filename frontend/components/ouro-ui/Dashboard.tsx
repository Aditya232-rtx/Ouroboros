"use client";

import { useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";
import AgentsPanel from "@/components/live/AgentsPanel";
import { getReport, triggerResearch, getResearch } from "@/lib/api";
import type { Finding, ScanStatus, GatewayState, ResearchFinding, TranscriptAgent, AgentGraphNode } from "@/lib/types";
import "./Dashboard.css";

interface DataPoint {
  x: number;
  y: number;
}

const VULN_DATA_PRIMARY: DataPoint[] = [
  { x: 0, y: 12 }, { x: 1, y: 28 }, { x: 2, y: 19 },
  { x: 3, y: 45 }, { x: 4, y: 38 }, { x: 5, y: 62 },
  { x: 6, y: 55 }, { x: 7, y: 78 }, { x: 8, y: 65 },
  { x: 9, y: 92 }, { x: 10, y: 85 }, { x: 11, y: 71 },
];

const VULN_DATA_SECONDARY: DataPoint[] = [
  { x: 0, y: 8 }, { x: 1, y: 15 }, { x: 2, y: 12 },
  { x: 3, y: 22 }, { x: 4, y: 18 }, { x: 5, y: 30 },
  { x: 6, y: 28 }, { x: 7, y: 35 }, { x: 8, y: 32 },
  { x: 9, y: 42 }, { x: 10, y: 38 }, { x: 11, y: 34 },
];

const TIME_LABELS = ["00:00", "02:00", "04:00", "06:00", "08:00", "10:00", "12:00"];

const RESEARCH_RESULTS_CAP = 5;

function dataToPath(data: DataPoint[], width: number, height: number, maxY: number): string {
  const padX = 20;
  const padTop = 10;
  const padBot = 10;
  const usableW = width - padX * 2;
  const usableH = height - padTop - padBot;

  return data
    .map((pt, i) => {
      const x = padX + (pt.x / 11) * usableW;
      const y = padTop + usableH - (pt.y / maxY) * usableH;
      return `${i === 0 ? "M" : "L"}${x},${y}`;
    })
    .join(" ");
}

function dataToAreaPath(data: DataPoint[], width: number, height: number, maxY: number): string {
  const padX = 20;
  const padTop = 10;
  const padBot = 10;
  const usableW = width - padX * 2;
  const usableH = height - padTop - padBot;

  const lineParts = data
    .map((pt, i) => {
      const x = padX + (pt.x / 11) * usableW;
      const y = padTop + usableH - (pt.y / maxY) * usableH;
      return `${i === 0 ? "M" : "L"}${x},${y}`;
    })
    .join(" ");

  const lastX = padX + (data[data.length - 1].x / 11) * usableW;
  const firstX = padX + (data[0].x / 11) * usableW;
  const bottom = padTop + usableH;

  return `${lineParts} L${lastX},${bottom} L${firstX},${bottom} Z`;
}

interface RenderedPoint {
  cx: number;
  cy: number;
  value: number;
  time: string;
}

function getDataPoints(data: DataPoint[], width: number, height: number, maxY: number): RenderedPoint[] {
  const padX = 20;
  const padTop = 10;
  const padBot = 10;
  const usableW = width - padX * 2;
  const usableH = height - padTop - padBot;

  return data.map((pt) => ({
    cx: padX + (pt.x / 11) * usableW,
    cy: padTop + usableH - (pt.y / maxY) * usableH,
    value: pt.y,
    time: `${String(pt.x * 2).padStart(2, "0")}:00`,
  }));
}

const Icons = {
  settings: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  ),
  logout: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  ),
  bell: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  ),
  search: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  ),
  chevronDown: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="6 9 12 15 18 9" />
    </svg>
  ),
  arrowRight: (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="12 5 19 12 12 19" />
    </svg>
  ),
  zap: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  ),
  key: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
    </svg>
  ),
  fileText: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  ),
  upload: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  ),
  home: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  ),
};

const SEVERITY_LABELS: Record<string, string> = {
  critical: "● Critical",
  high: "● High",
  medium: "● Medium",
  low: "● Low",
};
const STATUS_MAP: Record<string, string> = { active: "Active", patched: "Patched", pending: "Pending" };

interface DashboardProps {
  user: User | null;
  onNavigate: (view: string) => void;
  onSignOut: () => void;
  logoSrc: string;
  bgSrc: string;
  runId?: string | null;
  targetUrl?: string;
  scanStatus?: ScanStatus;
  findings?: Finding[];
  findingsHistory?: { t: number; count: number }[];
  gatewayState?: GatewayState;
  onDeployAgent?: () => void;
}

const SEVERITY_TO_TABLE: Record<string, string> = {
  critical: "critical",
  high: "high",
  medium: "medium",
  low: "low",
  info: "low",
};

const FINDING_STATUS_MAP: Record<string, string> = {
  open: "active",
  fixed: "patched",
  escalated: "pending",
};

export default function Dashboard({
  user,
  onNavigate,
  onSignOut,
  logoSrc,
  bgSrc,
  runId = null,
  targetUrl = "",
  scanStatus = "idle",
  findings = [],
  findingsHistory = [],
  gatewayState = "disconnected",
  onDeployAgent,
}: DashboardProps) {
  const [profileOpen, setProfileOpen] = useState(false);
  const [hoveredDot, setHoveredDot] = useState<number | null>(null);
  const [reportState, setReportState] = useState<"idle" | "loading" | "ready" | "not_ready" | "error">("idle");
  const [complianceReport, setComplianceReport] = useState<string | null>(null);
  const [researchFindings, setResearchFindings] = useState<ResearchFinding[]>([]);
  const [researchTotal, setResearchTotal] = useState(0);
  const [researchState, setResearchState] = useState<"idle" | "running" | "ready">("idle");
  const [liveAgents, setLiveAgents] = useState<TranscriptAgent[]>([]);
  const [liveGraphAgents, setLiveGraphAgents] = useState<Map<string, AgentGraphNode>>(new Map());

  const chartW = 560;
  const chartH = 200;
  const maxY = 100;

  const hasLiveTimeline = findingsHistory.length >= 2;
  const liveXMax = Math.max(1, findingsHistory.length - 1);
  const liveMaxY = Math.max(1, ...findingsHistory.map((p) => p.count));
  const liveData: DataPoint[] = findingsHistory.map((p, i) => ({ x: (i / liveXMax) * 11, y: p.count }));

  const chartData = hasLiveTimeline ? liveData : VULN_DATA_PRIMARY;
  const chartMaxY = hasLiveTimeline ? liveMaxY : maxY;

  const primaryPath = dataToPath(chartData, chartW, chartH, chartMaxY);
  const secondaryPath = dataToPath(VULN_DATA_SECONDARY, chartW, chartH, maxY);
  const areaPath = dataToAreaPath(chartData, chartW, chartH, chartMaxY);
  const dots = getDataPoints(chartData, chartW, chartH, chartMaxY);
  const liveTimeLabels = findingsHistory.length
    ? [findingsHistory[0], findingsHistory[findingsHistory.length - 1]].map(
        (p) => `${Math.floor(p.t / 60)}:${String(Math.floor(p.t % 60)).padStart(2, "0")}`
      )
    : [];

  const userName = user?.user_metadata?.full_name || user?.email?.split("@")[0] || "Operator";
  const userInitial = userName.charAt(0).toUpperCase();

  const hasLiveScan = Boolean(runId);
  const agentsLarge = hasLiveScan && findings.length === 0 && (scanStatus === "starting" || scanStatus === "running");

  // Real stats derived from the same live agent/transcript data AgentsPanel polls.
  const toolCallTotal = Array.from(liveGraphAgents.values()).reduce((sum, a) => sum + a.toolCount, 0);

  // Auto-trigger the research agent sweep once a scan is underway. The
  // backend needs the scan's run_dir to exist first (set once the SSE events
  // poller detects the strix_runs directory), so retry until it accepts.
  useEffect(() => {
    if (!runId) return;
    let cancelled = false;
    setResearchState("idle");

    async function attempt() {
      if (cancelled) return;
      try {
        await triggerResearch(runId!);
        if (!cancelled) setResearchState("running");
      } catch {
        if (!cancelled) setTimeout(attempt, 2000);
      }
    }
    attempt();

    return () => {
      cancelled = true;
    };
  }, [runId]);

  // Poll for research results.
  useEffect(() => {
    if (!runId || researchState !== "running") return;
    const interval = setInterval(async () => {
      try {
        const data = await getResearch(runId);
        if (data.ready) {
          setResearchFindings(data.findings.slice(0, RESEARCH_RESULTS_CAP));
          setResearchTotal(data.findings.length);
          setResearchState("ready");
        }
      } catch {
        // keep polling
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [runId, researchState]);

  async function handleExportReport() {
    if (!runId) return;
    setReportState("loading");
    try {
      const data = await getReport(runId);
      if (data.compliance_report) {
        setComplianceReport(data.compliance_report);
        setReportState("ready");
      } else {
        setReportState("not_ready");
      }
    } catch {
      setReportState("error");
    }
  }

  return (
    <div className="gdash">
      <div className="gdash__bg">
        <img src={bgSrc} alt="" className="gdash__bg-img" />
        <div className="gdash__bg-overlay" />
      </div>

      <main className="gdash__main">
        <div className="gdash__topbar">
          <div className="gdash__topbar-left">
            <img src={logoSrc} alt="Ouroborous" className="gdash__logo" onClick={() => onNavigate("home")} />
            <div className="gdash__greeting">
              <span className="gdash__greeting-label">Command Deck</span>
              <span className="gdash__greeting-name">Welcome, {userName}</span>
            </div>
          </div>

          <div className="gdash__topbar-right">
            <button className="gdash__topbar-btn" title="Search">
              {Icons.search}
            </button>
            <button className="gdash__topbar-btn gdash__topbar-btn--notif" title="Notifications">
              {Icons.bell}
            </button>

            <div className="gdash__profile" onClick={(e) => e.stopPropagation()}>
              <button className="gdash__profile-btn" onClick={() => setProfileOpen(!profileOpen)}>
                <span className="gdash__profile-avatar">{userInitial}</span>
                <span className="gdash__profile-name">{userName}</span>
                <span className="gdash__profile-chevron">{Icons.chevronDown}</span>
              </button>

              {profileOpen && (
                <div className="gdash__profile-dropdown">
                  <button
                    className="gdash__profile-dropdown-item"
                    onClick={() => {
                      setProfileOpen(false);
                      onNavigate("home");
                    }}
                  >
                    {Icons.home} <span>Home</span>
                  </button>
                  <button className="gdash__profile-dropdown-item">
                    {Icons.settings} <span>Settings</span>
                  </button>
                  <div className="gdash__profile-dropdown-divider" />
                  <button
                    className="gdash__profile-dropdown-item gdash__profile-dropdown-item--danger"
                    onClick={() => {
                      setProfileOpen(false);
                      onSignOut();
                    }}
                  >
                    {Icons.logout} <span>Sign Out</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="gdash__header">
          <h1 className="gdash__title">Autonomous Defense Node</h1>
          <p className="gdash__subtitle">
            {hasLiveScan ? `Live assessment — ${targetUrl}` : "Real-time attack surface monitoring & purple team simulation"}
          </p>
        </div>

        {hasLiveScan && (
          <div style={{ marginBottom: "24px" }}>
            <AgentsPanel
              runId={runId}
              large={agentsLarge}
              onUpdate={({ agents, graphAgents }) => {
                setLiveAgents(agents);
                setLiveGraphAgents(graphAgents);
              }}
            />
          </div>
        )}

        <div className="gdash__stats-row">
          <div className="gdash__stat-card glass">
            <div className="gdash__stat-header">
              <div className="gdash__stat-icon gdash__stat-icon--attacks">⚡</div>
              <span className="gdash__stat-trend gdash__stat-trend--up">+12%</span>
            </div>
            <span className="gdash__stat-value">{hasLiveScan ? toolCallTotal : "1,420"}</span>
            <span className="gdash__stat-label">Simulated Attacks</span>
          </div>
          <div className="gdash__stat-card glass">
            <div className="gdash__stat-header">
              <div className="gdash__stat-icon gdash__stat-icon--findings">◈</div>
              <span className="gdash__stat-trend gdash__stat-trend--down">-8%</span>
            </div>
            <span className="gdash__stat-value">{hasLiveScan ? findings.length : 283}</span>
            <span className="gdash__stat-label">Total Findings</span>
          </div>
          <div className="gdash__stat-card glass">
            <div className="gdash__stat-header">
              <div className="gdash__stat-icon gdash__stat-icon--cve">⬡</div>
              <span className="gdash__stat-trend gdash__stat-trend--up">+3</span>
            </div>
            <span className="gdash__stat-value">
              {hasLiveScan ? findings.filter((f) => f.cve || f.cwe).length : 47}
            </span>
            <span className="gdash__stat-label">CVE / CWE Mapped</span>
          </div>
          <div className="gdash__stat-card glass">
            <div className="gdash__stat-header">
              <div className="gdash__stat-icon gdash__stat-icon--uptime">{hasLiveScan ? "⌁" : "∞"}</div>
            </div>
            <span className="gdash__stat-value">{hasLiveScan ? liveAgents.length : "99.4%"}</span>
            <span className="gdash__stat-label">{hasLiveScan ? "Agents Spawned" : "Node Uptime"}</span>
          </div>
        </div>

        <div className="gdash__grid">
          <div className="gdash__chart-card glass">
            <div className="gdash__card-topbar">
              <h3 className="gdash__card-title">Vulnerability Timeline</h3>
              {!hasLiveScan && <button className="gdash__card-filter">Last 24h {Icons.chevronDown}</button>}
            </div>

            {hasLiveScan && !hasLiveTimeline ? (
              <div style={{ padding: "48px 0", textAlign: "center", color: "var(--on-image-dim)", fontSize: "13px" }}>
                Waiting for the first finding to plot this scan&apos;s timeline…
              </div>
            ) : (
              <>
                <div className="gdash__chart-wrap">
                  <svg className="gdash__chart-svg" viewBox={`0 0 ${chartW} ${chartH}`} preserveAspectRatio="none">
                    <defs>
                      <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#f68025" stopOpacity="0.3" />
                        <stop offset="100%" stopColor="#f68025" stopOpacity="0" />
                      </linearGradient>
                    </defs>
                    {[0.25, 0.5, 0.75].map((frac) => (
                      <line
                        key={frac}
                        className="gdash__chart-gridline"
                        x1="20"
                        x2={chartW - 20}
                        y1={10 + (chartH - 20) * frac}
                        y2={10 + (chartH - 20) * frac}
                      />
                    ))}
                    <path className="gdash__chart-area" d={areaPath} />
                    {!hasLiveScan && <path className="gdash__chart-line gdash__chart-line--secondary" d={secondaryPath} />}
                    <path className="gdash__chart-line" d={primaryPath} />
                    {dots.map((dot, i) => (
                      <circle
                        key={i}
                        className="gdash__chart-dot"
                        cx={dot.cx}
                        cy={dot.cy}
                        r={hoveredDot === i ? 6 : 4}
                        onMouseEnter={() => setHoveredDot(i)}
                        onMouseLeave={() => setHoveredDot(null)}
                      />
                    ))}
                  </svg>

                  {hoveredDot !== null && (
                    <div
                      className="gdash__chart-tooltip"
                      style={{
                        left: `${(dots[hoveredDot].cx / chartW) * 100}%`,
                        top: `${(dots[hoveredDot].cy / chartH) * 100 - 18}%`,
                        transform: "translateX(-50%)",
                      }}
                    >
                      <div className="gdash__chart-tooltip-value">{dots[hoveredDot].value}</div>
                      <div className="gdash__chart-tooltip-label">
                        {hasLiveTimeline
                          ? `${Math.floor(findingsHistory[hoveredDot].t / 60)}:${String(Math.floor(findingsHistory[hoveredDot].t % 60)).padStart(2, "0")}`
                          : dots[hoveredDot].time}
                      </div>
                    </div>
                  )}
                </div>

                <div className="gdash__chart-labels">
                  {(hasLiveTimeline ? liveTimeLabels : TIME_LABELS).map((label, i) => (
                    <span key={`${label}-${i}`} className="gdash__chart-label">
                      {label}
                    </span>
                  ))}
                </div>

                <div className="gdash__chart-legend">
                  <div className="gdash__chart-legend-item">
                    <span className="gdash__chart-legend-dot gdash__chart-legend-dot--primary" />
                    Vulnerabilities Found
                  </div>
                  {!hasLiveScan && (
                    <div className="gdash__chart-legend-item">
                      <span className="gdash__chart-legend-dot gdash__chart-legend-dot--secondary" />
                      Patched
                    </div>
                  )}
                </div>
              </>
            )}
          </div>

          <div className="gdash__table-card glass">
            <div className="gdash__card-topbar">
              <h3 className="gdash__card-title">Attack Log</h3>
            </div>

            <div className="gdash__table-wrap">
              <table className="gdash__table">
                <thead>
                  <tr>
                    <th>Attack Time</th>
                    <th>Findings</th>
                    <th>CVE / CWE</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {!hasLiveScan ? (
                    <tr>
                      <td colSpan={4} className="gdash__table-empty">
                        Launch a scan to see live attack findings here.
                      </td>
                    </tr>
                  ) : findings.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="gdash__table-empty">
                        {scanStatus === "running" || scanStatus === "starting"
                          ? "Scan in progress — no findings yet."
                          : "No vulnerabilities found."}
                      </td>
                    </tr>
                  ) : (
                    findings.map((f) => {
                        const sev = SEVERITY_TO_TABLE[f.severity] ?? "low";
                        const status = FINDING_STATUS_MAP[f.status ?? "open"] ?? "active";
                        return (
                          <tr key={f.id}>
                            <td>
                              <span className="gdash__table-time">{f.title}</span>
                            </td>
                            <td>
                              <div className="gdash__table-findings">
                                <span className={`gdash__table-severity gdash__table-severity--${sev}`}>
                                  {SEVERITY_LABELS[sev]}
                                </span>
                              </div>
                            </td>
                            <td>
                              <span className="gdash__table-cve">{f.cve || f.cwe || "—"}</span>
                            </td>
                            <td>
                              <span className="gdash__table-status">
                                <span className={`gdash__table-status-dot gdash__table-status-dot--${status}`} />
                                {STATUS_MAP[status]}
                              </span>
                            </td>
                          </tr>
                        );
                      })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="gdash__bottom-row">
          <div className="gdash__agent-card glass">
            <div className="gdash__card-topbar">
              <h3 className="gdash__card-title">Active Agents</h3>
            </div>
            <div className="gdash__agent-list">
              {hasLiveScan && liveAgents.length > 0
                ? liveAgents.map((a) => {
                    const graphAgent = liveGraphAgents.get(a.id);
                    const isRunning = a.status === "running";
                    return (
                      <div className="gdash__agent-item" key={a.id}>
                        <div className={`gdash__agent-icon gdash__agent-icon--${a.parent_id ? "defense" : "offense"}`}>
                          {a.parent_id ? "\u{1F6E1}" : "⚔"}
                        </div>
                        <div className="gdash__agent-info">
                          <div className="gdash__agent-name">{a.name}</div>
                          <div className="gdash__agent-role">
                            {graphAgent ? `${graphAgent.toolCount} tools · ${graphAgent.messageCount} msgs` : a.id}
                          </div>
                        </div>
                        <span
                          className={`gdash__agent-status gdash__agent-status--${isRunning ? "active" : "standby"}`}
                        >
                          {isRunning ? "Active" : "Idle"}
                        </span>
                      </div>
                    );
                  })
                : hasLiveScan
                  ? (
                      <p style={{ fontSize: "13px", color: "var(--on-image-dim)", padding: "8px 0" }}>
                        Waiting for agents to spawn…
                      </p>
                    )
                  : (
                      <>
                        <div className="gdash__agent-item">
                          <div className="gdash__agent-icon gdash__agent-icon--offense">⚔</div>
                          <div className="gdash__agent-info">
                            <div className="gdash__agent-name">IDOR</div>
                            <div className="gdash__agent-role">Auth Validation Agent</div>
                          </div>
                          <span className="gdash__agent-status gdash__agent-status--active">Active</span>
                        </div>
                        <div className="gdash__agent-item">
                          <div className="gdash__agent-icon gdash__agent-icon--defense">🛡</div>
                          <div className="gdash__agent-info">
                            <div className="gdash__agent-name">SQL Injection</div>
                            <div className="gdash__agent-role">SQLi Validation Agent</div>
                          </div>
                          <span className="gdash__agent-status gdash__agent-status--active">Active</span>
                        </div>
                        <div className="gdash__agent-item">
                          <div className="gdash__agent-icon gdash__agent-icon--defense">🛡</div>
                          <div className="gdash__agent-info">
                            <div className="gdash__agent-name">XSS</div>
                            <div className="gdash__agent-role">Xss Validation Agent</div>
                          </div>
                          <span className="gdash__agent-status gdash__agent-status--active">Active</span>
                        </div>
                        <div className="gdash__agent-item">
                          <div className="gdash__agent-icon gdash__agent-icon--defense">🛡</div>
                          <div className="gdash__agent-info">
                            <div className="gdash__agent-name">XEE</div>
                            <div className="gdash__agent-role">XEE Validation Agent</div>
                          </div>
                          <span className="gdash__agent-status gdash__agent-status--active">Active</span>
                        </div>
                        <div className="gdash__agent-item">
                          <div className="gdash__agent-icon gdash__agent-icon--recon">🔍</div>
                          <div className="gdash__agent-info">
                            <div className="gdash__agent-name">Reconnaissance</div>
                            <div className="gdash__agent-role">Assets and Surface Mapping</div>
                          </div>
                          <span className="gdash__agent-status gdash__agent-status--standby">Standby</span>
                        </div>
                      </>
                    )}
            </div>
          </div>

          <div className="gdash__threat-card glass">
            <div className="gdash__card-topbar">
              <h3 className="gdash__card-title">Research Agent</h3>
              <span style={{ fontSize: "11px", color: "var(--on-image-dim)" }}>
                {!hasLiveScan && "CVE / CWE sweep"}
                {hasLiveScan && researchState === "idle" && "—"}
                {hasLiveScan && researchState === "running" && "running…"}
                {hasLiveScan &&
                  researchState === "ready" &&
                  (researchTotal > RESEARCH_RESULTS_CAP
                    ? `top ${RESEARCH_RESULTS_CAP} of ${researchTotal}`
                    : `${researchFindings.length} result${researchFindings.length === 1 ? "" : "s"}`)}
              </span>
            </div>
            <div className="gdash__research-list">
              {!hasLiveScan && (
                <p style={{ fontSize: "12px", color: "var(--on-image-dim)", padding: "8px 0" }}>
                  Runs automatically once a scan starts — cross-references the target&apos;s stack against recent CVEs.
                </p>
              )}
              {hasLiveScan && researchState !== "ready" && (
                <p style={{ fontSize: "12px", color: "var(--on-image-dim)", padding: "8px 0" }}>
                  Sweeping recent CVE/CWE disclosures for this target&apos;s stack…
                </p>
              )}
              {hasLiveScan && researchState === "ready" && researchFindings.length === 0 && (
                <div style={{ display: "flex", alignItems: "flex-start", gap: "8px", padding: "8px 0" }}>
                  <span style={{ color: "#4ade80", fontSize: "13px", lineHeight: "1.4" }}>✓</span>
                  <div>
                    <p style={{ fontSize: "12px", color: "var(--on-image)", margin: 0 }}>
                      Live NVD sweep complete — no new CVEs matched.
                    </p>
                    <p style={{ fontSize: "11px", color: "var(--on-image-dim)", margin: "2px 0 0" }}>
                      Cross-referenced {targetUrl || "this target"}&apos;s inferred stack against recent disclosures.
                    </p>
                  </div>
                </div>
              )}
              {researchFindings.map((r, i) => (
                <div key={i} className="gdash__research-item">
                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "baseline" }}>
                    {r.cve && <span style={{ color: "var(--gold)", fontWeight: 700, fontSize: "12px" }}>{r.cve}</span>}
                    {r.severity && (
                      <span style={{ color: "var(--on-image-dim)", fontSize: "10px", textTransform: "uppercase" }}>
                        {r.severity}
                      </span>
                    )}
                  </div>
                  {r.component && (
                    <div style={{ color: "var(--on-image)", fontSize: "11px", marginTop: "2px" }}>{r.component}</div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="gdash__actions-card glass">
            <div className="gdash__card-topbar">
              <h3 className="gdash__card-title">Quick Actions</h3>
            </div>
            <div className="gdash__actions-list">
              <button className="gdash__action-btn" onClick={() => onNavigate("home")}>
                <span className="gdash__action-icon gdash__action-icon--scan">{Icons.zap}</span>
                Launch New Scan
                <span className="gdash__action-arrow">{Icons.arrowRight}</span>
              </button>
              <button
                className="gdash__action-btn"
                onClick={onDeployAgent}
                disabled={!hasLiveScan || findings.length === 0}
                title={!hasLiveScan || findings.length === 0 ? "Run a scan with findings first" : undefined}
              >
                <span className="gdash__action-icon gdash__action-icon--deploy">{Icons.upload}</span>
                {gatewayState === "connected" ? "Ouro working via WhatsApp" : "Deploy Agent"}
                <span className="gdash__action-arrow">{Icons.arrowRight}</span>
              </button>
              <button
                className="gdash__action-btn"
                onClick={handleExportReport}
                disabled={!hasLiveScan || reportState === "loading"}
              >
                <span className="gdash__action-icon gdash__action-icon--report">{Icons.fileText}</span>
                {reportState === "loading" ? "Fetching report…" : "Export Report"}
                <span className="gdash__action-arrow">{Icons.arrowRight}</span>
              </button>
              <button className="gdash__action-btn">
                <span className="gdash__action-icon gdash__action-icon--keys">{Icons.key}</span>
                Manage Tokens
                <span className="gdash__action-arrow">{Icons.arrowRight}</span>
              </button>
            </div>
            {reportState === "not_ready" && (
              <p style={{ fontSize: "12px", color: "var(--on-image-dim)", marginTop: "8px" }}>
                Compliance report isn&apos;t ready yet — Ouro generates it once remediation finishes.
              </p>
            )}
            {reportState === "ready" && complianceReport && (
              <pre
                style={{
                  marginTop: "12px",
                  maxHeight: "240px",
                  overflow: "auto",
                  fontSize: "11px",
                  lineHeight: 1.6,
                  whiteSpace: "pre-wrap",
                  color: "var(--on-image-dim)",
                }}
              >
                {complianceReport}
              </pre>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
