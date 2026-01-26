"use client";

import { motion } from "framer-motion";
import { ShieldAlert, ShieldCheck, FileText, Activity } from "lucide-react";
import { cn } from "../lib/utils";

interface AgentLoopProps {
    status: "idle" | "scanning" | "patching" | "verifying" | "reporting";
}

export default function AgentLoopVisualization({ status }: AgentLoopProps) {
    const isScanning = status === "scanning";
    const isPatching = status === "patching";
    const isVerifying = status === "verifying" || status === "reporting";

    return (
        <div className="relative flex items-center justify-center w-full h-[500px]">
            {/* Spinning Orbit Rings */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                {/* Outer Ring */}
                <div className="w-[400px] h-[400px] rounded-full border border-slate-200 dark:border-slate-800 border-dashed animate-spin-slow opacity-30"></div>
                {/* Inner Ring - Reverse Spin */}
                <div className="absolute w-[300px] h-[300px] rounded-full border border-emerald-500/20 border-dashed animate-spin-reverse-slow"></div>
            </div>

            {/* Central Core (Orchestrator) */}
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-20">
                <div className="w-24 h-24 rounded-full bg-white dark:bg-slate-900 border-4 border-slate-100 dark:border-slate-800 shadow-2xl flex items-center justify-center relative">
                    <Activity className="w-10 h-10 text-slate-400" />
                    <div className="absolute -bottom-8 text-xs font-mono text-slate-400 font-bold tracking-widest">CORE</div>
                </div>
            </div>

            {/* Nodes Positioned on Orbit */}
            {/* RED AGENT - Top */}
            <motion.div
                className="absolute top-[50px] left-1/2 transform -translate-x-1/2 z-20 flex flex-col items-center"
                animate={isScanning ? { scale: [1, 1.1, 1] } : {}}
                transition={{ repeat: Infinity, duration: 2 }}
            >
                <div className={cn(
                    "w-16 h-16 rounded-full flex items-center justify-center border-4 shadow-xl bg-white dark:bg-slate-900 transition-colors duration-300",
                    isScanning ? "border-red-500 shadow-red-500/50" : "border-slate-200 dark:border-slate-800"
                )}>
                    <ShieldAlert className={cn("w-8 h-8", isScanning ? "text-red-500" : "text-slate-400")} />
                </div>
                <div className="mt-2 text-center bg-white/80 dark:bg-slate-950/80 backdrop-blur px-2 py-1 rounded">
                    <h3 className={cn("font-bold text-xs", isScanning ? "text-red-500" : "text-slate-500")}>RED AGENT</h3>
                    {isScanning && <span className="text-[10px] text-red-500 animate-pulse">ATTACKING</span>}
                </div>
            </motion.div>

            {/* BLUE AGENT - Bottom Right */}
            <motion.div
                className="absolute bottom-[100px] right-[15%] z-20 flex flex-col items-center"
                animate={isPatching ? { scale: [1, 1.1, 1] } : {}}
                transition={{ repeat: Infinity, duration: 2 }}
            >
                <div className={cn(
                    "w-16 h-16 rounded-full flex items-center justify-center border-4 shadow-xl bg-white dark:bg-slate-900 transition-colors duration-300",
                    isPatching ? "border-blue-500 shadow-blue-500/50" : "border-slate-200 dark:border-slate-800"
                )}>
                    <ShieldCheck className={cn("w-8 h-8", isPatching ? "text-blue-500" : "text-slate-400")} />
                </div>
                <div className="mt-2 text-center bg-white/80 dark:bg-slate-950/80 backdrop-blur px-2 py-1 rounded">
                    <h3 className={cn("font-bold text-xs", isPatching ? "text-blue-500" : "text-slate-500")}>BLUE AGENT</h3>
                    {isPatching && <span className="text-[10px] text-blue-500 animate-pulse">DEFENDING</span>}
                </div>
            </motion.div>

            {/* GOVERNANCE - Bottom Left */}
            <motion.div
                className="absolute bottom-[100px] left-[15%] z-20 flex flex-col items-center"
                animate={isVerifying ? { scale: [1, 1.1, 1] } : {}}
                transition={{ repeat: Infinity, duration: 2 }}
            >
                <div className={cn(
                    "w-16 h-16 rounded-full flex items-center justify-center border-4 shadow-xl bg-white dark:bg-slate-900 transition-colors duration-300",
                    isVerifying ? "border-purple-500 shadow-purple-500/50" : "border-slate-200 dark:border-slate-800"
                )}>
                    <FileText className={cn("w-8 h-8", isVerifying ? "text-purple-500" : "text-slate-400")} />
                </div>
                <div className="mt-2 text-center bg-white/80 dark:bg-slate-950/80 backdrop-blur px-2 py-1 rounded">
                    <h3 className={cn("font-bold text-xs", isVerifying ? "text-purple-500" : "text-slate-500")}>GOVERNANCE</h3>
                    {isVerifying && <span className="text-[10px] text-purple-500 animate-pulse">AUDITING</span>}
                </div>
            </motion.div>

            {/* Connection Beams (Animated) */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 1 }}>
                <defs>
                    <linearGradient id="beam-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="rgba(16, 185, 129, 0)" />
                        <stop offset="50%" stopColor="rgba(16, 185, 129, 0.5)" />
                        <stop offset="100%" stopColor="rgba(16, 185, 129, 0)" />
                    </linearGradient>
                </defs>
                {/* Add standard SVG paths for connections if needed, but the rings provide enough context */}
            </svg>
        </div>
    );
}
