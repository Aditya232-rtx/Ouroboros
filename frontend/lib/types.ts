export type Severity = "critical" | "high" | "medium" | "low" | "info";

export interface Finding {
  id: string;
  title: string;
  severity: Severity;
  description: string;
  cve?: string;
  cwe?: string;
  url?: string;
  evidence?: string;
  status?: "open" | "fixed" | "escalated";
}

export type ScanStatus = "idle" | "starting" | "running" | "completed" | "failed";
export type GatewayState = "disconnected" | "connecting" | "waiting_qr" | "connected" | "restarting";

export interface ScanSession {
  runId: string;
  url: string;
  status: ScanStatus;
  findings: Finding[];
}

export interface GatewaySession {
  state: GatewayState;
  phone: string | null;
  qrData: string | null;
}

/* ── Live agent graph (Fang / Strix) ── */

export interface TranscriptAgent {
  id: string;
  name: string;
  parent_id: string | null;
  status: string;
  task: string;
  skills: string[];
}

export interface TranscriptEvent {
  id: string;
  type: "chat" | "tool";
  agent_id: string;
  timestamp: string;
  version: number;
  data: Record<string, unknown>;
}

export interface Transcript {
  agents: TranscriptAgent[];
  events: TranscriptEvent[];
}

export interface AgentTodo {
  id: string;
  title: string;
  status: "pending" | "in_progress" | "done" | string;
  priority: string;
}

export interface AgentsState {
  agents: TranscriptAgent[];
  todos: Record<string, AgentTodo[]>;
}

export interface AgentGraphNode {
  id: string;
  name: string;
  task: string;
  status: "running" | "completed" | "failed" | "error" | "stopped";
  parentId: string | null;
  children: string[];
  toolCount: number;
  messageCount: number;
}

export interface ToolRendererProps {
  toolName: string;
  args: Record<string, unknown>;
  result: unknown;
  status: string;
}

export interface ResearchFinding {
  cve?: string;
  cwe?: string;
  component?: string;
  severity?: string;
  summary?: string;
}
