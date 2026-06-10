"use client";

import { useEffect, useState } from "react";
import StatsCard from "../../components/StatsCard";
import TerminalLog from "../../components/TerminalLog";
import { FileText, Download, CheckCircle, Clock, ShieldCheck, FileJson, Lock, Zap } from "lucide-react";
import { Button } from "../../components/lightswind/button";
import { Badge } from "../../components/lightswind/badge";
import { LogEntry } from "../../lib/types";
import { exportReport } from "../../lib/api";

export default function AuditPage() {
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [isExporting, setIsExporting] = useState(false);

    const handleExport = async (reportId: string) => {
        setIsExporting(true);
        try {
            // Hardcoded ID for demo, real implementations uses selected report
            const result = await exportReport("demo-report-123");
            alert(`Report exported to Drive! File ID: ${result.file_id}`);
        } catch (error) {
            console.error("Export failed:", error);
            alert("Failed to export report.");
        } finally {
            setIsExporting(false);
        }
    };

    // Mock Data mimicking the screenshot
    const artifacts = [
        { name: "audit_v1.0.4.pdf", size: "2.4 MB", time: "2m ago", type: "pdf" },
        { name: "diff_patch_04.json", size: "14 KB", time: "5m ago", type: "code" },
        { name: "sig_registry.txt", size: "2 KB", time: "10m ago", type: "lock" },
    ];

    useEffect(() => {
        // Mock Logs for Audit Terminal
        const initialLogs: LogEntry[] = [
            {
                id: "1",
                timestamp: "10:42:01",
                level: "info",
                source: "system",
                message: "Initiating vulnerability scan on /contracts/core/Vault.sol..."
            },
            {
                id: "2",
                timestamp: "10:42:05",
                level: "warning",
                source: "system",
                message: "WARN: Reentrancy vulnerability detected in withdraw() function."
            },
            {
                id: "3",
                timestamp: "10:42:06",
                level: "debug",
                source: "system",
                message: "AUTO-FIX: Applying Mutex lock pattern (ReentrancyGuard)."
            },
            {
                id: "4",
                timestamp: "10:42:08",
                level: "success",
                source: "system",
                message: "Fix verified via Unit Test Suite A. Gas optimization: -420 wei."
            },
            {
                id: "5",
                timestamp: "10:42:12",
                level: "info",
                source: "system",
                message: "HASH: Commit: 8f9d3a2b1c4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s"
            },
            {
                id: "6",
                timestamp: "10:42:15",
                level: "info",
                source: "system",
                message: "SIGNATURE: 0x7a2...3f1 [Verified by Ouroboros_Bot]"
            }
        ];
        setLogs(initialLogs);

        const interval = setInterval(() => {
            const messages = [
                "DOCS: Generating updated documentation for automated changes...",
                "UPDATE: Updated Vault.sol documentation with new security considerations.",
                "Archiving scan results to Cold Storage...",
                "Hashing patch diffs for non-repudiation...",
            ];
            const newLog: LogEntry = {
                id: Date.now().toString(),
                timestamp: new Date().toLocaleTimeString(),
                level: "info",
                source: "system",
                message: messages[Math.floor(Math.random() * messages.length)]
            };
            setLogs(prev => [...prev, newLog].slice(-50));
        }, 5000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="h-[calc(100vh-8rem)] flex flex-col space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between pb-2">
                <div className="flex flex-col space-y-1">
                    <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center">
                        <ShieldCheck className="w-6 h-6 text-emerald-500 mr-3" />
                        War Room
                        <span className="ml-3 px-2 py-0.5 rounded textxs bg-slate-100 dark:bg-slate-800 text-slate-500 font-mono text-xs border border-slate-200 dark:border-slate-700">v1.0.4-beta</span>
                    </h1>
                    <p className="text-slate-500 text-sm ml-9">
                        Repository: <span className="text-emerald-600 dark:text-emerald-500 cursor-pointer hover:underline">org/defi-protocol-v2</span>
                    </p>
                </div>
                <div className="flex items-center space-x-3">
                    <Button variant="outline" className="bg-white dark:bg-slate-800 font-mono text-xs">
                        Copy Hash
                    </Button>
                    <Button className="bg-emerald-500 hover:bg-emerald-600 text-white shadow-md shadow-emerald-500/20">
                        <Download className="w-4 h-4 mr-2" />
                        Export PDF
                    </Button>
                </div>
            </div>

            {/* Main Content: Split Grid */}
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6 min-h-0">
                {/* Left: Terminal Log (Dark) */}
                <div className="flex flex-col h-full min-h-0 bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl relative">
                    <div className="absolute top-3 right-4 flex space-x-2">
                        <div className="w-2 h-2 rounded-full bg-amber-500"></div>
                        <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                    </div>
                    <div className="bg-slate-900/50 p-2 px-4 border-b border-slate-800 text-slate-500 font-mono text-xs flex items-center">
                        <span className="mr-2">_&gt;</span> audit_log_stream.sh
                    </div>
                    <TerminalLog
                        logs={logs}
                        classname="h-full border-none rounded-none pt-0" // remove extra padding if needed
                        title="" // Custom title bar above
                    />
                </div>

                {/* Right: Reports & Artifacts */}
                <div className="flex flex-col space-y-6 overflow-y-auto">
                    {/* Final Report Gen Card */}
                    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
                        <h3 className="font-bold text-slate-900 dark:text-white flex items-center mb-4">
                            <FileText className="w-4 h-4 mr-2 text-blue-500" />
                            Final Report Gen
                        </h3>
                        <div className="space-y-4">
                            <div className="flex justify-between text-xs font-medium text-slate-500">
                                <span>Generating PDF Summary...</span>
                                <span className="text-slate-900 dark:text-white">84%</span>
                            </div>
                            <div className="w-full h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                                <div className="h-full bg-emerald-500 w-[84%] rounded-full"></div>
                            </div>

                            <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
                                <div className="flex justify-between text-xs text-slate-500 mt-2">
                                    <span>Syncing to Google Docs...</span>
                                    <span className="text-amber-500 font-medium">Pending</span>
                                </div>
                                <div className="w-full h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden mt-1">
                                    <div className="h-full bg-slate-300 dark:bg-slate-600 w-[20%] rounded-full animate-pulse"></div>
                                </div>
                            </div>

                            <Button
                                variant="outline"
                                className="w-full mt-2 border-dashed text-slate-500 hover:text-blue-600 hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-colors"
                                onClick={() => handleExport("latest-report-id")}
                                disabled={isExporting}
                            >
                                {isExporting ? "Uploading to Drive..." : "Export to Google Drive"}
                            </Button>
                        </div>
                    </div>

                    {/* Signed Artifacts List */}
                    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm flex-1">
                        <h3 className="font-bold text-slate-900 dark:text-white flex items-center mb-4">
                            <ShieldCheck className="w-4 h-4 mr-2 text-purple-500" />
                            Signed Artifacts
                        </h3>
                        <div className="space-y-4">
                            {artifacts.map((file, i) => (
                                <div key={i} className="flex items-center justify-between group cursor-pointer">
                                    <div className="flex items-center space-x-3">
                                        <div className={`p-2 rounded-lg ${file.type === 'pdf' ? 'bg-red-50 text-red-500' :
                                            file.type === 'code' ? 'bg-blue-50 text-blue-500' :
                                                'bg-emerald-50 text-emerald-500'
                                            }`}>
                                            {file.type === 'pdf' ? <FileText className="w-5 h-5" /> :
                                                file.type === 'code' ? <FileJson className="w-5 h-5" /> :
                                                    <Lock className="w-5 h-5" />}
                                        </div>
                                        <div>
                                            <div className="text-sm font-medium text-slate-700 dark:text-slate-200 group-hover:text-blue-600 transition-colors">
                                                {file.name}
                                            </div>
                                            <div className="text-xs text-slate-400">
                                                {file.size} • {file.time}
                                            </div>
                                        </div>
                                    </div>
                                    <Button variant="ghost" size="icon" className="text-slate-400 hover:text-slate-600">
                                        <Download className="w-4 h-4" />
                                    </Button>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {/* Bottom: Stats Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatsCard
                    name="Total Vulnerabilities"
                    value="0"
                    icon={ShieldCheck}
                    color="emerald"
                    change="(-12 Fixed)"
                    changeType="positive" // Green
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
                <StatsCard
                    name="Code Coverage"
                    value="98.4%"
                    icon={FileText}
                    color="blue"
                    change="+2.1%"
                    changeType="positive"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
                <StatsCard
                    name="Gas Saved"
                    value="45k"
                    icon={Zap}
                    color="purple"
                    description="Wei"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
                <StatsCard
                    name="Audit Status"
                    value="Passing"
                    icon={CheckCircle}
                    color="emerald"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
            </div>
        </div>
    );
}
