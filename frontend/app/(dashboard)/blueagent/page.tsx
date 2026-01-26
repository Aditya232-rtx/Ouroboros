"use client";

import { useEffect, useState } from "react";
import StatsCard from "../../components/StatsCard";
import PatchPreview from "../../components/PatchPreview";
import TerminalLog from "../../components/TerminalLog";
import AgentLoopVisualization from "../../components/AgentLoopVisualization";
import { Zap, Code2, CheckCircle, Clock } from "lucide-react";
import { LogEntry } from "../../lib/types";

export default function BlueAgentPage() {
    const dummyDiff = `--- src/components/Dashboard.vue
+++ src/components/Dashboard.vue
@@ -43,4 +43,4 @@
  <div class="user-content">
-   <span v-html="userComment"></span>
+   <span v-text="userComment"></span>
    <span class="comment-body">`;

    // Mock Logs for Blue Agent
    const initialLogs: LogEntry[] = [
        {
            id: "1",
            timestamp: "10:42:15",
            level: "info",
            source: "blue_agent",
            message: "Received context from Red Agent (Issue #402: Stored XSS)."
        },
        {
            id: "2",
            timestamp: "10:42:16",
            level: "info",
            source: "blue_agent",
            message: "Analyzing dependency graph for `src/components/Dashboard.vue`..."
        },
        {
            id: "3",
            timestamp: "10:42:16",
            level: "info",
            source: "blue_agent",
            message: "Locating vulnerability source... Line 45 detected."
        }
    ];

    const [logs, setLogs] = useState<LogEntry[]>(initialLogs);

    useEffect(() => {
        const interval = setInterval(() => {
            const phases = [
                "Querying LLM (Model: Code-Secure-v4)...",
                "Strategy 1: Sanitize input (DOMPurify).",
                "Strategy 2: Use Vue `v-text` directive (Recommended).",
                "Generating Patch Candidate v1...",
                "Running static analysis on patch...",
                "Syntax Check: PASS",
                "Regression Test (Unit): PASS"
            ];
            const newLog: LogEntry = {
                id: Date.now().toString(),
                timestamp: new Date().toLocaleTimeString(),
                level: "info",
                source: "blue_agent",
                message: phases[Math.floor(Math.random() * phases.length)]
            };
            setLogs(prev => [...prev, newLog].slice(-50));
        }, 4000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="h-[calc(100vh-8rem)] flex flex-col space-y-4">
            {/* Header */}
            <div className="flex flex-col space-y-1 pb-2">
                <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center">
                    <span className="w-3 h-3 rounded-full bg-blue-500 mr-3 animate-pulse"></span>
                    War Room
                </h1>
                <p className="text-slate-500 text-sm ml-6">
                    Monitoring autonomous remediation agents on <span className="bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded font-mono text-xs">github.com/acme/api-gateway</span>
                </p>
            </div>

            {/* Main Content: Split Grid */}
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-0">
                {/* Left: Visualization (1 Col) */}
                <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 flex flex-col items-center justify-center relative overflow-hidden shadow-sm">
                    <h3 className="absolute top-4 left-4 text-xs font-bold text-slate-400 uppercase tracking-widest">Agent Loop</h3>
                    <div className="absolute top-4 right-4 text-[10px] bg-blue-500/10 text-blue-500 px-2 py-1 rounded-full border border-blue-500/20 font-mono">
                        Cycle #4092
                    </div>
                    {/* Simplified Agent Viz with Blue Highlight */}
                    <div className="w-full h-full flex items-center justify-center scale-90">
                        <AgentLoopVisualization status="patching" />
                    </div>

                    <div className="absolute bottom-6 bg-blue-50 dark:bg-slate-800/50 px-4 py-2 rounded-full border border-blue-100 dark:border-slate-700 flex items-center space-x-2">
                        <div className="w-4 h-4 rounded-full border-2 border-blue-500 border-t-transparent animate-spin"></div>
                        <span className="text-xs font-mono text-blue-600 dark:text-blue-400 font-medium">Validating Patch Safety...</span>
                    </div>
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
                            <span className="text-slate-500 text-xs font-mono">src/components/Dashboard.vue</span>
                        </div>
                        <div className="flex-1 overflow-auto bg-[#0d1117]">
                            <PatchPreview
                                file="src/components/Dashboard.vue"
                                diff={dummyDiff}
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
                    value="142"
                    icon={Zap}
                    color="blue"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
                <StatsCard
                    name="Validation Passes"
                    value="98.5%"
                    icon={CheckCircle}
                    color="emerald"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
                <StatsCard
                    name="Lines Fixed"
                    value="1,204"
                    icon={Code2}
                    color="purple"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
                <StatsCard
                    name="Pending Approval"
                    value="3"
                    icon={Clock}
                    color="amber"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
            </div>
        </div>
    );
}
