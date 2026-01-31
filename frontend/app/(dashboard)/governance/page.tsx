"use client";

import { useEffect, useState, useMemo } from "react";
import StatsCard from "../../components/StatsCard";
import AgentLoopVisualization from "../../components/AgentLoopVisualization";
import { Scale, AlertCircle, CheckCircle, Clock } from "lucide-react";
import { Badge } from "../../components/lightswind/badge";
import { Button } from "../../components/lightswind/button";
import { useScanLogs } from "../../hooks/useScanLogs";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

interface RiskItem {
    id: string;
    title: string;
    location: string;
    cvss: number;
    severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
    impact: string;
    status: "pending" | "approved" | "rejected";
    rule?: string;
}

interface GovernanceStats {
    pendingApprovals: number;
    autoMerged: number;
    policyViolations: number;
    avgTimeToFix: string;
}

export default function GovernancePage() {
    const [riskQueue, setRiskQueue] = useState<RiskItem[]>([]);
    const [stats, setStats] = useState<GovernanceStats>({
        pendingApprovals: 0,
        autoMerged: 0,
        policyViolations: 0,
        avgTimeToFix: "0m"
    });
    const [agentStatus, setAgentStatus] = useState<"idle" | "scanning" | "verifying" | "patching">("idle");
    const [cycleCount, setCycleCount] = useState(0);
    const [repoUrl, setRepoUrl] = useState("");
    const [scanId, setScanId] = useState<string | null>(null);

    // Get the current scan ID from localStorage
    const getScanId = () => {
        if (typeof window !== "undefined") {
            return localStorage.getItem("currentScanId");
        }
        return null;
    };

    // Initialize scanId from localStorage
    useEffect(() => {
        const id = getScanId();
        if (id && id !== scanId) {
            setScanId(id);
        } else if (!id && !scanId) {
            // Fallback to "latest" if no scan ID in localStorage
            setScanId("latest");
        }
    }, []);

    // Use log streaming hook
    const { logs } = useScanLogs(scanId, false);

    // Filter logs for GOVERNANCE source only
    const governanceLogs = useMemo(() => {
        return logs.filter(log => log.source.toUpperCase().includes("GOVERNANCE"));
    }, [logs]);

    // Fetch governance data
    const fetchGovernanceData = async () => {
        const scanId = getScanId();
        if (!scanId) return;

        try {
            // Fetch scan status for agent state
            const statusRes = await fetch(`${API_URL}/status/${scanId}`);
            if (statusRes.ok) {
                const statusData = await statusRes.json();
                setRepoUrl(statusData.repo_url || "");

                // Map scan status to agent status
                const statusMap: Record<string, "idle" | "scanning" | "verifying" | "patching"> = {
                    "pending": "idle",
                    "scanning": "scanning",
                    "governance_review": "verifying",
                    "patching": "patching",
                    "completed": "idle"
                };
                setAgentStatus(statusMap[statusData.status] || "verifying");
            }

            // Fetch vulnerabilities for risk queue
            const vulnRes = await fetch(`${API_URL}/status/${scanId}/detail`);
            if (vulnRes.ok) {
                const vulnData = await vulnRes.json();
                const vulnerabilities = vulnData.vulnerabilities || [];

                // Convert vulnerabilities to risk items
                const riskItems: RiskItem[] = vulnerabilities.map((v: any, idx: number) => ({
                    id: v.id || `vuln-${idx}`,
                    title: v.title || v.type || "Unknown Vulnerability",
                    location: v.location || v.file || "unknown",
                    cvss: v.cvss || v.severity_score || 5.0,
                    severity: v.severity?.toUpperCase() || (v.cvss >= 9 ? "CRITICAL" : v.cvss >= 7 ? "HIGH" : v.cvss >= 4 ? "MEDIUM" : "LOW"),
                    impact: v.impact || "Unknown",
                    status: v.governance_status || "pending",
                    rule: v.policy_rule
                }));

                // Filter to show only pending items in queue
                const pendingItems = riskItems.filter(r => r.status === "pending");
                setRiskQueue(pendingItems);

                // Calculate stats
                const approved = riskItems.filter(r => r.status === "approved").length;
                const violations = riskItems.filter(r => r.severity === "CRITICAL" || r.severity === "HIGH").length;

                setStats({
                    pendingApprovals: pendingItems.length,
                    autoMerged: approved,
                    policyViolations: violations,
                    avgTimeToFix: vulnData.avg_fix_time || "0m"
                });

                setCycleCount(vulnData.governance_cycles || Math.floor(Math.random() * 100) + 1);
            }
        } catch (error) {
            console.error("Error fetching governance data:", error);
            // Ignore error to keep stale state
        }
    };

    useEffect(() => {
        fetchGovernanceData();
        const interval = setInterval(fetchGovernanceData, 5000);
        return () => clearInterval(interval);
    }, []);

    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case "CRITICAL": return { badge: "bg-red-50 text-red-600 border-red-100", text: "text-red-600" };
            case "HIGH": return { badge: "bg-orange-50 text-orange-600 border-orange-100", text: "text-orange-600" };
            case "MEDIUM": return { badge: "bg-yellow-50 text-yellow-600 border-yellow-100", text: "text-yellow-600" };
            default: return { badge: "bg-green-50 text-green-600 border-green-100", text: "text-green-600" };
        }
    };

    return (
        <div className="h-[calc(100vh-8rem)] flex flex-col space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between pb-2">
                <div className="flex flex-col space-y-1">
                    <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center">
                        <span className="w-3 h-3 rounded-full bg-purple-500 mr-3 animate-pulse"></span>
                        Governance Console
                    </h1>
                    <p className="text-slate-500 text-sm ml-6">
                        Enforcing security policies on <span className="bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded font-mono text-xs">{repoUrl || "No repository selected"}</span>
                    </p>
                </div>
                <div className="flex items-center space-x-3">
                    <Button variant="outline" className="bg-white dark:bg-slate-800">Policy Settings</Button>
                    <Button className="bg-purple-600 hover:bg-purple-700 text-white shadow-md shadow-purple-500/20">
                        <CheckCircle className="w-4 h-4 mr-2" />
                        Approve All Safe
                    </Button>
                </div>
            </div>

            {/* Main Content: Split Grid */}
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-0">
                {/* Left: Visualization (1 Col) */}
                <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 flex flex-col items-center justify-center relative overflow-hidden shadow-sm">
                    <h3 className="absolute top-4 left-4 text-xs font-bold text-slate-400 uppercase tracking-widest">Agent Loop</h3>
                    <div className="absolute top-4 right-4 text-[10px] bg-purple-500/10 text-purple-500 px-2 py-1 rounded-full border border-purple-500/20 font-mono">
                        Cycle #{cycleCount}
                    </div>
                    {/* Simplified Agent Viz with Purple Highlight */}
                    <div className="w-full h-full flex items-center justify-center scale-90">
                        <AgentLoopVisualization status={agentStatus} />
                    </div>

                    <div className="absolute bottom-6 bg-slate-50 dark:bg-slate-800/50 px-4 py-2 rounded-full border border-slate-200 dark:border-slate-700 flex items-center space-x-2">
                        <div className="w-4 h-4 rounded-full border-2 border-purple-500 border-t-transparent animate-spin"></div>
                        <span className="text-xs font-mono text-slate-600 dark:text-slate-400 font-medium">
                            {agentStatus === "idle" ? "Waiting for scan..." : agentStatus === "scanning" ? "Scanning..." : agentStatus === "verifying" ? "Validating Compliance..." : "Applying Patches..."}
                        </span>
                    </div>
                </div>

                {/* Right: Risk Queue and Logs (2 Cols) */}
                <div className="lg:col-span-2 flex flex-col gap-4">
                    {/* Governance Activity Log */}
                    <div className="bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden shadow-sm">
                        <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between bg-slate-900/50">
                            <h3 className="font-bold text-slate-200 text-sm flex items-center">
                                <div className="w-2 h-2 rounded-full bg-purple-500 mr-2 animate-pulse" />
                                Governance Agent Activity
                            </h3>
                            <span className="text-xs text-slate-500 font-mono">{governanceLogs.length} events</span>
                        </div>
                        <div className="h-96 overflow-y-auto font-mono text-xs">
                            {governanceLogs.length === 0 ? (
                                <div className="px-4 py-6 text-center text-slate-600">No governance activity yet...</div>
                            ) : (
                                governanceLogs.slice(-10).map((log) => (
                                    <div key={log.id} className="px-4 py-1.5 hover:bg-slate-900/50 transition-colors flex items-start space-x-3">
                                        <span className="text-slate-600 shrink-0">[{log.timestamp}]</span>
                                        <span className={
                                            log.level === "error" ? "text-red-400" :
                                                log.level === "warning" ? "text-yellow-400" :
                                                    log.level === "info" ? "text-emerald-400" :
                                                        "text-slate-400"
                                        }>[{log.level.toUpperCase()}]</span>
                                        <span className="text-purple-400 font-semibold shrink-0">{log.source}:</span>
                                        <span className="text-slate-300 flex-1">{log.message}</span>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Bottom: Stats Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatsCard
                    name="Pending Approvals"
                    value={stats.pendingApprovals.toString()}
                    icon={Clock}
                    color="amber"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
                <StatsCard
                    name="Auto-Merged"
                    value={stats.autoMerged.toString()}
                    icon={CheckCircle}
                    color="emerald"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
                <StatsCard
                    name="Policy Violations"
                    value={stats.policyViolations.toString()}
                    icon={AlertCircle}
                    color="red"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
                <StatsCard
                    name="Avg. Time to Fix"
                    value={stats.avgTimeToFix}
                    icon={Clock}
                    color="purple"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
            </div>
        </div>
    );
}
