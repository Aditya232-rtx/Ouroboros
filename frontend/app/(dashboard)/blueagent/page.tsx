"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import StatsCard from "../../components/StatsCard";
import PatchPreview from "../../components/PatchPreview";
import TerminalLog from "../../components/TerminalLog";
import AgentLoopVisualization from "../../components/AgentLoopVisualization";
import { Zap, Code2, CheckCircle, Clock } from "lucide-react";
import { LogEntry, ScanStatus } from "../../lib/types";
import { fetchLogs, fetchScanStatus, fetchVulnerabilities } from "../../lib/api";

function BlueAgentContent() {
    const searchParams = useSearchParams();
    const scanId = searchParams.get("scan_id") || "latest";
    
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [scanStatus, setScanStatus] = useState<ScanStatus | null>(null);
    const [patchDiff, setPatchDiff] = useState<string>("");
    const [patchFile, setPatchFile] = useState<string>("src/components/Dashboard.vue");
    const [stats, setStats] = useState({
        patchesGenerated: 0,
        validationRate: 0,
        linesFixed: 0,
        pendingApproval: 0,
    });

    useEffect(() => {
        const loadData = async () => {
            try {
                // Fetch logs
                const logData = await fetchLogs(scanId);
                if (logData.length > 0) {
                    // Filter for blue_agent logs
                    const blueAgentLogs = logData.filter(l => 
                        l.source === "blue_agent" || l.source === "BLUE_AGENT" ||
                        l.message.toLowerCase().includes("fix") || l.message.toLowerCase().includes("patch")
                    );
                    setLogs(blueAgentLogs.length > 0 ? blueAgentLogs : logData);

                    // Extract latest patch diff from logs if available
                    const diffLog = [...logData].reverse().find(l =>
                        l.message.includes("diff") || l.message.includes("---") || l.message.includes("@@")
                    );
                    if (diffLog) setPatchDiff(diffLog.message);
                }
                
                // Fetch scan status
                const status = await fetchScanStatus(scanId);
                setScanStatus(status);
                
                // Fetch vulnerabilities to compute real stats
                const vulns = await fetchVulnerabilities(scanId);
                const totalFound = vulns.length;
                const fixedCount = vulns.filter(v => v.status === "remediated").length;
                const pendingCount = vulns.filter(v => v.status === "open").length;

                // Estimate lines fixed from vuln descriptions (fallback: 8 lines/fix avg)
                const estimatedLines = fixedCount * 8;

                // Validation rate = fixed / total (or 0 if no vulns)
                const rate = totalFound > 0 ? Math.round((fixedCount / totalFound) * 1000) / 10 : 0;

                // Extract file path from latest fix-related log
                const fileLog = [...logData].reverse().find(l =>
                    l.message.includes(".py") || l.message.includes(".js") || l.message.includes(".ts") || l.message.includes(".vue")
                );
                if (fileLog) {
                    const fileMatch = fileLog.message.match(/([\w/.-]+\.(py|js|ts|vue|jsx|tsx|java|go|rb))/);
                    if (fileMatch) setPatchFile(fileMatch[1]);
                }

                setStats({
                    patchesGenerated: fixedCount,
                    validationRate: rate,
                    linesFixed: estimatedLines,
                    pendingApproval: pendingCount,
                });
                
            } catch (error) {
                console.error("Failed to load data:", error);
            }
        };

        loadData();
        const interval = setInterval(loadData, 5000);
        return () => clearInterval(interval);
    }, [scanId]);

    return (
        <div className="h-[calc(100vh-8rem)] flex flex-col space-y-4">
            {/* Header */}
            <div className="flex flex-col space-y-1 pb-2">
                <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center">
                    <span className="w-3 h-3 rounded-full bg-blue-500 mr-3 animate-pulse"></span>
                    War Room
                </h1>
                <p className="text-slate-500 text-sm ml-6">
                    Monitoring autonomous remediation agents on <span className="bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded font-mono text-xs">{scanStatus?.repo_url?.replace("https://github.com/", "") || "Loading..."}</span>
                </p>
            </div>

            {/* Main Content: Split Grid */}
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-0">
                {/* Left: Visualization (1 Col) */}
                <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 flex flex-col items-center justify-center relative overflow-hidden shadow-sm">
                    <h3 className="absolute top-4 left-4 text-xs font-bold text-slate-400 uppercase tracking-widest">Agent Loop</h3>
                    <div className="absolute top-4 right-4 text-[10px] bg-blue-500/10 text-blue-500 px-2 py-1 rounded-full border border-blue-500/20 font-mono">
                        {scanStatus?.current_phase || "idle"}
                    </div>
                    {/* Simplified Agent Viz with Blue Highlight */}
                    <div className="w-full h-full flex items-center justify-center scale-90">
                        <AgentLoopVisualization status={(scanStatus?.status || "idle") as any} currentPhase={scanStatus?.current_phase} />
                    </div>

                    {scanStatus?.status && scanStatus.status !== "completed" && scanStatus.status !== "failed" && (
                        <div className="absolute bottom-6 bg-blue-50 dark:bg-slate-800/50 px-4 py-2 rounded-full border border-blue-100 dark:border-slate-700 flex items-center space-x-2">
                            <div className="w-4 h-4 rounded-full border-2 border-blue-500 border-t-transparent animate-spin"></div>
                            <span className="text-xs font-mono text-blue-600 dark:text-blue-400 font-medium">
                                {scanStatus.current_phase === "fixes_generated" ? "Validating Patch Safety..." :
                                 scanStatus.current_phase === "scan_complete" ? "Analyzing Vulnerabilities..." :
                                 scanStatus.current_phase === "governance_complete" ? "Generating Fixes..." :
                                 scanStatus.current_phase === "verification_complete" ? "Creating Pull Request..." :
                                 scanStatus.current_phase === "pr_created" ? "Generating Report..." :
                                 `${scanStatus.current_phase || "Processing"}...`}
                            </span>
                        </div>
                    )}
                </div>

                {/* Right: Console & Patch (2 Cols) */}
                <div className="lg:col-span-2 flex flex-col space-y-4 min-h-0 h-full">
                    {/* Top: Terminal Log (65%) */}
                    <div className="flex-[0.65] min-h-0 bg-slate-950 rounded-xl border border-slate-800 overflow-hidden shadow-lg flex flex-col">
                        <TerminalLog
                            logs={logs}
                            classname="h-full border-none rounded-none"
                            title="blue_agent_patch.log"
                        />
                    </div>

                    {/* Bottom: Patch Preview (35%) */}
                    <div className="flex-[0.35] min-h-0 bg-[#0d1117] rounded-xl border border-slate-800 overflow-hidden shadow-lg flex flex-col">
                        <div className="bg-[#161b22] px-4 py-2 border-b border-slate-800 flex justify-between items-center">
                            <span className="text-slate-400 text-xs font-bold font-mono flex items-center uppercase tracking-wider">
                                <Code2 className="w-3 h-3 mr-2" />
                                Patch Preview
                            </span>
                            <span className="text-slate-500 text-xs font-mono">{patchFile}</span>
                        </div>
                        <div className="flex-1 overflow-auto bg-[#0d1117]">
                            <PatchPreview
                                file={patchFile}
                                diff={patchDiff || "// No patch available yet"}
                                className="border-none bg-transparent"
                            />
                        </div>
                    </div>
                </div>
            </div>

            {/* Bottom: Stats Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatsCard
                    name="Patches Generated"
                    value={String(stats.patchesGenerated)}
                    icon={Zap}
                    color="blue"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
                <StatsCard
                    name="Validation Passes"
                    value={`${stats.validationRate}%`}
                    icon={CheckCircle}
                    color="emerald"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
                <StatsCard
                    name="Lines Fixed"
                    value={stats.linesFixed.toLocaleString()}
                    icon={Code2}
                    color="purple"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
                <StatsCard
                    name="Pending Approval"
                    value={String(stats.pendingApproval)}
                    icon={Clock}
                    color="amber"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
            </div>
        </div>
    );
}

export default function BlueAgentPage() {
    return (
        <Suspense fallback={<div className="p-8 text-center">Loading...</div>}>
            <BlueAgentContent />
        </Suspense>
    );
}