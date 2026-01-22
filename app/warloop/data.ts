// Data types for War Room
export interface LogEntry {
    timestamp: string;
    agent: 'ORCHESTRATOR' | 'RED_AGENT' | 'BLUE_AGENT' | 'GOVERNANCE' | 'AUDIT';
    message: string;
    highlight?: boolean;
    codeReference?: string;
}

export interface RepositoryInfo {
    owner: string;
    name: string;
    status: 'Active' | 'Inactive' | 'Paused';
}

export interface Stats {
    vulnsFound: number;
    autoFixed: number;
    pullRequests: number;
    systemUptime: string;
}

export interface WarRoomData {
    repository: RepositoryInfo;
    stats: Stats;
    logs: LogEntry[];
    agentLoopActive: boolean;
}

// Mock data - will be replaced with API calls
export const MOCK_WAR_ROOM_DATA: WarRoomData = {
    repository: {
        owner: 'stripe',
        name: 'stripe-ios',
        status: 'Active',
    },
    stats: {
        vulnsFound: 12,
        autoFixed: 8,
        pullRequests: 4,
        systemUptime: '99.9%',
    },
    agentLoopActive: true,
    logs: [
        {
            timestamp: '10:42:01',
            agent: 'ORCHESTRATOR',
            message: 'Initializing scan cycle #4922...',
        },
        {
            timestamp: '10:42:02',
            agent: 'RED_AGENT',
            message: 'Target identified: ',
            codeReference: 'src/auth/login.ts',
        },
        {
            timestamp: '10:42:02',
            agent: 'RED_AGENT',
            message: 'Injecting payload pattern SQLi_Vector_04...',
        },
        {
            timestamp: '10:42:05',
            agent: 'RED_AGENT',
            message: 'CRITICAL VULNERABILITY DETECTED (CWE-89)',
            highlight: true,
        },
        {
            timestamp: '10:42:06',
            agent: 'BLUE_AGENT',
            message: 'Analyzing attack vector...',
        },
        {
            timestamp: '10:42:07',
            agent: 'BLUE_AGENT',
            message: 'Context: Unsanitized input in query string builder.',
        },
        {
            timestamp: '10:42:09',
            agent: 'BLUE_AGENT',
            message: 'Applying patch strategy: Parameterized Query Transformation.',
        },
        {
            timestamp: '10:42:12',
            agent: 'BLUE_AGENT',
            message: 'Validating fix against test suite... PASSED',
        },
        {
            timestamp: '10:42:15',
            agent: 'GOVERNANCE',
            message: 'Checking license compliance (MIT)... OK',
        },
        {
            timestamp: '10:42:15',
            agent: 'GOVERNANCE',
            message: 'Checking style guidelines (Prettier)... OK',
        },
        {
            timestamp: '10:42:18',
            agent: 'AUDIT',
            message: 'Generating report artifacts...',
        },
        {
            timestamp: '10:42:19',
            agent: 'AUDIT',
            message: 'Pull Request #402 created.',
        },
        {
            timestamp: '10:42:22',
            agent: 'ORCHESTRATOR',
            message: 'Cycle complete. Cooling down (2000ms)...',
        },
    ],
};

// TODO: Replace with actual API endpoint
// export async function fetchWarRoomData(): Promise<WarRoomData> {
//   const response = await fetch('/api/warroom');
//   return response.json();
// }

// For now, return mock data
export function getWarRoomData(): WarRoomData {
    return MOCK_WAR_ROOM_DATA;
}
