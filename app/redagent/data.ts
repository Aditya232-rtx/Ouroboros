// Data types for Red Agent page
export interface RedAgentLogEntry {
    timestamp: string;
    message: string;
    severity?: 'info' | 'warn' | 'critical' | 'success' | 'action';
    highlight?: boolean;
}

export interface RedAgentStats {
    vulnerabilitiesFound: number;
    autoFixed: number;
    pullRequests: number;
    uptime: string;
}

export interface RedAgentData {
    repository: {
        owner: string;
        name: string;
    };
    systemActive: boolean;
    agentStatus: 'active' | 'idle' | 'paused';
    currentActivity: string;
    stats: RedAgentStats;
    logs: RedAgentLogEntry[];
}

// Mock data for Red Agent
export const MOCK_RED_AGENT_DATA: RedAgentData = {
    repository: {
        owner: 'acme',
        name: 'api-gateway',
    },
    systemActive: true,
    agentStatus: 'active',
    currentActivity: 'Simulating Attack Vectors...',
    stats: {
        vulnerabilitiesFound: 12,
        autoFixed: 8,
        pullRequests: 3,
        uptime: '42h 12m',
    },
    logs: [
        {
            timestamp: '10:42:01',
            message: 'Initializing Red Team Protocol v1.4.2...',
            severity: 'info',
        },
        {
            timestamp: '10:42:02',
            message: 'Target: github.com/acme/api-gateway',
            severity: 'info',
        },
        {
            timestamp: '10:42:05',
            message: 'WARN: Potentially exposed .env file detected in commit history (SHA: 7a8b9c).',
            severity: 'warn',
        },
        {
            timestamp: '10:42:08',
            message: 'Scanning for SQL Injection vulnerabilities in /auth/login endpoint...',
            severity: 'info',
        },
        {
            timestamp: '10:42:09',
            message: "> Payload: ' OR 1=1 --",
            severity: 'info',
        },
        {
            timestamp: '10:42:09',
            message: 'Response: 403 Forbidden (Sanitization Active) - PASS',
            severity: 'success',
        },
        {
            timestamp: '10:42:12',
            message: 'Scanning for XSS in user profile comments...',
            severity: 'info',
        },
        {
            timestamp: '10:42:15',
            message: 'CRITICAL: Stored XSS vulnerability found in POST /api/comments',
            severity: 'critical',
            highlight: true,
        },
        {
            timestamp: '',
            message: 'Details: Input is not properly escaped before rendering in Dashboard.vue:45',
            severity: 'info',
        },
        {
            timestamp: '10:42:16',
            message: 'Creating issue ticket #402 on GitHub repository...',
            severity: 'action',
        },
        {
            timestamp: '10:42:18',
            message: 'Generating patch suggestion via LLM...',
            severity: 'info',
        },
        {
            timestamp: '10:42:21',
            message: 'Patch generated. Passing context to Blue Agent for verification.',
            severity: 'action',
        },
        {
            timestamp: '10:42:22',
            message: 'Waiting for Blue Agent approval_',
            severity: 'info',
        },
    ],
};

// Get Red Agent data (currently returns mock data)
export function getRedAgentData(): RedAgentData {
    return MOCK_RED_AGENT_DATA;
}

// TODO: Replace with actual API endpoint
// export async function fetchRedAgentData(): Promise<RedAgentData> {
//   const response = await fetch('/api/redagent');
//   return response.json();
// }
