import { type LogEntry } from './data';

// Helper function to get agent color
export function getAgentColor(agent: LogEntry['agent'], isDark: boolean): string {
    const colors = {
        ORCHESTRATOR: isDark ? 'text-blue-500' : 'text-blue-600',
        RED_AGENT: isDark ? 'text-red-500' : 'text-red-600',
        BLUE_AGENT: isDark ? 'text-blue-500' : 'text-blue-600',
        GOVERNANCE: isDark ? 'text-purple-500' : 'text-purple-600',
        AUDIT: isDark ? 'text-green-500' : 'text-green-600',
    };
    return colors[agent];
}

// Component to render a single log entry
export function LogEntryComponent({ entry, isDark }: { entry: LogEntry; isDark: boolean }) {
    const agentColor = getAgentColor(entry.agent, isDark);

    return (
        <div className={`flex ${entry.highlight ? 'bg-red-50 dark:bg-red-950/20 -mx-4 px-4 py-1.5 border-y border-red-100/50 dark:border-red-900/30' : ''}`}>
            <span className="text-slate-400 dark:text-slate-500 mr-3 w-20 shrink-0 select-none">[{entry.timestamp}]</span>
            <span>
                <span className={`${agentColor} font-bold`}>{entry.agent}</span>: {entry.message}
                {entry.codeReference && (
                    <span className="text-slate-800 dark:text-slate-200 bg-slate-100 dark:bg-slate-800 px-1 rounded">
                        {entry.codeReference}
                    </span>
                )}
            </span>
        </div>
    );
}
