
import { useState, useEffect, useRef } from 'react';
import { LogEntry } from '../lib/types';
import { fetchLogs } from '../lib/api';

export function useScanLogs(scanId: string | null, isPaused: boolean = false) {
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const retryCountRef = useRef(0);

    useEffect(() => {
        if (!scanId || isPaused) return;

        let timeoutId: NodeJS.Timeout;
        let isMounted = true;

        const pollLogs = async () => {
            if (!isMounted) return;

            try {
                // Determine interval based on retries (simple backoff)
                const interval = Math.min(2000 + (retryCountRef.current * 1000), 10000);

                const fetchedLogs = await fetchLogs(scanId);

                if (fetchedLogs && fetchedLogs.length > 0) {
                    // Start of append logic - optimizations could be done here (only append new)
                    // But currently backend returns ALL logs.
                    setLogs(fetchedLogs);
                    retryCountRef.current = 0; // Reset backoff on success
                } else {
                    // If fetchedLogs is empty, it might be an error or just no logs yet.
                    // If we ALREADY have logs, preserving them is safer than clearing them
                    // to prevent "disappearing" on transient failures.
                    if (logs.length === 0 && fetchedLogs.length === 0) {
                        // Valid empty state
                    } else if (fetchedLogs.length === 0 && logs.length > 0) {
                        console.warn("Fetched empty logs but have existing logs. Preserving existing.");
                        // Do NOT setLogs([]) here.
                    }
                }
            } catch (error) {
                console.warn("Log polling error:", error);
                retryCountRef.current += 1;
            } finally {
                if (isMounted && !isPaused) {
                    // Schedule next poll
                    const nextInterval = Math.min(2000 + (retryCountRef.current * 1000), 10000);
                    timeoutId = setTimeout(pollLogs, nextInterval);
                }
            }
        };

        pollLogs();

        return () => {
            isMounted = false;
            clearTimeout(timeoutId);
        };
    }, [scanId, isPaused]);

    return { logs, isLoading };
}
