'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { getRedAgentData, type RedAgentLogEntry } from './data';

// Helper function to get log color based on severity
function getLogColor(severity?: RedAgentLogEntry['severity'], isDark: boolean): string {
    if (!severity) return isDark ? 'text-gray-300' : 'text-gray-700';

    const colors = {
        info: isDark ? 'text-gray-300' : 'text-gray-700',
        warn: isDark ? 'text-yellow-400' : 'text-yellow-600',
        critical: isDark ? 'text-red-400' : 'text-red-600',
        success: isDark ? 'text-green-400' : 'text-green-600',
        action: isDark ? 'text-blue-400' : 'text-blue-600',
    };
    return colors[severity];
}

export default function RedAgent() {
    const [isDark, setIsDark] = useState(false);
    const data = getRedAgentData();

    useEffect(() => {
        const updateDarkMode = () => {
            const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
            setIsDark(document.documentElement.classList.contains('dark') || prefersDark);
        };
        updateDarkMode();

        const observer = new MutationObserver(updateDarkMode);
        observer.observe(document.documentElement, { attributes: true });
        return () => observer.disconnect();
    }, []);

    return (
        <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
            {/* Navigation */}
            <nav className="sticky top-0 z-50 bg-white/80 dark:bg-gray-800/80 backdrop-blur-md border-b border-gray-200 dark:border-gray-700 h-16 px-6 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded bg-red-600 flex items-center justify-center text-white font-bold">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                    </div>
                    <span className="font-bold text-xl tracking-tight">Ouroborus</span>
                </div>
                <div className="flex items-center gap-4">
                    <div className={`hidden md:flex items-center px-3 py-1 rounded-full text-sm font-medium border ${data.systemActive
                        ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800'
                        : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-400 border-gray-200 dark:border-gray-700'
                        }`}>
                        <span className={`w-2 h-2 rounded-full mr-2 ${data.systemActive ? 'bg-emerald-500 animate-pulse' : 'bg-gray-400'}`}></span>
                        {data.systemActive ? 'System Active' : 'System Inactive'}
                    </div>
                    <button className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors">
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                    </button>
                    <Link href="/" className="w-8 h-8 rounded-full bg-gradient-to-tr from-red-600 to-purple-500"></Link>
                </div>
            </nav>

            {/* Main Content */}
            <main className="flex-1 flex flex-col p-6 max-w-7xl mx-auto w-full gap-6">
                {/* Header */}
                <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <h1 className="text-2xl font-bold flex items-center gap-2">
                            <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                            </svg>
                            War Room
                        </h1>
                        <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">
                            Monitoring autonomous security agents on <span className="font-mono text-xs bg-gray-200 dark:bg-gray-800 px-1 py-0.5 rounded">github.com/{data.repository.owner}/{data.repository.name}</span>
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        <button className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded shadow-sm text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-700 transition">
                            Pause Simulation
                        </button>
                        <button className="px-4 py-2 bg-red-600 text-white rounded shadow-sm text-sm font-medium hover:bg-red-700 transition flex items-center gap-2">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                            Force Scan
                        </button>
                    </div>
                </header>

                {/* Tabs */}
                <div className="border-b border-gray-200 dark:border-gray-700">
                    <nav className="-mb-px flex space-x-8">
                        <div className="border-red-600 text-red-600 whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-red-600 animate-pulse"></span>
                            Red Agent
                        </div>
                        <Link href="/warloop" className="border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300 whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                            Blue Agent
                        </Link>
                        <button className="border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300 whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-purple-500"></span>
                            Governance
                        </button>
                        <button className="border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300 whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            Audit / Docs
                        </button>
                    </nav>
                </div>

                {/* Main Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-[500px]">
                    {/* Agent Loop Visualization */}
                    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6 flex flex-col items-center justify-center relative overflow-hidden shadow-sm">
                        <div className="absolute inset-0 bg-[radial-gradient(#e5e7eb_1px,transparent_1px)] dark:bg-[radial-gradient(#374151_1px,transparent_1px)] [background-size:16px_16px] opacity-50"></div>
                        <h3 className="absolute top-4 left-6 text-sm font-semibold text-gray-500 uppercase tracking-wider">Agent Loop</h3>

                        <div className="relative w-64 h-64">
                            {/* Rotating dashed circle */}
                            <div className="absolute inset-0 rounded-full border-2 border-dashed border-gray-300 dark:border-gray-600 animate-[spin_12s_linear_infinite]"></div>

                            {/* Center RED Agent */}
                            <div className="absolute inset-0 flex items-center justify-center z-10">
                                <div className="w-24 h-24 rounded-full bg-white dark:bg-gray-800 border-4 border-red-600 shadow-[0_0_20px_rgba(239,68,68,0.3)] flex flex-col items-center justify-center relative">
                                    <svg className="w-8 h-8 text-red-600 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                    </svg>
                                    <span className="text-xs font-bold text-red-600">RED</span>
                                    <div className="absolute -bottom-8 bg-red-50 dark:bg-red-900/20 text-red-600 px-2 py-0.5 rounded text-[10px] font-mono border border-red-200 dark:border-red-800">
                                        {data.agentStatus === 'active' ? 'Active' : 'Idle'}
                                    </div>
                                </div>
                            </div>

                            {/* Blue Agent - Top */}
                            <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-white dark:bg-gray-800 border-2 border-blue-500 flex items-center justify-center shadow-md">
                                <span className="text-[10px] font-bold text-blue-500">BLUE</span>
                            </div>

                            {/* Governance - Bottom Right */}
                            <div className="absolute bottom-10 right-0 w-12 h-12 rounded-full bg-white dark:bg-gray-800 border-2 border-purple-500 flex items-center justify-center shadow-md">
                                <span className="text-[10px] font-bold text-purple-500">GOV</span>
                            </div>

                            {/* Audit - Bottom Left */}
                            <div className="absolute bottom-10 left-0 w-12 h-12 rounded-full bg-white dark:bg-gray-800 border-2 border-yellow-500 flex items-center justify-center shadow-md">
                                <span className="text-[10px] font-bold text-yellow-500">AUD</span>
                            </div>
                        </div>

                        <div className="mt-8 text-center z-10">
                            <div className="flex items-center justify-center gap-2 text-red-600 font-mono text-sm">
                                <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                </svg>
                                {data.currentActivity}
                            </div>
                        </div>
                    </div>

                    {/* Terminal Log Panel */}
                    <div className="lg:col-span-2 bg-gray-900 dark:bg-black rounded-xl border border-gray-800 shadow-xl flex flex-col overflow-hidden font-mono text-sm">
                        {/* Terminal Header */}
                        <div className="bg-gray-800/50 border-b border-gray-700 px-4 py-2 flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <div className="flex gap-1.5">
                                    <div className="w-3 h-3 rounded-full bg-red-500"></div>
                                    <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                                </div>
                                <span className="ml-3 text-gray-400 text-xs">red_agent_output.log</span>
                            </div>
                            <div className="flex items-center gap-3">
                                <span className="flex items-center gap-1 text-xs text-green-400">
                                    <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse"></span>
                                    Live Stream
                                </span>
                                <button className="text-gray-500 hover:text-gray-300">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                    </svg>
                                </button>
                                <button className="text-gray-500 hover:text-gray-300">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                    </svg>
                                </button>
                            </div>
                        </div>

                        {/* Terminal Content */}
                        <div className="flex-1 p-4 overflow-y-auto text-gray-300 space-y-1" style={{ scrollbarWidth: 'thin', scrollbarColor: '#4B5563 transparent' }}>
                            {data.logs.map((log, index) => (
                                <div
                                    key={index}
                                    className={`flex gap-3 ${log.highlight ? 'bg-red-900/20 border-l-2 border-red-500 pl-2 -ml-2' : ''} ${index < data.logs.length - 3 ? 'opacity-75' : index < data.logs.length - 1 ? 'opacity-90' : ''
                                        }`}
                                >
                                    <span className="text-gray-500 select-none w-16 text-right">{log.timestamp}</span>
                                    <span className={getLogColor(log.severity, true)}>{log.message}</span>
                                </div>
                            ))}
                            <div className="flex gap-3 animate-pulse">
                                <span className="text-gray-500 select-none w-16 text-right"></span>
                                <span className="border-r-2 border-gray-400 pr-1"></span>
                            </div>
                        </div>

                        {/* Terminal Input */}
                        <div className="bg-gray-800 p-2 border-t border-gray-700 flex items-center">
                            <span className="text-red-600 mr-2">❯</span>
                            <input
                                className="bg-transparent border-none w-full text-gray-500 text-sm focus:ring-0 cursor-not-allowed"
                                disabled
                                placeholder="System running autonomous loop..."
                                type="text"
                            />
                        </div>
                    </div>
                </div>

                {/* Stats Cards */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-2">
                    <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700 flex items-center justify-between shadow-sm">
                        <div>
                            <p className="text-xs text-gray-500 dark:text-gray-400 uppercase font-semibold">Vulnerabilities Found</p>
                            <p className="text-2xl font-bold">{data.stats.vulnerabilitiesFound}</p>
                        </div>
                        <div className="bg-red-100 dark:bg-red-900/30 p-2 rounded text-red-600">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                        </div>
                    </div>

                    <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700 flex items-center justify-between shadow-sm">
                        <div>
                            <p className="text-xs text-gray-500 dark:text-gray-400 uppercase font-semibold">Auto-Fixed</p>
                            <p className="text-2xl font-bold">{data.stats.autoFixed}</p>
                        </div>
                        <div className="bg-green-100 dark:bg-green-900/30 p-2 rounded text-green-600">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                        </div>
                    </div>

                    <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700 flex items-center justify-between shadow-sm">
                        <div>
                            <p className="text-xs text-gray-500 dark:text-gray-400 uppercase font-semibold">Pull Requests</p>
                            <p className="text-2xl font-bold">{data.stats.pullRequests}</p>
                        </div>
                        <div className="bg-blue-100 dark:bg-blue-900/30 p-2 rounded text-blue-600">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                            </svg>
                        </div>
                    </div>

                    <div className="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700 flex items-center justify-between shadow-sm">
                        <div>
                            <p className="text-xs text-gray-500 dark:text-gray-400 uppercase font-semibold">Uptime</p>
                            <p className="text-2xl font-bold">{data.stats.uptime}</p>
                        </div>
                        <div className="bg-purple-100 dark:bg-purple-900/30 p-2 rounded text-purple-600">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                    </div>
                </div>
            </main>

            {/* Footer */}
            <footer className="mt-8 py-6 border-t border-gray-200 dark:border-gray-700 text-center text-sm text-gray-500">
                <p>© 2023 Ouroborus Security. Autonomous Defense Systems.</p>
            </footer>
        </div>
    );
}
