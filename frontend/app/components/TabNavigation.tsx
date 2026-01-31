"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "../lib/utils";
import { Activity, ShieldAlert, ShieldCheck, Scale, FileText, Search } from "lucide-react";

const tabs = [
    {
        name: "Agent Loop",
        href: "/warloop",
        icon: Activity,
        color: "text-emerald-500",
    },
    {
        name: "Red Agent",
        href: "/redagent",
        icon: ShieldAlert,
        color: "text-red-500",
    },
    {
        name: "Blue Agent",
        href: "/blueagent",
        icon: ShieldCheck,
        color: "text-blue-500",
    },
    {
        name: "Governance",
        href: "/governance",
        icon: Scale,
        color: "text-amber-500",
    },
    {
        name: "Audit & Docs",
        href: "/audit",
        icon: FileText,
        color: "text-purple-500",
    },
    {
        name: "Research",
        href: "/research",
        icon: Search,
        color: "text-cyan-500",
    },
];

export default function TabNavigation() {
    const pathname = usePathname();

    return (
        <div className="border-b border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-950/50 backdrop-blur sticky top-16 z-30">
            <div className="px-4 sm:px-6 lg:px-8">
                <nav className="-mb-px flex space-x-8 overflow-x-auto no-scrollbar" aria-label="Tabs">
                    {tabs.map((tab) => {
                        const isActive = pathname === tab.href;
                        const Icon = tab.icon;

                        return (
                            <Link
                                key={tab.name}
                                href={tab.href}
                                className={cn(
                                    isActive
                                        ? "border-emerald-500 text-emerald-600 dark:text-emerald-400"
                                        : "border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700 dark:text-slate-400 dark:hover:border-slate-700 dark:hover:text-slate-300",
                                    "group inline-flex items-center border-b-2 py-4 px-1 text-sm font-medium whitespace-nowrap transition-colors"
                                )}
                                aria-current={isActive ? "page" : undefined}
                            >
                                <Icon
                                    className={cn(
                                        isActive ? tab.color : "text-slate-400 group-hover:text-slate-500 dark:text-slate-500 dark:group-hover:text-slate-400",
                                        "-ml-0.5 mr-2 h-4 w-4 transition-colors"
                                    )}
                                    aria-hidden="true"
                                />
                                <span>{tab.name}</span>
                            </Link>
                        );
                    })}
                </nav>
            </div>
        </div>
    );
}
