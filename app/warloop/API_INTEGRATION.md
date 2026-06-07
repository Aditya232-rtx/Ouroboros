# War Room Data API Integration Guide

## Overview
The War Room page is currently using mock data, but it's structured to easily integrate with a backend API. This document explains the data format and how to implement the API endpoint.

## Data Structure

### WarRoomData Interface
```typescript
interface WarRoomData {
  repository: RepositoryInfo;
  stats: Stats;
  logs: LogEntry[];
  agentLoopActive: boolean;
}
```

### RepositoryInfo
```typescript
interface RepositoryInfo {
  owner: string;        // GitHub repo owner (e.g., "stripe")
  name: string;         // Repository name (e.g., "stripe-ios")
  status: 'Active' | 'Inactive' | 'Paused';
}
```

### Stats
```typescript
interface Stats {
  vulnsFound: number;      // Total vulnerabilities found
  autoFixed: number;       // Number of auto-fixed issues
  pullRequests: number;    // Number of PRs created
  systemUptime: string;    // Uptime percentage (e.g., "99.9%")
}
```

### LogEntry
```typescript
interface LogEntry {
  timestamp: string;       // Time in HH:MM:SS format (e.g., "10:42:01")
  agent: 'ORCHESTRATOR' | 'RED_AGENT' | 'BLUE_AGENT' | 'GOVERNANCE' | 'AUDIT';
  message: string;         // Log message
  highlight?: boolean;     // Optional: true for critical messages (red background)
  codeReference?: string;  // Optional: file path or code reference
}
```

## API Integration

### Step 1: Create API Endpoint
Create a new API route at `app/api/warroom/route.ts`:

```typescript
import { NextResponse } from 'next/server';
import { type WarRoomData } from '@/app/warloop/data';

export async function GET() {
  // TODO: Replace with actual data source
  // This could fetch from:
  // - Database
  // - External service
  // - Real-time WebSocket connection
  
  const data: WarRoomData = {
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
      // ... log entries
    ],
  };

  return NextResponse.json(data);
}
```

### Step 2: Update Data Fetching
In `app/warloop/data.ts`, uncomment the async function:

```typescript
// Replace the current getWarRoomData() with:
export async function fetchWarRoomData(): Promise<WarRoomData> {
  const response = await fetch('/api/warroom', {
    cache: 'no-store', // For real-time data
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch war room data');
  }
  
  return response.json();
}
```

### Step 3: Update Page Component
In `app/warloop/page.tsx`, update to use async fetching:

```typescript
'use client';

import { useState, useEffect } from 'react';
import { fetchWarRoomData, type WarRoomData } from './data';

export default function WarRoom() {
  const [data, setData] = useState<WarRoomData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const result = await fetchWarRoomData();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }

    loadData();
    
    // Optional: Set up polling for real-time updates
    const interval = setInterval(loadData, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!data) return <div>No data</div>;

  // ... rest of component
}
```

## Real-Time Updates (Optional)

For live updates, consider using:

### Option 1: Server-Sent Events (SSE)
```typescript
// app/api/warroom/stream/route.ts
export async function GET() {
  const encoder = new TextEncoder();
  
  const stream = new ReadableStream({
    async start(controller) {
      // Send updates periodically
      const interval = setInterval(async () => {
        const data = await getLatestWarRoomData();
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify(data)}\n\n`)
        );
      }, 1000);
      
      // Cleanup
      return () => clearInterval(interval);
    },
  });
  
  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}
```

### Option 2: WebSocket
Use libraries like `socket.io` or native WebSockets for bidirectional communication.

## Example API Response

```json
{
  "repository": {
    "owner": "stripe",
    "name": "stripe-ios",
    "status": "Active"
  },
  "stats": {
    "vulnsFound": 12,
    "autoFixed": 8,
    "pullRequests": 4,
    "systemUptime": "99.9%"
  },
  "agentLoopActive": true,
  "logs": [
    {
      "timestamp": "10:42:01",
      "agent": "ORCHESTRATOR",
      "message": "Initializing scan cycle #4922..."
    },
    {
      "timestamp": "10:42:05",
      "agent": "RED_AGENT",
      "message": "CRITICAL VULNERABILITY DETECTED (CWE-89)",
      "highlight": true
    }
  ]
}
```

## Current Implementation

Currently, the page uses `getWarRoomData()` which returns mock data from `MOCK_WAR_ROOM_DATA`. This allows the UI to work immediately while the backend is being developed.

To integrate with a real API:
1. Implement the API endpoint
2. Update the data fetching logic
3. Handle loading and error states
4. Consider implementing real-time updates
