import { LucideIcon } from "lucide-react";
import { cn } from "../lib/utils";

interface StatsCardProps {
    name: string;
    value: string;
    change?: string;
    changeType?: "positive" | "negative" | "neutral";
    icon: LucideIcon;
    description?: string;
    className?: string;
    color?: "default" | "red" | "blue" | "emerald" | "amber" | "purple";
}

export default function StatsCard({
    name,
    value,
    change,
    changeType = "neutral",
    icon: Icon,
    description,
    className,
    color = "default",
}: StatsCardProps) {
    const colorStyles = {
        default: "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800",
        red: "bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-900/50",
        blue: "bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-900/50",
        emerald: "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-900/50",
        amber: "bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-900/50",
        purple: "bg-purple-50 dark:bg-purple-950/30 border-purple-200 dark:border-purple-900/50",
    };

    const iconColors = {
        default: "text-slate-500",
        red: "text-red-500",
        blue: "text-blue-500",
        emerald: "text-emerald-500",
        amber: "text-amber-500",
        purple: "text-purple-500",
    };

    return (
        <div className={cn("rounded-xl border p-6 shadow-sm", colorStyles[color], className)}>
            <div className="flex items-center">
                <div className="flex-shrink-0">
                    <Icon className={cn("h-6 w-6", iconColors[color])} aria-hidden="true" />
                </div>
                <div className="ml-4 flex-1">
                    <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400">{name}</h3>
                    <div className="flex items-baseline">
                        <p className="text-2xl font-semibold text-slate-900 dark:text-white">{value}</p>
                        {change && (
                            <p
                                className={cn(
                                    "ml-2 flex items-baseline text-sm font-semibold",
                                    changeType === "positive" ? "text-emerald-600 dark:text-emerald-400" :
                                        changeType === "negative" ? "text-red-600 dark:text-red-400" :
                                            "text-slate-500 dark:text-slate-400"
                                )}
                            >
                                {change}
                            </p>
                        )}
                    </div>
                    {description && (
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-500">{description}</p>
                    )}
                </div>
            </div>
        </div>
    );
}
