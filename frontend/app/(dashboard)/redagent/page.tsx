"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import AgentLoopVisualization from "../../components/AgentLoopVisualization";
import TerminalLog from "../../components/TerminalLog";
import StatsCard from "../../components/StatsCard";
import { fetchVulnerabilities, fetchLogs, fetchScanStatus, downloadReportPdf, downloadInitialReportPdf } from "../../lib/api";
import { useScanLogs } from "../../hooks/useScanLogs";
import { Vulnerability, LogEntry, ScanStatus } from "../../lib/types";
import { ShieldAlert, Wrench, GitPullRequest, Timer, Download } from "lucide-react";

export default function RedAgentPage() {
    const searchParams = useSearchParams();
    const scanId = searchParams.get("scanId") || searchParams.get("scan_id") || "latest";

    const [vulnerabilities, setVulnerabilities] = useState<Vulnerability[]>([]);
    // Use hook for robust log fetching
    const { logs: allLogs } = useScanLogs(scanId);

    // Strict filtering for Red Agent logs only
    const logs = allLogs.filter(l => l.source === "RED_AGENT");

    const [scanStatus, setScanStatus] = useState<ScanStatus | null>(null);
    const [isDownloading, setIsDownloading] = useState(false);
    const [stats, setStats] = useState({
        vulnsFound: 0,
        autoFixed: 0,
        pullRequests: 0,
        scanTime: "0m"
    });

    const handleDownloadReport = async () => {
        setIsDownloading(true);
        try {
            await downloadInitialReportPdf(scanId);
        } catch (error) {
            console.error("Download failed:", error);
            alert("Failed to download report. Please try again.");
        } finally {
            setIsDownloading(false);
        }
    };

    useEffect(() => {
        const loadData = async () => {
            try {
                // Fetch vulnerabilities
                const vulns = await fetchVulnerabilities(scanId);
                // Keep existing if fetch fails/returns empty unexpectedly? 
                // Vulns API returns [] on error. Let's trust it for now but maybe safeguard?
                if (vulns) setVulnerabilities(vulns);

                // Logs are handled by useScanLogs hook now

                // Fetch scan status
                const status = await fetchScanStatus(scanId);
                if (status) {
                    setScanStatus(status);

                    // Fetch detailed data for accurate stats
                    try {
                        const detailRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/status/${scanId}/detail`);
                        const detailData = await detailRes.json();

                        // Calculate scan time
                        let scanTimeStr = "0m";
                        if (status?.started_at) {
                            const endTime = status?.completed_at ? new Date(status.completed_at).getTime() : Date.now();
                            const startTime = new Date(status.started_at).getTime();
                            const minutes = Math.floor((endTime - startTime) / 60000);
                            scanTimeStr = `${minutes}m`;
                        }

                        setStats({
                            vulnsFound: vulns.length,
                            autoFixed: detailData.fixes?.length || 0,
                            pullRequests: detailData.pr_url ? 1 : 0,
                            scanTime: scanTimeStr
                        });
                    } catch (detailError) {
                        console.error("Failed to fetch detail data, using fallback stats", detailError);
                        // Fallback to basic stats
                        setStats({
                            vulnsFound: vulns.length,
                            autoFixed: 0,
                            pullRequests: 0,
                            scanTime: "0m"
                        });
                    }
                }
            } catch (error) {
                console.error("Failed to load data:", error);
                // Do NOT clear state on error
            }
        };

        loadData();
        const interval = setInterval(loadData, 5000); // Poll every 5 seconds
        return () => clearInterval(interval);
    }, [scanId]);

    const criticalCount = vulnerabilities.filter(v => v.severity === "critical").length;

    return (
        <div className="h-[calc(100vh-8rem)] flex flex-col space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between pb-2">
                <div className="flex flex-col space-y-1">
                    <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center">
                        <span className="w-3 h-3 rounded-full bg-red-500 mr-3 animate-pulse"></span>
                        War Room
                    </h1>
                    <p className="text-slate-500 text-sm ml-6">
                        Monitoring autonomous remediation agents on <span className="bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded font-mono text-xs">{scanStatus?.repo_url?.replace("https://github.com/", "") || "Loading..."}</span>
                    </p>
                </div>
                <div className="flex items-center space-x-3">
                    <button
                        className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors flex items-center"
                        onClick={handleDownloadReport}
                        disabled={isDownloading}
                    >
                        <Download className="w-4 h-4 mr-2" />
                        {isDownloading ? "Downloading..." : "Download Report"}
                    </button>
                    <button className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors">
                        Pause Simulation
                    </button>
                    <button className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg text-sm font-medium shadow-md transition-colors flex items-center">
                        <ShieldAlert className="w-4 h-4 mr-2" />
                        Force Scan
                    </button>
                </div>
            </div>

            {/* Main Content: Split Grid */}
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-0">
                {/* Left: Visualization (1 Col) */}
                <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 flex flex-col items-center justify-center relative overflow-hidden shadow-sm">
                    <h3 className="absolute top-4 left-4 text-xs font-bold text-slate-400 uppercase tracking-widest">Agent Loop</h3>

                    {/* Simplified Agent Viz with Red Highlight */}
                    <div className="w-full h-full flex items-center justify-center scale-90">
                        <AgentLoopVisualization status="scanning" />
                    </div>

                    <div className="absolute bottom-6 flex items-center space-x-2 text-red-500 animate-pulse">
                        <div className="w-2 h-2 rounded-full bg-red-500"></div>
                        <span className="text-xs font-mono font-bold uppercase">Simulating Attack Vectors...</span>
                    </div>
                </div>

                {/* Right: Terminal Logs (2 Cols) */}
                <div className="lg:col-span-2 flex flex-col h-full min-h-0 bg-slate-950 rounded-xl border border-slate-800 overflow-hidden shadow-lg">
                    <TerminalLog
                        logs={logs}
                        classname="h-full border-none rounded-none"
                        title="red_agent_output.log"
                    />
                </div>
            </div>

            {/* Bottom: Stats Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatsCard
                    name="Vulnerabilities Found"
                    value={stats.vulnsFound.toString()}
                    icon={ShieldAlert}
                    color="red"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
                <StatsCard
                    name="Auto-Fixed"
                    value={stats.autoFixed.toString()}
                    icon={Wrench}
                    color="emerald"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
                <StatsCard
                    name="Pull Requests"
                    value={stats.pullRequests.toString()}
                    icon={GitPullRequest}
                    color="blue"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
                <StatsCard
                    name="Scan Time"
                    value={stats.scanTime}
                    icon={Timer}
                    color="purple"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
            </div>
        </div>
    );
}
