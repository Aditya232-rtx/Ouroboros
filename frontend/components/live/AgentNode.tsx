"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { AgentGraphNode } from "@/lib/types";

const STATUS_STYLES: Record<string, string> = {
  running: "bg-blue-500",
  completed: "bg-emerald-500",
  failed: "bg-red-500",
  error: "bg-red-500",
};

const STATUS_LABEL: Record<string, string> = {
  running: "running",
  completed: "completed",
  failed: "failed",
  error: "error",
  stopped: "idle",
};

function AgentNodeComponent({ data, selected }: NodeProps) {
  const agent = data as unknown as AgentGraphNode & { isSelected: boolean };
  const isSelected = agent.isSelected || selected;

  return (
    <div
      className="ouro-agent-node group w-[300px] rounded-xl px-4 py-3.5"
      style={{
        border: `1px solid ${isSelected ? "#e9d494" : "#4a4530"}`,
        background: isSelected ? "#20260f" : "#181c10",
        boxShadow: isSelected ? "0 0 22px rgba(233, 212, 148, 0.18)" : "none",
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        isConnectable={false}
        className={`!w-1.5 !h-1.5 !border-0 ${agent.parentId ? "!bg-[#6b6446]" : "!bg-transparent"}`}
      />

      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="relative flex h-2.5 w-2.5 shrink-0">
            <span
              className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${STATUS_STYLES[agent.status] ?? "bg-gray-500"} ${
                agent.status === "running" ? "animate-ping" : ""
              }`}
            />
            <span
              className={`relative inline-flex h-2.5 w-2.5 rounded-full ${STATUS_STYLES[agent.status] ?? "bg-gray-500"}`}
            />
          </span>
          <span
            className="text-[15px] font-semibold leading-snug line-clamp-2"
            style={{ color: "#fdf9ec", fontFamily: "var(--font-pixel)" }}
          >
            {agent.name}
          </span>
        </div>
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="#a89d78"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          className="w-3.5 h-3.5 shrink-0 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
          aria-hidden="true"
        >
          <path d="M7 17 17 7M7 7h10v10" />
        </svg>
      </div>

      <div className="mt-2 flex items-center gap-3 text-[11px]" style={{ color: "#a89d78" }}>
        <span className="capitalize">{STATUS_LABEL[agent.status] ?? agent.status}</span>
        {agent.toolCount > 0 && <span>{agent.toolCount} tool{agent.toolCount === 1 ? "" : "s"}</span>}
        {agent.messageCount > 0 && <span>{agent.messageCount} msg{agent.messageCount === 1 ? "" : "s"}</span>}
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        isConnectable={false}
        className={`!w-1.5 !h-1.5 !border-0 ${agent.children && agent.children.length > 0 ? "!bg-[#6b6446]" : "!bg-transparent"}`}
      />
    </div>
  );
}

export default memo(AgentNodeComponent);
