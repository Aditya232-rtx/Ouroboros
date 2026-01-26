"use client";

import { Switch } from "./lightswind/switch";
import { Badge } from "./lightswind/badge";
import { Shield, Lock, Globe } from "lucide-react";

export default function PolicyPanel() {
    const policies = [
        { name: "Require Two-Person Review", enabled: true, icon: Shield },
        { name: "Block Critical Vulnerabilities", enabled: true, icon: Lock },
        { name: "Enforce HTTPS Everywhere", enabled: true, icon: Globe },
        { name: "Auto-Approve Low Risks", enabled: false, icon: Shield },
    ];

    return (
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden shadow-sm">
            <div className="p-6 border-b border-slate-200 dark:border-slate-800">
                <h3 className="font-semibold text-slate-900 dark:text-white">Enforcement Policies</h3>
                <p className="text-sm text-slate-500">Configure automated decision gates</p>
            </div>
            <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {policies.map((policy) => {
                    const Icon = policy.icon;
                    return (
                        <div key={policy.name} className="flex items-center justify-between p-4 px-6 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                            <div className="flex items-center space-x-3">
                                <div className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                                    <Icon className="h-5 w-5" />
                                </div>
                                <div>
                                    <p className="font-medium text-slate-900 dark:text-white">{policy.name}</p>
                                    <div className="flex items-center mt-1">
                                        {policy.enabled ? (
                                            <Badge variant="outline" className="text-emerald-600 border-emerald-200 bg-emerald-50 text-[10px]">Active</Badge>
                                        ) : (
                                            <Badge variant="outline" className="text-slate-500 text-[10px]">Disabled</Badge>
                                        )}
                                    </div>
                                </div>
                            </div>
                            <Switch checked={policy.enabled} />
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
