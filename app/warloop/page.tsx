'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { getWarRoomData, type LogEntry } from './data';
import { LogEntryComponent } from './LogEntry';

export default function WarRoom() {
    const [isDark, setIsDark] = useState(false);
    // Get data (currently returns mock data, will be replaced with API call)
    const data = getWarRoomData();

    useEffect(() => {
        // Detect dark mode from system
        const updateDarkMode = () => {
            const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
            setIsDark(document.documentElement.classList.contains('dark') || prefersDark);
        };
        updateDarkMode();

        // Watch for changes
        const observer = new MutationObserver(updateDarkMode);
        observer.observe(document.documentElement, { attributes: true });
        return () => observer.disconnect();
    }, []);

    return (
        <div className="min-h-screen flex flex-col overflow-hidden bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
            {/* Header */}
            <header className="h-16 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex items-center justify-between px-6 z-50 shrink-0 shadow-sm">
                <div className="flex items-center space-x-6">
                    <div className="flex items-center space-x-3">
                        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-700 flex items-center justify-center shadow-lg shadow-blue-200 dark:shadow-blue-900/50 ring-1 ring-black/5">
                            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                            </svg>
                        </div>
                        <div>
                            <h1 className="text-lg font-bold tracking-tight leading-none">Ouroboros</h1>
                            <span className="text-[10px] text-slate-500 dark:text-slate-400 font-mono tracking-wider uppercase">War Room v2.1</span>
                        </div>
                    </div>
                    <div className="h-8 w-px bg-slate-200 dark:bg-slate-700 mx-2"></div>
                    <div className="flex items-center space-x-3 bg-slate-50 dark:bg-slate-800/50 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700">
                        <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                        </svg>
                        <span className="text-xs font-mono text-slate-600 dark:text-slate-300">repo: <span className="font-bold text-slate-900 dark:text-slate-100">{data.repository.owner}/{data.repository.name}</span></span>
                        <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium ml-2 ${data.repository.status === 'Active'
                            ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800'
                            : 'bg-slate-50 dark:bg-slate-900/20 text-slate-700 dark:text-slate-400 border border-slate-200 dark:border-slate-800'
                            }`}>{data.repository.status}</span>
                    </div>
                </div>
                <div className="flex items-center space-x-3">
                    <button className="flex items-center space-x-2 px-3 py-1.5 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors text-slate-600 dark:text-slate-300 text-xs font-medium shadow-sm">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span>Pause Sim</span>
                    </button>
                    <button className="flex items-center space-x-2 px-3 py-1.5 rounded-md bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors text-blue-700 dark:text-blue-400 text-xs font-medium shadow-sm">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span>Force Scan</span>
                    </button>
                    <div className="h-8 w-px bg-slate-200 dark:bg-slate-700 mx-2"></div>
                    <Link href="/" className="h-8 w-8 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden border border-slate-200 dark:border-slate-700 ring-2 ring-white dark:ring-slate-900 flex items-center justify-center hover:opacity-80 transition-opacity">
                        <svg className="w-5 h-5 text-slate-600 dark:text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                    </Link>
                </div>
            </header>

            {/* Navigation Tabs */}
            <div className="border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-6 shrink-0 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
                <nav className="flex space-x-6">
                    <button className="pb-3 pt-4 px-1 border-b-2 border-blue-600 text-sm font-medium text-blue-700 dark:text-blue-400 flex items-center space-x-2 bg-blue-50/30 dark:bg-blue-900/10">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        <span>Agent Loop</span>
                    </button>
                    <Link href="/redagent" className="pb-3 pt-4 px-1 border-b-2 border-transparent hover:border-slate-300 dark:hover:border-slate-600 text-sm font-medium text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 transition-all flex items-center space-x-2">
                        <span className="w-2 h-2 rounded-full bg-red-600"></span>
                        <span>Red Team</span>
                    </Link>
                    <button className="pb-3 pt-4 px-1 border-b-2 border-transparent hover:border-slate-300 dark:hover:border-slate-600 text-sm font-medium text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 transition-all flex items-center space-x-2">
                        <span className="w-2 h-2 rounded-full bg-blue-600"></span>
                        <span>Blue Team</span>
                    </button>
                    <button className="pb-3 pt-4 px-1 border-b-2 border-transparent hover:border-slate-300 dark:hover:border-slate-600 text-sm font-medium text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 transition-all flex items-center space-x-2">
                        <span className="w-2 h-2 rounded-full bg-purple-600"></span>
                        <span>Governance</span>
                    </button>
                    <button className="pb-3 pt-4 px-1 border-b-2 border-transparent hover:border-slate-300 dark:hover:border-slate-600 text-sm font-medium text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 transition-all flex items-center space-x-2">
                        <span className="w-2 h-2 rounded-full bg-green-600"></span>
                        <span>Audit / Docs</span>
                    </button>
                </nav>
            </div>

            {/* Main Content */}
            <main className="flex-1 flex flex-col p-4 md:p-6 overflow-hidden min-h-0 bg-slate-50/50 dark:bg-slate-950/50">
                <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6 min-h-0 mb-6">
                    {/* Agent Loop Visualization */}
                    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-soft relative overflow-hidden flex flex-col">
                        <div className="absolute inset-0 bg-[linear-gradient(to_right,#e2e8f0_1px,transparent_1px),linear-gradient(to_bottom,#e2e8f0_1px,transparent_1px)] dark:bg-[linear-gradient(to_right,#334155_1px,transparent_1px),linear-gradient(to_bottom,#334155_1px,transparent_1px)] bg-[length:24px_24px] opacity-30 pointer-events-none"></div>
                        <div className="scan-line pointer-events-none"></div>

                        <div className="absolute top-4 left-4 z-20">
                            <h2 className="text-xs font-bold text-slate-400 dark:text-slate-500 flex items-center uppercase tracking-widest bg-white/80 dark:bg-slate-900/80 backdrop-blur px-2 py-1 rounded-md border border-slate-100 dark:border-slate-800">
                                <span className={`w-1.5 h-1.5 rounded-full mr-2 ${data.agentLoopActive ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'
                                    }`}></span>
                                Agent Loop {data.agentLoopActive ? 'Active' : 'Inactive'}
                            </h2>
                        </div>

                        <div className="flex-1 flex items-center justify-center relative">
                            <div className="absolute w-[400px] h-[400px] bg-blue-50/80 dark:bg-blue-900/20 rounded-full blur-3xl"></div>

                            {/* Orbital Container */}
                            <div className="orbit-container scale-75 md:scale-90 lg:scale-100">
                                {/* Core */}
                                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-28 h-28 bg-white dark:bg-slate-800 rounded-full flex flex-col items-center justify-center border border-slate-200 dark:border-slate-700 shadow-lg z-20 ring-4 ring-slate-50 dark:ring-slate-900">
                                    <svg className="w-8 h-8 text-slate-700 dark:text-slate-300 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                                    </svg>
                                    <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 mt-1 tracking-widest">CORE</span>
                                </div>

                                {/* Orbit Track */}
                                <div className="orbit-track border-slate-300 dark:border-slate-700">
                                    {/* Red Agent */}
                                    <div className="orbit-node node-top border-red-100 dark:border-red-900/50 bg-white dark:bg-slate-800 group cursor-pointer hover:scale-110 transition-transform hover:shadow-lg">
                                        <svg className="w-5 h-5 text-red-600 dark:text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                        </svg>
                                        <div className="absolute -top-8 w-max px-2 py-1 rounded bg-white dark:bg-slate-800 border border-red-100 dark:border-red-900 shadow-sm text-[10px] font-bold text-red-600 dark:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">Red Agent</div>
                                    </div>

                                    {/* Blue Agent */}
                                    <div className="orbit-node node-right border-blue-100 dark:border-blue-900/50 bg-white dark:bg-slate-800 group cursor-pointer hover:scale-110 transition-transform hover:shadow-lg">
                                        <svg className="w-5 h-5 text-blue-600 dark:text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                                        </svg>
                                        <div className="absolute -right-24 top-1/2 -translate-y-1/2 w-max px-2 py-1 rounded bg-white dark:bg-slate-800 border border-blue-100 dark:border-blue-900 shadow-sm text-[10px] font-bold text-blue-600 dark:text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">Blue Agent</div>
                                    </div>

                                    {/* Governance */}
                                    <div className="orbit-node node-bottom border-purple-100 dark:border-purple-900/50 bg-white dark:bg-slate-800 group cursor-pointer hover:scale-110 transition-transform hover:shadow-lg">
                                        <svg className="w-5 h-5 text-purple-600 dark:text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
                                        </svg>
                                        <div className="absolute -bottom-8 w-max px-2 py-1 rounded bg-white dark:bg-slate-800 border border-purple-100 dark:border-purple-900 shadow-sm text-[10px] font-bold text-purple-600 dark:text-purple-500 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">Governance</div>
                                    </div>

                                    {/* Audit */}
                                    <div className="orbit-node node-left border-green-100 dark:border-green-900/50 bg-white dark:bg-slate-800 group cursor-pointer hover:scale-110 transition-transform hover:shadow-lg">
                                        <svg className="w-5 h-5 text-green-600 dark:text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                        <div className="absolute -left-24 top-1/2 -translate-y-1/2 w-max px-2 py-1 rounded bg-white dark:bg-slate-800 border border-green-100 dark:border-green-900 shadow-sm text-[10px] font-bold text-green-600 dark:text-green-500 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">Audit</div>
                                    </div>
                                </div>

                                {/* Inner dashed circle */}
                                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[180px] h-[180px] border border-dashed border-slate-200 dark:border-slate-700 rounded-full animate-[spin_15s_linear_reverse_infinite]"></div>
                            </div>
                        </div>

                        <div className="absolute bottom-4 right-4 flex space-x-3 text-[10px] font-mono text-slate-400 dark:text-slate-500 bg-white/80 dark:bg-slate-900/80 backdrop-blur px-3 py-1.5 rounded-full border border-slate-100 dark:border-slate-800">
                            <div className="flex items-center"><span className="w-2 h-2 rounded-full bg-red-600 mr-1.5"></span>Attack</div>
                            <div className="flex items-center"><span className="w-2 h-2 rounded-full bg-blue-600 mr-1.5"></span>Defend</div>
                            <div className="flex items-center"><span className="w-2 h-2 rounded-full bg-purple-600 mr-1.5"></span>Verify</div>
                        </div>
                    </div>

                    {/* Terminal Logs */}
                    <div className="bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-soft flex flex-col font-mono text-xs overflow-hidden">
                        <div className="bg-slate-100 dark:bg-slate-800 px-4 py-2.5 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between shrink-0">
                            <div className="flex items-center space-x-2">
                                <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                </svg>
                                <span className="text-slate-600 dark:text-slate-300 font-semibold">system_orchestrator.log</span>
                            </div>
                            <div className="flex items-center space-x-1.5">
                                <span className="w-2.5 h-2.5 rounded-full bg-slate-300 dark:bg-slate-600 border border-slate-400/30"></span>
                                <span className="w-2.5 h-2.5 rounded-full bg-slate-300 dark:bg-slate-600 border border-slate-400/30"></span>
                            </div>
                        </div>
                        <div className="p-4 overflow-y-auto custom-scrollbar flex-1 space-y-2 text-slate-600 dark:text-slate-400 bg-white dark:bg-slate-900/50 font-medium">
                            {data.logs.map((log, index) => (
                                <LogEntryComponent key={index} entry={log} isDark={isDark} />
                            ))}
                            {/* Active cursor */}
                            <div className="flex animate-pulse">
                                <span className="text-slate-400 dark:text-slate-500 mr-3 w-20 shrink-0 select-none">[10:42:24]</span>
                                <span className="w-2 h-4 bg-slate-400 dark:bg-slate-600"></span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Stats Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 h-auto shrink-0">
                    <div className="bg-white dark:bg-slate-900 rounded-xl p-4 border border-slate-200 dark:border-slate-800 shadow-soft flex items-center justify-between hover:shadow-md transition-shadow">
                        <div>
                            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Vulns Found</p>
                            <h3 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{data.stats.vulnsFound}</h3>
                        </div>
                        <div className="h-10 w-10 rounded-lg bg-red-50 dark:bg-red-950/20 flex items-center justify-center border border-red-100 dark:border-red-900">
                            <svg className="w-5 h-5 text-red-600 dark:text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                        </div>
                    </div>

                    <div className="bg-white dark:bg-slate-900 rounded-xl p-4 border border-slate-200 dark:border-slate-800 shadow-soft flex items-center justify-between hover:shadow-md transition-shadow">
                        <div>
                            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Auto-Fixed</p>
                            <h3 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{data.stats.autoFixed}</h3>
                        </div>
                        <div className="h-10 w-10 rounded-lg bg-blue-50 dark:bg-blue-950/20 flex items-center justify-center border border-blue-100 dark:border-blue-900">
                            <svg className="w-5 h-5 text-blue-600 dark:text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                        </div>
                    </div>

                    <div className="bg-white dark:bg-slate-900 rounded-xl p-4 border border-slate-200 dark:border-slate-800 shadow-soft flex items-center justify-between hover:shadow-md transition-shadow">
                        <div>
                            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Pull Requests</p>
                            <h3 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{data.stats.pullRequests}</h3>
                        </div>
                        <div className="h-10 w-10 rounded-lg bg-purple-50 dark:bg-purple-950/20 flex items-center justify-center border border-purple-100 dark:border-purple-900">
                            <svg className="w-5 h-5 text-purple-600 dark:text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                            </svg>
                        </div>
                    </div>

                    <div className="bg-white dark:bg-slate-900 rounded-xl p-4 border border-slate-200 dark:border-slate-800 shadow-soft flex items-center justify-between hover:shadow-md transition-shadow">
                        <div>
                            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">System Uptime</p>
                            <h3 className="text-2xl font-bold text-green-600 dark:text-green-500">{data.stats.systemUptime}</h3>
                        </div>
                        <div className="h-10 w-10 rounded-lg bg-green-50 dark:bg-green-950/20 flex items-center justify-center border border-green-100 dark:border-green-900">
                            <svg className="w-5 h-5 text-green-600 dark:text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                    </div>
                </div>
            </main>

            <style jsx>{`
        .orbit-container {
          position: relative;
          width: 360px;
          height: 360px;
        }
        .orbit-track {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          width: 280px;
          height: 280px;
          border: 1px dashed;
          border-radius: 50%;
          animation: spin 30s linear infinite;
        }
        .orbit-node {
          position: absolute;
          width: 56px;
          height: 56px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
          animation: spin-reverse 30s linear infinite;
          z-index: 10;
          border-width: 1px;
        }
        .node-top { top: -28px; left: 50%; transform: translateX(-50%); }
        .node-right { top: 50%; right: -28px; transform: translateY(-50%); }
        .node-bottom { bottom: -28px; left: 50%; transform: translateX(-50%); }
        .node-left { top: 50%; left: -28px; transform: translateY(-50%); }
        @keyframes spin { 100% { transform: translate(-50%, -50%) rotate(360deg); } }
        @keyframes spin-reverse { 100% { transform: rotate(-360deg); } }
        .custom-scrollbar::-webkit-scrollbar { width: 8px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: rgb(241 245 249 / 1); }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgb(203 213 225 / 1); border-radius: 4px; border: 2px solid rgb(241 245 249 / 1); }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgb(148 163 184 / 1); }
        .scan-line {
          width: 100%;
          height: 2px;
          background: rgba(37, 99, 235, 0.2);
          position: absolute;
          top: 0;
          left: 0;
          animation: scan 4s linear infinite;
          opacity: 0.1;
          box-shadow: 0 0 4px rgba(37, 99, 235, 0.2);
        }
        @keyframes scan { 
          0% { top: 0%; opacity: 0; }
          10% { opacity: 0.1; }
          90% { opacity: 0.1; }
          100% { top: 100%; opacity: 0; }
        }
      `}</style>
        </div>
    );
}
