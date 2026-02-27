'use client';

import { useState, useEffect, useRef } from 'react';
import {
    Search,
    Zap,
    AlertTriangle,
    ShieldAlert,
    ShieldCheck,
    Info,
    RefreshCw,
    ExternalLink,
    ChevronDown,
    ChevronUp,
    Brain,
    Clock,
    Activity,
} from 'lucide-react';
import { cn } from '../../lib/utils';

// ─── Types ───────────────────────────────────────────────────────────────────

interface Finding {
    id: string;
    cve_id: string;
    title: string;
    severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN';
    cvss_score: number | null;
    cwe: string;
    description: string;
    poc_code: string;
    discovered_at: string;
    affected_assets: string[];
    solution: string | null;
}

// ─── Severity utilities ──────────────────────────────────────────────────────

const SEVERITY_CONFIG = {
    CRITICAL: {
        icon: ShieldAlert,
        badge: 'bg-red-500/10 text-red-400 border-red-500/20',
        row: 'border-l-2 border-l-red-500',
        dot: 'bg-red-500',
        label: 'CRITICAL',
    },
    HIGH: {
        icon: AlertTriangle,
        badge: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
        row: 'border-l-2 border-l-amber-500',
        dot: 'bg-amber-500',
        label: 'HIGH',
    },
    MEDIUM: {
        icon: Info,
        badge: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
        row: 'border-l-2 border-l-blue-500',
        dot: 'bg-blue-400',
        label: 'MEDIUM',
    },
    LOW: {
        icon: ShieldCheck,
        badge: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
        row: 'border-l-2 border-l-slate-500',
        dot: 'bg-slate-500',
        label: 'LOW',
    },
    UNKNOWN: {
        icon: Info,
        badge: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
        row: 'border-l-2 border-l-slate-600',
        dot: 'bg-slate-600',
        label: 'UNKNOWN',
    },
} as const;

function getSeverityConf(sev: string) {
    return SEVERITY_CONFIG[sev as keyof typeof SEVERITY_CONFIG] ?? SEVERITY_CONFIG.UNKNOWN;
}

function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    });
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function FindingCard({ finding }: { finding: Finding }) {
    const [expanded, setExpanded] = useState(false);
    const conf = getSeverityConf(finding.severity);
    const SevIcon = conf.icon;

    return (
        <div className={cn(
            'bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800',
            'shadow-sm overflow-hidden transition-all duration-200',
            conf.row,
        )}>
            {/* Header row */}
            <button
                onClick={() => setExpanded(!expanded)}
                className="w-full text-left px-5 py-4 flex items-start gap-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
            >
                {/* Severity badge */}
                <span className={cn(
                    'inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] font-bold font-mono',
                    'border whitespace-nowrap shrink-0 mt-0.5',
                    conf.badge,
                )}>
                    <SevIcon className="h-3 w-3" />
                    {conf.label}
                    {finding.cvss_score !== null && (
                        <span className="opacity-70">· {finding.cvss_score.toFixed(1)}</span>
                    )}
                </span>

                {/* Title + meta */}
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-sm font-semibold text-slate-900 dark:text-white truncate">
                            {finding.cve_id || finding.id}
                        </span>
                        {finding.cwe && (
                            <span className="text-[10px] font-mono text-slate-400 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">
                                {finding.cwe.trim()}
                            </span>
                        )}
                    </div>
                    <p className="mt-0.5 text-sm text-slate-600 dark:text-slate-400 line-clamp-2">
                        {finding.title}
                    </p>
                    <div className="mt-1.5 flex items-center gap-3 text-[11px] text-slate-400 font-mono">
                        <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {formatDate(finding.discovered_at)}
                        </span>
                        {finding.affected_assets[0] && (
                            <span className="flex items-center gap-1 truncate">
                                <Activity className="h-3 w-3" />
                                {finding.affected_assets[0]}
                            </span>
                        )}
                    </div>
                </div>

                {/* Expand toggle */}
                <div className="shrink-0 text-slate-400">
                    {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                </div>
            </button>

            {/* Expanded body */}
            {expanded && (
                <div className="border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/50 px-5 py-4 space-y-4">
                    {/* Description */}
                    <div>
                        <h4 className="text-[10px] font-mono font-semibold text-slate-500 uppercase tracking-widest mb-1">
                            Description
                        </h4>
                        <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                            {finding.description}
                        </p>
                    </div>

                    {/* PoC Code */}
                    {finding.poc_code && (
                        <div>
                            <h4 className="text-[10px] font-mono font-semibold text-slate-500 uppercase tracking-widest mb-1">
                                Proof of Concept
                            </h4>
                            <div className="bg-slate-950 rounded-lg border border-slate-800 p-3 overflow-x-auto">
                                <pre className="text-xs font-mono text-emerald-400 whitespace-pre-wrap break-all">
                                    {finding.poc_code}
                                </pre>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

// ─── Animated log line ───────────────────────────────────────────────────────

function AgentStatusBanner({ isRunning, lastTarget }: { isRunning: boolean; lastTarget: string }) {
    if (!isRunning) return null;
    return (
        <div className="flex items-center gap-3 px-4 py-2.5 bg-cyan-500/10 border border-cyan-500/20 rounded-xl text-sm font-mono text-cyan-400">
            <div className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse shrink-0" />
            <span className="truncate">
                research_agent: Analyzing <span className="text-cyan-300 font-semibold">{lastTarget}</span>
                <span className="animate-pulse ml-1">▋</span>
            </span>
        </div>
    );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ResearchPage() {
    const [findings, setFindings] = useState<Finding[]>([]);
    const [url, setUrl] = useState('');
    const [isDispatching, setIsDispatching] = useState(false);
    const [agentRunning, setAgentRunning] = useState(false);
    const [lastTarget, setLastTarget] = useState('');
    const [searchTerm, setSearchTerm] = useState('');
    const [severityFilter, setSeverityFilter] = useState<string>('ALL');
    const [isRefreshing, setIsRefreshing] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    // ── Fetch findings ──────────────────────────────────────────────────────
    const fetchFindings = async (quiet = false) => {
        if (!quiet) setIsRefreshing(true);
        try {
            const res = await fetch(`${API_URL}/api/research/findings`);
            if (res.ok) {
                const data = await res.json();
                setFindings(data.findings ?? []);
            }
        } catch { /* backend offline */ }
        finally { if (!quiet) setIsRefreshing(false); }
    };

    useEffect(() => {
        fetchFindings();
        const iv = setInterval(() => fetchFindings(true), 5000);
        return () => clearInterval(iv);
    }, []);

    // ── Dispatch agent ──────────────────────────────────────────────────────
    const dispatchAgent = async () => {
        if (!url.trim() || isDispatching) return;
        setIsDispatching(true);
        setAgentRunning(true);
        setLastTarget(url.trim());
        try {
            await fetch(`${API_URL}/api/research/trigger`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url.trim() }),
            });
            setUrl('');
        } catch { /* ignore */ }
        finally { setIsDispatching(false); }

        // Agent runs in background; stop "running" indicator after 90s max
        setTimeout(() => setAgentRunning(false), 90_000);
    };

    // ── Filter findings ─────────────────────────────────────────────────────
    const filtered = findings.filter(f => {
        const matchSev = severityFilter === 'ALL' || f.severity === severityFilter;
        const q = searchTerm.toLowerCase();
        const matchQ = !q || f.cve_id?.toLowerCase().includes(q) || f.title?.toLowerCase().includes(q);
        return matchSev && matchQ;
    });

    // ── Stats ───────────────────────────────────────────────────────────────
    const stats = {
        total: findings.length,
        critical: findings.filter(f => f.severity === 'CRITICAL').length,
        high: findings.filter(f => f.severity === 'HIGH').length,
        medium: findings.filter(f => f.severity === 'MEDIUM').length,
    };

    const SHARD_SEVERITIES = ['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];

    return (
        <div className="space-y-6">
            {/* ── Page header ─────────────────────────────────────────────── */}
            <div className="flex items-start justify-between flex-wrap gap-4">
                <div>
                    <h1 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                        <Brain className="h-5 w-5 text-cyan-500" />
                        Research Agent Console
                    </h1>
                    <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                        Dispatch the LangGraph agent to scrape NVD/Exploit-DB and store findings in local vector memory.
                    </p>
                </div>
                <button
                    onClick={() => fetchFindings()}
                    disabled={isRefreshing}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors text-sm font-medium text-slate-600 dark:text-slate-400"
                >
                    <RefreshCw className={cn('h-4 w-4', isRefreshing && 'animate-spin')} />
                    Refresh
                </button>
            </div>

            {/* ── Stats strip ─────────────────────────────────────────────── */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {[
                    { label: 'Total Findings', value: stats.total, color: 'text-cyan-500', bg: 'bg-cyan-500/10 border-cyan-500/20' },
                    { label: 'Critical', value: stats.critical, color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/20' },
                    { label: 'High', value: stats.high, color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20' },
                    { label: 'Medium', value: stats.medium, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20' },
                ].map(s => (
                    <div key={s.label} className={cn('rounded-xl border p-4 shadow-sm', s.bg)}>
                        <p className="text-xs font-mono text-slate-500 dark:text-slate-400 uppercase tracking-widest">{s.label}</p>
                        <p className={cn('mt-1 text-3xl font-bold tabular-nums', s.color)}>{s.value}</p>
                    </div>
                ))}
            </div>

            {/* ── Dispatch panel ──────────────────────────────────────────── */}
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm p-5">
                <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
                    <Zap className="h-4 w-4 text-cyan-500" />
                    Dispatch Intelligence Scrape
                </h2>
                <div className="flex gap-3 flex-wrap sm:flex-nowrap">
                    <div className="relative flex-1 min-w-0">
                        <ExternalLink className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 pointer-events-none" />
                        <input
                            ref={inputRef}
                            type="url"
                            value={url}
                            onChange={e => setUrl(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && dispatchAgent()}
                            placeholder="https://nvd.nist.gov/vuln/detail/CVE-XXXX-XXXXX"
                            className={cn(
                                'w-full pl-10 pr-4 py-2.5 rounded-lg border font-mono text-sm',
                                'border-slate-200 dark:border-slate-700',
                                'bg-slate-50 dark:bg-slate-800',
                                'text-slate-900 dark:text-white placeholder:text-slate-400',
                                'focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500',
                                'transition-colors',
                            )}
                        />
                    </div>
                    <button
                        onClick={dispatchAgent}
                        disabled={isDispatching || !url.trim()}
                        className={cn(
                            'inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all shrink-0',
                            'focus:outline-none focus:ring-2 focus:ring-cyan-500/50',
                            isDispatching || !url.trim()
                                ? 'bg-slate-200 dark:bg-slate-700 text-slate-400 cursor-not-allowed'
                                : 'bg-cyan-500 hover:bg-cyan-400 text-slate-950 shadow-sm shadow-cyan-500/20',
                        )}
                    >
                        {isDispatching ? (
                            <>
                                <div className="h-4 w-4 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
                                Dispatching…
                            </>
                        ) : (
                            <>
                                <Brain className="h-4 w-4" />
                                Deploy Agent
                            </>
                        )}
                    </button>
                </div>
                <p className="mt-2 text-[11px] text-slate-400 font-mono">
                    The agent scrapes the URL, extracts CVE metadata via local LLM, stores it in ChromaDB, and saves a report.
                </p>
            </div>

            {/* ── Running indicator ────────────────────────────────────────── */}
            <AgentStatusBanner isRunning={agentRunning} lastTarget={lastTarget} />

            {/* ── Findings list ────────────────────────────────────────────── */}
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
                {/* Toolbar */}
                <div className="flex flex-wrap items-center gap-3 px-5 py-3 border-b border-slate-200 dark:border-slate-800">
                    {/* Search */}
                    <div className="relative flex-1 min-w-[180px]">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400 pointer-events-none" />
                        <input
                            type="text"
                            value={searchTerm}
                            onChange={e => setSearchTerm(e.target.value)}
                            placeholder="Search CVE ID or title…"
                            className={cn(
                                'w-full pl-8 pr-3 py-1.5 rounded-lg border text-sm',
                                'border-slate-200 dark:border-slate-700',
                                'bg-slate-50 dark:bg-slate-800',
                                'text-slate-900 dark:text-white placeholder:text-slate-400',
                                'focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500',
                            )}
                        />
                    </div>

                    {/* Severity filters */}
                    <div className="flex gap-1 flex-wrap">
                        {SHARD_SEVERITIES.map(sev => (
                            <button
                                key={sev}
                                onClick={() => setSeverityFilter(sev)}
                                className={cn(
                                    'px-2.5 py-1 rounded-md text-[11px] font-mono font-semibold border transition-colors',
                                    severityFilter === sev
                                        ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400'
                                        : 'bg-transparent border-slate-200 dark:border-slate-700 text-slate-500 hover:border-slate-300 dark:hover:border-slate-600',
                                )}
                            >
                                {sev}
                            </button>
                        ))}
                    </div>

                    <span className="ml-auto text-xs font-mono text-slate-400">
                        {filtered.length} / {findings.length} findings
                    </span>
                </div>

                {/* Cards */}
                <div className="p-4 space-y-3">
                    {filtered.length === 0 ? (
                        <div className="py-16 flex flex-col items-center justify-center text-center space-y-3">
                            <Brain className="h-10 w-10 text-slate-300 dark:text-slate-700" />
                            <p className="text-sm text-slate-500 dark:text-slate-400">
                                {findings.length === 0
                                    ? 'No findings yet — deploy the agent above to start researching.'
                                    : 'No findings match your current filters.'}
                            </p>
                        </div>
                    ) : (
                        filtered.map(f => <FindingCard key={f.id} finding={f} />)
                    )}
                </div>
            </div>
        </div>
    );
}
