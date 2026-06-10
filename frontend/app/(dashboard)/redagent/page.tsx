"use client";

import { useEffect, useState } from "react";
import AgentLoopVisualization from "../../components/AgentLoopVisualization";
import TerminalLog from "../../components/TerminalLog";
import StatsCard from "../../components/StatsCard";
import { fetchVulnerabilities } from "../../lib/api";
import { Vulnerability, LogEntry } from "../../lib/types";
import { ShieldAlert, Wrench, GitPullRequest, Timer, Target } from "lucide-react";

export default function RedAgentPage() {
    const [vulnerabilities, setVulnerabilities] = useState<Vulnerability[]>([]);

    // Mock Logs for Red Agent
    const initialLogs: LogEntry[] = [
        {
            id: "1",
            timestamp: "10:42:01",
            level: "info",
            source: "system",
            message: "Initializing Red Team Protocol v1.4.2..."
        },
        {
            id: "2",
            timestamp: "10:42:02",
            level: "info",
            source: "system",
            message: "Target: github.com/stripe/stripe-ios"
        },
        {
            id: "3",
            timestamp: "10:42:05",
            level: "warning",
            source: "red_agent",
            message: "WARN: Potentially exposed .env file detected in commit history (SHA: 7a8b9c)."
        },
        {
            id: "4",
            timestamp: "10:42:08",
            level: "info",
            source: "red_agent",
            message: "Scanning for SQL Injection vulnerabilities in /auth/login endpoint..."
        },
        {
            id: "5",
            timestamp: "10:42:09",
            level: "debug",
            source: "red_agent",
            message: "> Payload: ' OR 1=1 --"
        }
    ];

    const [logs, setLogs] = useState<LogEntry[]>(initialLogs);

    useEffect(() => {
        fetchVulnerabilities("latest").then(setVulnerabilities);

        const interval = setInterval(() => {
            const newLog: LogEntry = {
                id: Date.now().toString(),
                timestamp: new Date().toLocaleTimeString(),
                level: Math.random() > 0.8 ? "error" : "info",
                source: "red_agent",
                message: Math.random() > 0.8 ? "CRITICAL: Stored XSS vulnerability found in POST /api/comments" : "Scanning for SQL Injection vulnerabilities in /auth/login endpoint..."
            };
            setLogs(prev => [...prev, newLog].slice(-50));
        }, 3000);
        return () => clearInterval(interval);
    }, []);

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
                        Monitoring autonomous security agents on <span className="bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded font-mono text-xs">github.com/acme/api-gateway</span>
                    </p>
                </div>
                <div className="flex items-center space-x-3">
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
                    value="12"
                    icon={ShieldAlert}
                    color="red"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
                <StatsCard
                    name="Auto-Fixed"
                    value="8"
                    icon={Wrench}
                    color="emerald"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
                <StatsCard
                    name="Pull Requests"
                    value="3"
                    icon={GitPullRequest}
                    color="blue"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
                <StatsCard
                    name="Uptime"
                    value="42h 12m"
                    icon={Timer}
                    color="purple"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
            </div>
        </div>
    );
}
