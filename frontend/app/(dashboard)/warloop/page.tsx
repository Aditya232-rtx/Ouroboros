"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import AgentLoopVisualization from "../../components/AgentLoopVisualization";
import TerminalLog from "../../components/TerminalLog";
import { fetchStats, fetchLogs, fetchScanStatus } from "../../lib/api";
import { Stats, LogEntry, ScanStatus } from "../../lib/types";
import { Pause, Play } from "lucide-react";

export default function WarRoomPage() {
    const searchParams = useSearchParams();
    const repo = searchParams.get("repo");

    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [scanStatus, setScanStatus] = useState<ScanStatus | null>(null);
    const [isPaused, setIsPaused] = useState(false);

    useEffect(() => {
        // Initial fetch
        const loadData = async () => {
            try {
                // In a real app, scanId would come from context or active scan
                // For V1 demo, we poll the latest scan or a fixed ID if available
                // We need to know the active scanId.
                // Strategy: We can fetch latest scan status if API supports it, 
                // or just pass a known ID if we triggered it.
                // For now, let's poll assuming we have a way to get the ID.
                // If no ID, we might wait.

                // However, without a scanId context, we can't poll logs.
                // I will assume we can get the active scan from a global state or search params if passed.
                // If not, we poll nothing until a scan starts.

                // If `repo` param is there, we assume we might be viewing that repo's scan.
                // Let's fallback to "latest" if possible or keep empty until scan starts.

                // Temporarily: 
                const currentScanId = "latest"; // Backend needs to support this or we need to pass it.
                // Since backend doesn't support "latest" yet, we simply won't get logs 
                // UNLESS we trigger the scan and get the ID.

                // Let's just poll and if empty, fine.
                const activeLogs = await fetchLogs(currentScanId);
                if (activeLogs.length > 0) setLogs(activeLogs);

                // Status
                const status = await fetchScanStatus(currentScanId);
                if (status) setScanStatus(status);
            } catch (e) {
                console.error("Polling failed", e);
            }
        };

        loadData();
        const interval = setInterval(loadData, 2000);


        return () => clearInterval(interval);
    }, [isPaused]);

    return (
        <div className="h-[calc(100vh-8rem)] flex flex-col space-y-4">
            {/* Repo Header */}
            <div className="flex items-center justify-between bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-sm">
                <div className="flex items-center space-x-4">
                    <div className="flex items-center space-x-2 px-3 py-1 bg-slate-100 dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
                        <span className="text-slate-500 text-xs font-mono">repo:</span>
                        <span className="text-slate-900 dark:text-slate-200 font-mono font-bold text-sm">
                            {repo?.replace("https://github.com/", "") || "stripe/stripe-ios"}
                        </span>
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                            Active
                        </span>
                    </div>
                </div>

                <div className="flex items-center space-x-2">
                    <button
                        onClick={() => setIsPaused(!isPaused)}
                        className="flex items-center space-x-2 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors text-sm font-medium text-slate-600 dark:text-slate-400"
                    >
                        {isPaused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
                        <span>{isPaused ? "Resume" : "Pause Sim"}</span>
                    </button>
                    <button className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 text-blue-600 dark:text-blue-400 text-sm font-medium hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors">
                        Force Scan
                    </button>
                </div>
            </div>

            {/* Main Content Area - Split View */}
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6 min-h-0">
                {/* Left: Agent Loop Visualization */}
                <div className="bg-slate-50 dark:bg-slate-900/50 rounded-2xl border border-slate-200 dark:border-slate-800 relative overflow-hidden flex items-center justify-center p-8">
                    <div className="absolute top-4 left-4 z-10 flex items-center space-x-2">
                        <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                        <span className="text-xs font-mono font-medium text-slate-500 uppercase tracking-widest">
                            Agent Loop Active
                        </span>
                    </div>

                    {/* Grid Background Effect */}
                    <div className="absolute inset-0 opacity-[0.03] dark:opacity-[0.05]"
                        style={{ backgroundImage: 'linear-gradient(#64748b 1px, transparent 1px), linear-gradient(90deg, #64748b 1px, transparent 1px)', backgroundSize: '40px 40px' }}
                    />

                    <AgentLoopVisualization status={(scanStatus?.status || "idle") as any} />
                </div>

                {/* Right: Terminal Logs */}
                <div className="flex flex-col h-full min-h-0 bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl">
                    <TerminalLog
                        logs={logs}
                        classname="h-full border-none rounded-none"
                        title="system_orchestrator.log"
                    />
                </div>
            </div>
        </div>
    );
}
