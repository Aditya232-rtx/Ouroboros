"use client";

import { useEffect, useState } from "react";
import StatsCard from "../../components/StatsCard";
import AgentLoopVisualization from "../../components/AgentLoopVisualization";
import { Scale, AlertCircle, CheckCircle, Clock } from "lucide-react";
import { Badge } from "../../components/lightswind/badge";
import { Button } from "../../components/lightswind/button";

export default function GovernancePage() {
    return (
        <div className="h-[calc(100vh-8rem)] flex flex-col space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between pb-2">
                <div className="flex flex-col space-y-1">
                    <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center">
                        <span className="w-3 h-3 rounded-full bg-purple-500 mr-3 animate-pulse"></span>
                        Governance Console
                    </h1>
                    <p className="text-slate-500 text-sm ml-6">
                        Enforcing security policies on <span className="bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded font-mono text-xs">github.com/acme/api-gateway</span>
                    </p>
                </div>
                <div className="flex items-center space-x-3">
                    <Button variant="outline" className="bg-white dark:bg-slate-800">Policy Settings</Button>
                    <Button className="bg-purple-600 hover:bg-purple-700 text-white shadow-md shadow-purple-500/20">
                        <CheckCircle className="w-4 h-4 mr-2" />
                        Approve All Safe
                    </Button>
                </div>
            </div>

            {/* Main Content: Split Grid */}
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-0">
                {/* Left: Visualization (1 Col) */}
                <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 flex flex-col items-center justify-center relative overflow-hidden shadow-sm">
                    <h3 className="absolute top-4 left-4 text-xs font-bold text-slate-400 uppercase tracking-widest">Agent Loop</h3>
                    <div className="absolute top-4 right-4 text-[10px] bg-purple-500/10 text-purple-500 px-2 py-1 rounded-full border border-purple-500/20 font-mono">
                        Cycle #4092
                    </div>
                    {/* Simplified Agent Viz with Purple Highlight */}
                    <div className="w-full h-full flex items-center justify-center scale-90">
                        <AgentLoopVisualization status="verifying" />
                    </div>

                    <div className="absolute bottom-6 bg-slate-50 dark:bg-slate-800/50 px-4 py-2 rounded-full border border-slate-200 dark:border-slate-700 flex items-center space-x-2">
                        <div className="w-4 h-4 rounded-full border-2 border-purple-500 border-t-transparent animate-spin"></div>
                        <span className="text-xs font-mono text-slate-600 dark:text-slate-400 font-medium">Validating Compliance...</span>
                    </div>
                </div>

                {/* Right: Risk Queue (2 Cols) */}
                <div className="lg:col-span-2 flex flex-col bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
                    <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center bg-slate-50/50 dark:bg-slate-800/20">
                        <h3 className="font-bold text-slate-700 dark:text-slate-200 flex items-center">
                            <Scale className="w-4 h-4 mr-2" />
                            Risk Evaluation Queue
                        </h3>
                        <div className="flex items-center space-x-2 text-sm text-slate-500">
                            <span>Sort by:</span>
                            <select className="bg-transparent font-medium text-slate-700 dark:text-slate-300 outline-none">
                                <option>Severity</option>
                                <option>Time</option>
                            </select>
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto">
                        <table className="w-full text-left text-sm">
                            <thead className="bg-slate-50 dark:bg-slate-800/50 text-slate-500 font-medium border-b border-slate-100 dark:border-slate-800">
                                <tr>
                                    <th className="px-6 py-3">VULNERABILITY</th>
                                    <th className="px-6 py-3">CVSS / IMPACT</th>
                                    <th className="px-6 py-3">POLICY STATUS</th>
                                    <th className="px-6 py-3 text-right">ACTION</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                <tr className="group hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                                    <td className="px-6 py-4">
                                        <div className="font-bold text-slate-900 dark:text-white">SQL Injection in Login</div>
                                        <div className="text-xs text-slate-500 font-mono mt-0.5">auth/login.ts:42</div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center space-x-2">
                                            <Badge className="bg-red-50 text-red-600 border-red-100">9.8</Badge>
                                            <span className="font-bold text-red-600 text-xs">CRITICAL</span>
                                        </div>
                                        <div className="text-xs text-slate-400 mt-1">Business Impact: High</div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-start space-x-2">
                                            <AlertCircle className="w-4 h-4 text-amber-500 mt-0.5" />
                                            <div>
                                                <span className="font-medium text-amber-600 text-xs block">Requires Approval</span>
                                                <span className="text-[10px] text-slate-400">Rule: No Critical Auto-Merge</span>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <Button variant="outline" size="sm">Review</Button>
                                    </td>
                                </tr>
                                <tr className="group hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                                    <td className="px-6 py-4">
                                        <div className="font-bold text-slate-900 dark:text-white">Stored XSS in Comments</div>
                                        <div className="text-xs text-slate-500 font-mono mt-0.5">components/CommentList.vue:15</div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center space-x-2">
                                            <Badge className="bg-orange-50 text-orange-600 border-orange-100">7.5</Badge>
                                            <span className="font-bold text-orange-600 text-xs">HIGH</span>
                                        </div>
                                        <div className="text-xs text-slate-400 mt-1">Business Impact: Moderate</div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-start space-x-2">
                                            <AlertCircle className="w-4 h-4 text-amber-500 mt-0.5" />
                                            <div>
                                                <span className="font-medium text-amber-600 text-xs block">Requires Approval</span>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <Button variant="outline" size="sm">Review</Button>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            {/* Bottom: Stats Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatsCard
                    name="Pending Approvals"
                    value="5"
                    icon={Clock}
                    color="amber"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
                <StatsCard
                    name="Auto-Merged"
                    value="14"
                    icon={CheckCircle}
                    color="emerald"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
                <StatsCard
                    name="Policy Violations"
                    value="2"
                    icon={AlertCircle}
                    color="red"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
                <StatsCard
                    name="Avg. Time to Fix"
                    value="12m 30s"
                    icon={Clock}
                    color="purple"
                    className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 shadow-sm hover:shadow transition-shadow"
                />
            </div>
        </div>
    );
}
