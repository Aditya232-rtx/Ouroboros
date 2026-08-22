"use client";

import { Component, useMemo, type ReactNode } from "react";
import { Brain, Bot } from "lucide-react";
import { getToolRenderer, getToolIcon } from "./tool-renderers";
import ChatBubble from "./tool-renderers/ChatBubble";
import type { ToolRendererProps, AgentGraphNode, TranscriptAgent, TranscriptEvent } from "@/lib/types";

class RendererErrorBoundary extends Component<{ toolName: string; children: ReactNode }, { hasError: boolean }> {
  constructor(props: { toolName: string; children: ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  render() {
    if (this.state.hasError) {
      return <span className="text-[#555] font-semibold text-sm">{this.props.toolName.replace(/_/g, " ")}</span>;
    }
    return this.props.children;
  }
}

function SafeToolRenderer(props: ToolRendererProps) {
  // getToolRenderer looks up a pre-defined component from a static registry —
  // it never creates a new component, just returns an existing reference.
  const Renderer = getToolRenderer(props.toolName);
  return (
    <RendererErrorBoundary toolName={props.toolName}>
      <Renderer {...props} />
    </RendererErrorBoundary>
  );
}

function asRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value)) return value as Record<string, unknown>;
  if (value == null) return {};
  return { __raw: typeof value === "string" ? value : JSON.stringify(value) };
}

function eventSeq(id: string): number {
  const m = /(\d+)$/.exec(id);
  return m ? parseInt(m[1], 10) : 0;
}

const STATUS_STYLE: Record<string, string> = {
  completed: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10",
  running: "text-blue-400 border-blue-500/30 bg-blue-500/10",
  stopped: "text-[#aaa] border-[#333] bg-[#1a1a1a]",
  failed: "text-red-400 border-red-500/30 bg-red-500/10",
};

function graphStatus(status: string): AgentGraphNode["status"] {
  if (status === "completed") return "completed";
  if (status === "running") return "running";
  if (status === "failed") return "failed";
  return status as AgentGraphNode["status"];
}

/** Adapt transcript agents + events into the Map<id, AgentGraphNode> the live graph renders. */
export function buildGraphAgents(agents: TranscriptAgent[], events: TranscriptEvent[]): Map<string, AgentGraphNode> {
  const childrenOf = new Map<string, string[]>();
  for (const a of agents) {
    if (a.parent_id) {
      const arr = childrenOf.get(a.parent_id) ?? [];
      arr.push(a.id);
      childrenOf.set(a.parent_id, arr);
    }
  }

  const toolCount = new Map<string, number>();
  const messageCount = new Map<string, number>();
  for (const e of events) {
    if (e.type === "tool") {
      toolCount.set(e.agent_id, (toolCount.get(e.agent_id) ?? 0) + 1);
    } else {
      messageCount.set(e.agent_id, (messageCount.get(e.agent_id) ?? 0) + 1);
    }
  }

  const map = new Map<string, AgentGraphNode>();
  for (const a of agents) {
    map.set(a.id, {
      id: a.id,
      name: a.name,
      task: a.task ?? "",
      status: graphStatus(a.status),
      parentId: a.parent_id,
      children: childrenOf.get(a.id) ?? [],
      toolCount: toolCount.get(a.id) ?? 0,
      messageCount: messageCount.get(a.id) ?? 0,
    });
  }
  return map;
}

export function AgentTranscript({
  agent,
  events,
  showHeader = true,
}: {
  agent: TranscriptAgent;
  events: TranscriptEvent[];
  showHeader?: boolean;
}) {
  const mine = useMemo(
    () => events.filter((e) => e.agent_id === agent.id).sort((a, b) => eventSeq(a.id) - eventSeq(b.id)),
    [events, agent.id]
  );

  const toolCount = mine.filter((e) => e.type === "tool").length;
  const msgCount = mine.length - toolCount;

  return (
    <div>
      {showHeader && (
        <>
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="text-base font-semibold text-white truncate">{agent.name}</span>
            <span
              className={`flex-shrink-0 text-xs font-medium capitalize px-2 py-0.5 rounded-full border ${
                STATUS_STYLE[agent.status] ?? "text-[#aaa] border-[#333] bg-[#1a1a1a]"
              }`}
            >
              {agent.status}
            </span>
            <span className="font-mono text-xs text-[#555]">{agent.id}</span>
          </div>
          <p className="text-xs text-[#666] mb-4">
            {msgCount} message{msgCount === 1 ? "" : "s"} · {toolCount} tool call{toolCount === 1 ? "" : "s"}
          </p>
        </>
      )}

      {mine.length === 0 ? (
        <p className="text-sm text-[#666]">No recorded activity for this agent.</p>
      ) : (
        <div className="py-1">
          {mine.map((event, i) => {
            const isLast = i === mine.length - 1;
            const isTool = event.type === "tool";
            const toolName = isTool ? String(event.data?.tool_name ?? "tool") : "";
            const role = !isTool ? String(event.data?.role ?? "assistant") : "";

            let Icon;
            let iconColor: string;
            if (isTool) {
              const meta = getToolIcon(toolName);
              Icon = meta.icon;
              iconColor = meta.color;
            } else {
              const isUser = role === "user" || role === "human";
              Icon = isUser ? Bot : Brain;
              iconColor = isUser ? "text-blue-400" : "text-purple-400";
            }

            const status = isTool ? String(event.data?.status ?? "completed") : "completed";

            return (
              <div key={event.id} className="flex gap-3">
                <div className="flex flex-col items-center shrink-0">
                  <div
                    className={`w-[30px] h-[30px] rounded-full bg-black border flex items-center justify-center shrink-0 ${
                      isTool && status === "running"
                        ? "border-blue-500/40 animate-pulse"
                        : isTool && status === "failed"
                          ? "border-red-500/30"
                          : "border-[#222]"
                    }`}
                  >
                    <Icon className={`w-3.5 h-3.5 ${iconColor}`} />
                  </div>
                  {!isLast && <div className="w-px flex-1 bg-[#1a1a1a] mt-1" />}
                </div>
                <div className="flex-1 min-w-0 pt-[5px] pb-6">
                  {isTool ? (
                    <SafeToolRenderer
                      toolName={toolName}
                      args={asRecord(event.data?.args)}
                      result={event.data?.result ?? null}
                      status={status}
                    />
                  ) : (
                    <ChatBubble role={role} content={String(event.data?.content ?? "")} />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
