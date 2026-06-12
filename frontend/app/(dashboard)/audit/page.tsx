"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import StatsCard from "../../components/StatsCard";
import TerminalLog from "../../components/TerminalLog";
import { FileText, Download, CheckCircle, Clock, ShieldCheck, FileJson, Lock, Zap } from "lucide-react";
import { Button } from "../../components/lightswind/button";
import { Badge } from "../../components/lightswind/badge";
import { LogEntry } from "../../lib/types";
import { downloadReportPdf, fetchLogs, fetchScanStatus, fetchVulnerabilities } from "../../lib/api";

function AuditContent() {
    const searchParams = useSearchParams();
    const scanId = searchParams.get("scan_id") || "latest";
    
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [scanStatus, setScanStatus] = useState<{ repo_url?: string } | null>(null);
    const [isDownloading, setIsDownloading] = useState(false);
    const [stats, setStats] = useState({
        totalVulns: 0,
        fixedVulns: 0,
        codeCoverage: "0%",
        auditStatus: "Pending"
    });

    const handleDownloadPdf = async () => {
        setIsDownloading(true);
        try {
            await downloadReportPdf(scanId);
        } catch (error) {
            console.error("Download failed:", error);
            alert("Failed to download report. Please try again.");
        } finally {
            setIsDownloading(false);
        }
    };

    // Dynamic artifacts based on scan
    const [artifacts, setArtifacts] = useState([
        { name: "audit_report.pdf", size: "Loading...", time: "now", type: "pdf" },
        { name: "vulnerability_scan.json", size: "Loading...", time: "now", type: "code" },
        { name: "signature_log.txt", size: "Loading...", time: "now", type: "lock" },
    ]);

    useEffect(() => {
        const loadData = async () => {
            try {
                // Fetch logs
                const logData = await fetchLogs(scanId);
                if (logData.length > 0) {
                    // Filter for audit-related logs
                    const auditLogs = logData.filter(l => 
                        l.source === "governance" || 
                        l.source === "system" ||
                        l.message.toLowerCase().includes("audit") ||
                        l.message.toLowerCase().includes("hash") ||
                        l.message.toLowerCase().includes("signature")
                    );
                    setLogs(auditLogs.length > 0 ? auditLogs : logData.slice(-20));
                }
                
                // Fetch scan status and vulnerabilities for stats
                const status = await fetchScanStatus(scanId);
                setScanStatus(status);
                const vulns = await fetchVulnerabilities(scanId);
                
                const fixedCount = vulns.filter(v => v.status === "remediated").length;
                
                setStats({
                    totalVulns: vulns.length,
                    fixedVulns: fixedCount,
                    codeCoverage: vulns.length > 0 ? `${Math.round((fixedCount / vulns.length) * 100)}%` : "N/A",
                    auditStatus: status?.status === "completed" ? "Passing" : "In Progress"
                });
                
                // Update artifacts with dynamic data
                setArtifacts([
                    { name: `audit_${scanId}.pdf`, size: "2.4 MB", time: "Ready", type: "pdf" },
                    { name: `vulns_${scanId}.json`, size: `${vulns.length * 2} KB`, time: "Ready", type: "code" },
                    { name: `sig_${scanId}.txt`, size: "2 KB", time: "Ready", type: "lock" },
                ]);
                
            } catch (error) {
                console.error("Failed to load audit data:", error);
            }
        };

        loadData();
        const interval = setInterval(loadData, 5000);
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
                        Repository: <span className="text-emerald-600 dark:text-emerald-500 cursor-pointer hover:underline">{scanStatus?.repo_url?.replace("https://github.com/", "") || "Loading..."}</span>
                    </p>
                </div>
                <div className="flex items-center space-x-3">
                    <Button variant="outline" className="bg-white dark:bg-slate-800 font-mono text-xs">
                        Copy Hash
                    </Button>
                    <Button 
                        className="bg-emerald-500 hover:bg-emerald-600 text-white shadow-md shadow-emerald-500/20"
                        onClick={handleDownloadPdf}
                        disabled={isDownloading}
                    >
                        <Download className="w-4 h-4 mr-2" />
                        {isDownloading ? "Downloading..." : "Download PDF"}
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
                                    <span>Report ready for download</span>
                                    <span className="text-emerald-500 font-medium">Complete</span>
                                </div>
                                <div className="w-full h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden mt-1">
                                    <div className="h-full bg-emerald-500 w-full rounded-full"></div>
                                </div>
                            </div>

                            <Button
                                variant="outline"
                                className="w-full mt-2 border-dashed text-slate-500 hover:text-emerald-600 hover:border-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-900/10 transition-colors"
                                onClick={handleDownloadPdf}
                                disabled={isDownloading}
                            >
                                <Download className="w-4 h-4 mr-2" />
                                {isDownloading ? "Generating PDF..." : "Download Full Report"}
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
                    value={stats.totalVulns.toString()}
                    icon={ShieldCheck}
                    color="emerald"
                    change={`(-${stats.fixedVulns} Fixed)`}
                    changeType="positive"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
                <StatsCard
                    name="Fix Coverage"
                    value={stats.codeCoverage}
                    icon={FileText}
                    color="blue"
                    changeType="positive"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
                <StatsCard
                    name="Fixed"
                    value={stats.fixedVulns.toString()}
                    icon={Zap}
                    color="purple"
                    description="Vulnerabilities"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
                <StatsCard
                    name="Audit Status"
                    value={stats.auditStatus}
                    icon={CheckCircle}
                    color="emerald"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
            </div>
        </div>
    );
}

export default function AuditPage() {
    return (
        <Suspense fallback={<div className="p-8 text-center">Loading...</div>}>
            <AuditContent />
        </Suspense>
    );
}