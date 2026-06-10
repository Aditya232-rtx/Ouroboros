"use client";

import { useRef, useEffect } from "react";
import { cn } from "../lib/utils";

export interface LogEntry {
    id: string;
    timestamp: string;
    level: "info" | "warning" | "error" | "success" | "debug";
    source: string;
    message: string;
}

interface TerminalLogProps {
    logs: LogEntry[];
    classname?: string;
    title?: string;
}

export default function TerminalLog({ logs, classname, title = "System Log" }: TerminalLogProps) {
    const scrollRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    const getLevelColor = (level: string) => {
        switch (level) {
            case "error": return "text-red-400";
            case "warning": return "text-amber-400";
            case "success": return "text-emerald-400";
            case "debug": return "text-blue-400";
            default: return "text-slate-300";
        }
    };

    return (
        <div className={cn("flex flex-col rounded-xl border border-slate-800 bg-slate-950 shadow-2xl overflow-hidden", classname)}>
            <div className="flex items-center justify-between border-b border-slate-800 px-4 py-2 bg-slate-900/50">
                <div className="flex items-center space-x-2">
                    <div className="flex space-x-1.5">
                        <div className="h-2.5 w-2.5 rounded-full bg-red-500/50" />
                        <div className="h-2.5 w-2.5 rounded-full bg-amber-500/50" />
                        <div className="h-2.5 w-2.5 rounded-full bg-emerald-500/50" />
                    </div>
                    <span className="ml-2 text-xs font-mono text-slate-400 uppercase tracking-widest">{title}</span>
                </div>
                <div className="text-[10px] bg-emerald-500/10 text-emerald-500 px-2 py-0.5 rounded border border-emerald-500/20 font-mono animate-pulse">
                    LIVE
                </div>
            </div>

            <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto p-4 font-mono text-xs sm:text-sm space-y-1 max-h-[400px]"
            >
                {logs.length === 0 ? (
                    <div className="text-slate-600 italic">Waiting for log stream...</div>
                ) : (
                    logs.map((log) => (
                        <div key={log.id} className="flex space-x-2 group hover:bg-white/5 p-0.5 rounded px-2 -mx-2 transition-colors">
                            <span className="text-slate-500 shrink-0 w-[85px]">{log.timestamp}</span>
                            <span className={cn("font-bold shrink-0 w-[70px]", getLevelColor(log.level))}>
                                [{log.level.toUpperCase()}]
                            </span>
                            <span className="text-slate-400 shrink-0 w-[80px] border-r border-slate-800 mr-2">
                                {log.source}:
                            </span>
                            <span className="text-slate-300 break-all">{log.message}</span>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
