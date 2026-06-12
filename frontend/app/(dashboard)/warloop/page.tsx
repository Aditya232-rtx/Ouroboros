"use client";

import { Suspense, useEffect, useState, useRef } from "react";
import { useSearchParams } from "next/navigation";
import AgentLoopVisualization from "../../components/AgentLoopVisualization";
import TerminalLog from "../../components/TerminalLog";
import { fetchScanStatus, startScan } from "../../lib/api";
import { ScanStatus } from "../../lib/types";
import { Pause, Play } from "lucide-react";
import { useScanLogs } from "../../hooks/useScanLogs";

function WarRoomContent() {
    const searchParams = useSearchParams();
    const repo = searchParams.get("repo");

    // Use custom hook for logs
    const [scanId, setScanId] = useState<string | null>(null);
    const [isPaused, setIsPaused] = useState(false);
    const { logs } = useScanLogs(scanId, isPaused);

    const [scanStatus, setScanStatus] = useState<ScanStatus | null>(null);
    const [isStartingScan, setIsStartingScan] = useState(false);
    const hasStartedRef = useRef(false);

    // Sync scanId with URL or recover latest
    useEffect(() => {
        const urlScanId = searchParams.get("scanId");
        if (urlScanId && !scanId) {
            console.log("Resuming existing scan from URL:", urlScanId);
            setScanId(urlScanId);
            fetchScanStatus(urlScanId).then(status => {
                if (status) setScanStatus(status);
            }).catch(console.error);
        } else if (!urlScanId && !scanId && !repo) {
            // If no params, try to recover "latest" scan logic
            console.log("No params, checking for latest scan...");
            fetchScanStatus("latest").then(status => {
                if (status && status.id) {
                    console.log("Recovered latest scan:", status.id);
                    setScanId(status.id);
                    setScanStatus(status);

                    // Update URL to persist this recovered ID
                    const newUrl = new URL(window.location.href);
                    newUrl.searchParams.set("scanId", status.id);
                    if (status.repo_url) newUrl.searchParams.set("repo", status.repo_url);
                    window.history.replaceState({}, "", newUrl.toString());
                }
            }).catch(() => {
                console.log("No latest scan found.");
            });
        }
    }, [searchParams, scanId, repo]);

    // Auto-start scan ONLY if no scanId exists AND repo is provided
    useEffect(() => {
        const startScanForRepo = async () => {
            // CRITICAL FIX: Don't start if we have a scanId (from state or URL)
            const urlScanId = searchParams.get("scanId");
            if (!repo || scanId || urlScanId || isStartingScan || hasStartedRef.current) return;

            hasStartedRef.current = true;
            setIsStartingScan(true);
            try {
                console.log("Starting NEW scan for repo:", repo);
                const response = await startScan({ repo_url: repo });

                console.log("Scan started with ID:", response.scan_id);
                setScanId(response.scan_id);

                // Update URL without reloading
                const newUrl = new URL(window.location.href);
                newUrl.searchParams.set("scanId", response.scan_id);
                window.history.replaceState({}, "", newUrl.toString());

                // Also set initial status
                setScanStatus({
                    id: response.scan_id,
                    status: "scanning",
                    progress: 0,
                    current_phase: "initializing",
                    repo_url: repo,
                    started_at: new Date().toISOString()
                });
            } catch (error) {
                console.error("Failed to start scan:", error);
                alert("Failed to start scan. Please check if the repository URL is valid and try again.");
            } finally {
                setIsStartingScan(false);
            }
        };

        startScanForRepo();
    }, [repo, scanId, isStartingScan, searchParams]);

    // Poll for scan status (Logs handled by useScanLogs)
    useEffect(() => {
        if (!scanId || isPaused) return;

        let errorCount = 0;
        const loadStatus = async () => {
            try {
                const status = await fetchScanStatus(scanId);
                // Only update if we got a valid status
                if (status) {
                    setScanStatus(status);
                    errorCount = 0;
                } else {
                    // If null (404/429), increment error count but KEEP existing state
                    errorCount++;
                    console.warn(`Status fetch returned null (Attempt ${errorCount})`);
                }
            } catch (e) {
                console.error("Status polling failed", e);
                errorCount++;
            }
        };

        // Initial load
        loadStatus();
        const interval = setInterval(loadStatus, 5000);

        return () => clearInterval(interval);
    }, [isPaused, scanId]);

    return (
        <div className="h-[calc(100vh-8rem)] flex flex-col space-y-4">
            {/* Repo Header */}
            <div className="flex items-center justify-between bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-sm">
                <div className="flex items-center space-x-4">
                    <div className="flex items-center space-x-2 px-3 py-1 bg-slate-100 dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
                        <span className="text-slate-500 text-xs font-mono">repo:</span>
                        <span className="text-slate-900 dark:text-slate-200 font-mono font-bold text-sm">
                            {repo?.replace("https://github.com/", "") || scanStatus?.repo_url?.replace("https://github.com/", "") || "Loading..."}
                        </span>
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                            {scanStatus?.status || "initializing"}
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
                    {isStartingScan ? (
                        <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 text-emerald-600 dark:text-emerald-400 text-sm font-medium">
                            <div className="w-3 h-3 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
                            <span>Starting scan...</span>
                        </div>
                    ) : scanId ? (
                        <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 text-blue-600 dark:text-blue-400 text-sm font-medium">
                            <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
                            <span>Scan Active</span>
                        </div>
                    ) : null}
                </div>
            </div>

            {/* Main Content Area - Split View */}
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6 min-h-0">
                {/* Left: Agent Loop Visualization */}
                <div className="bg-slate-50 dark:bg-slate-900/50 rounded-2xl border border-slate-200 dark:border-slate-800 relative overflow-hidden flex items-center justify-center p-8">
                    <div className="absolute top-4 left-4 z-10 flex items-center space-x-2">
                        <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                        <span className="text-xs font-mono font-medium text-slate-500 uppercase tracking-widest">
                            {scanStatus?.current_phase || "Agent Loop Active"}
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

export default function WarRoomPage() {
    return (
        <Suspense fallback={<div className="p-8 text-center">Loading...</div>}>
            <WarRoomContent />
        </Suspense>
    );
}