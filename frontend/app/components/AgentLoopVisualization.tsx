"use client";

import { motion } from "framer-motion";
import { ShieldAlert, ShieldCheck, FileText, Activity } from "lucide-react";
import { cn } from "../lib/utils";

interface AgentLoopProps {
    status: "idle" | "scanning" | "patching" | "verifying" | "reporting" | "completed" | "failed" | "running" | "pending";
    currentPhase?: string; // Backend phase: initializing, scan_complete, documentation_initial, governance_complete, fixes_generated, verification_complete, pr_created, documentation_final, complete, completed
}

/**
 * Maps the backend current_phase to which agent is currently active.
 * Returns: "red" | "blue" | "governance" | "core" | null
 */
function getActiveAgent(status: string, currentPhase?: string): "red" | "blue" | "governance" | "core" | null {
    // First check current_phase (more granular)
    if (currentPhase) {
        const phase = currentPhase.toLowerCase();
        if (phase === "initializing" || phase === "scan_complete" || phase === "scanning" || phase === "verification_complete") return "red";
        if (phase === "documentation_initial" || phase === "documentation_final" || phase === "reporting") return "core";
        if (phase === "governance_complete" || phase === "governance") return "governance";
        if (phase === "fixes_generated" || phase === "patching" || phase === "generating_fixes") return "blue";
        if (phase === "pr_created") return "core";
        if (phase === "complete" || phase === "completed") return null;
    }
    // Fallback to status
    if (status === "scanning" || status === "running") return "red";
    if (status === "patching" || status === "generating_fixes") return "blue";
    if (status === "verifying") return "red";
    if (status === "reporting") return "core";
    return null;
}

const glowPulse = {
    scale: [1, 1.08, 1],
    transition: { repeat: Infinity, duration: 1.8, ease: "easeInOut" },
};

const idleState = {};

export default function AgentLoopVisualization({ status, currentPhase }: AgentLoopProps) {
    const activeAgent = getActiveAgent(status, currentPhase);

    const isRedActive = activeAgent === "red";
    const isBlueActive = activeAgent === "blue";
    const isGovActive = activeAgent === "governance";
    const isCoreActive = activeAgent === "core";
    const isCompleted = status === "completed" || currentPhase === "complete" || currentPhase === "completed";

    return (
        <div className="relative flex items-center justify-center w-full h-[500px]">
            {/* Spinning Orbit Rings */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                {/* Outer Ring */}
                <div className="w-[400px] h-[400px] rounded-full border border-slate-200 dark:border-slate-800 border-dashed animate-spin-slow opacity-30"></div>
                {/* Inner Ring - Reverse Spin */}
                <div className="absolute w-[300px] h-[300px] rounded-full border border-emerald-500/20 border-dashed animate-spin-reverse"></div>
            </div>

            {/* Central Core (Orchestrator) */}
            <motion.div
                className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-20"
                animate={isCoreActive ? glowPulse : idleState}
            >
                <div className={cn(
                    "w-24 h-24 rounded-full bg-white dark:bg-slate-900 border-4 shadow-2xl flex items-center justify-center relative transition-all duration-500",
                    isCoreActive
                        ? "border-emerald-500 shadow-emerald-500/50"
                        : isCompleted
                            ? "border-emerald-400 shadow-emerald-400/30"
                            : "border-slate-100 dark:border-slate-800"
                )}>
                    {isCoreActive && (
                        <div className="absolute inset-0 rounded-full border-2 border-emerald-400/60 animate-ping" />
                    )}
                    <Activity className={cn("w-10 h-10 transition-colors duration-500",
                        isCoreActive ? "text-emerald-500" : isCompleted ? "text-emerald-400" : "text-slate-400"
                    )} />
                    <div className="absolute -bottom-8 text-xs font-mono text-slate-400 font-bold tracking-widest">CORE</div>
                </div>
            </motion.div>

            {/* RED AGENT - Top */}
            <motion.div
                className="absolute top-[50px] left-1/2 transform -translate-x-1/2 z-20 flex flex-col items-center"
                animate={isRedActive ? glowPulse : idleState}
            >
                <div className={cn(
                    "w-16 h-16 rounded-full flex items-center justify-center border-4 shadow-xl bg-white dark:bg-slate-900 transition-all duration-500 relative",
                    isRedActive ? "border-red-500 shadow-red-500/50" : "border-slate-200 dark:border-slate-800"
                )}>
                    {isRedActive && (
                        <div className="absolute inset-0 rounded-full border-2 border-red-400/60 animate-ping" />
                    )}
                    <ShieldAlert className={cn("w-8 h-8 transition-colors duration-500", isRedActive ? "text-red-500" : "text-slate-400")} />
                </div>
                <div className="mt-2 text-center bg-white/80 dark:bg-slate-950/80 backdrop-blur px-2 py-1 rounded">
                    <h3 className={cn("font-bold text-xs transition-colors duration-500", isRedActive ? "text-red-500" : "text-slate-500")}>RED AGENT</h3>
                    {isRedActive && <span className="text-[10px] text-red-500 animate-pulse font-medium">ATTACKING</span>}
                </div>
            </motion.div>

            {/* BLUE AGENT - Bottom Right */}
            <motion.div
                className="absolute bottom-[100px] right-[15%] z-20 flex flex-col items-center"
                animate={isBlueActive ? glowPulse : idleState}
            >
                <div className={cn(
                    "w-16 h-16 rounded-full flex items-center justify-center border-4 shadow-xl bg-white dark:bg-slate-900 transition-all duration-500 relative",
                    isBlueActive ? "border-blue-500 shadow-blue-500/50" : "border-slate-200 dark:border-slate-800"
                )}>
                    {isBlueActive && (
                        <div className="absolute inset-0 rounded-full border-2 border-blue-400/60 animate-ping" />
                    )}
                    <ShieldCheck className={cn("w-8 h-8 transition-colors duration-500", isBlueActive ? "text-blue-500" : "text-slate-400")} />
                </div>
                <div className="mt-2 text-center bg-white/80 dark:bg-slate-950/80 backdrop-blur px-2 py-1 rounded">
                    <h3 className={cn("font-bold text-xs transition-colors duration-500", isBlueActive ? "text-blue-500" : "text-slate-500")}>BLUE AGENT</h3>
                    {isBlueActive && <span className="text-[10px] text-blue-500 animate-pulse font-medium">DEFENDING</span>}
                </div>
            </motion.div>

            {/* GOVERNANCE - Bottom Left */}
            <motion.div
                className="absolute bottom-[100px] left-[15%] z-20 flex flex-col items-center"
                animate={isGovActive ? glowPulse : idleState}
            >
                <div className={cn(
                    "w-16 h-16 rounded-full flex items-center justify-center border-4 shadow-xl bg-white dark:bg-slate-900 transition-all duration-500 relative",
                    isGovActive ? "border-purple-500 shadow-purple-500/50" : "border-slate-200 dark:border-slate-800"
                )}>
                    {isGovActive && (
                        <div className="absolute inset-0 rounded-full border-2 border-purple-400/60 animate-ping" />
                    )}
                    <FileText className={cn("w-8 h-8 transition-colors duration-500", isGovActive ? "text-purple-500" : "text-slate-400")} />
                </div>
                <div className="mt-2 text-center bg-white/80 dark:bg-slate-950/80 backdrop-blur px-2 py-1 rounded">
                    <h3 className={cn("font-bold text-xs transition-colors duration-500", isGovActive ? "text-purple-500" : "text-slate-500")}>GOVERNANCE</h3>
                    {isGovActive && <span className="text-[10px] text-purple-500 animate-pulse font-medium">AUDITING</span>}
                </div>
            </motion.div>

            {/* Completion Badge */}
            {isCompleted && (
                <motion.div
                    className="absolute top-4 left-1/2 transform -translate-x-1/2 z-30"
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                >
                    <div className="flex items-center space-x-2 bg-emerald-50 dark:bg-emerald-900/30 px-3 py-1.5 rounded-full border border-emerald-200 dark:border-emerald-800">
                        <div className="w-2 h-2 rounded-full bg-emerald-500" />
                        <span className="text-xs font-mono font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">COMPLETED</span>
                    </div>
                </motion.div>
            )}

            {/* Connection Beams (Animated) */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 1 }}>
                <defs>
                    <linearGradient id="beam-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="rgba(16, 185, 129, 0)" />
                        <stop offset="50%" stopColor="rgba(16, 185, 129, 0.5)" />
                        <stop offset="100%" stopColor="rgba(16, 185, 129, 0)" />
                    </linearGradient>
                </defs>
            </svg>
        </div>
    );
}
