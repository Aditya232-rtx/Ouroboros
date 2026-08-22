"use client";

import type { ToolRendererProps } from "@/lib/types";
import { TruncatedText } from "./ToolCard";

export default function AgentCommsRenderer({ toolName, args }: ToolRendererProps) {
  if (toolName === "create_agent") {
    const name = (args.name as string) ?? (args.agent_name as string) ?? "";
    const task = (args.task as string) ?? "";
    return (
      <div className="ouro-tool-agents">
        <div className="flex items-center gap-2">
          <span className="text-cyan-400/80 font-semibold text-sm">spawning</span>
          {name && <span className="text-cyan-400 font-semibold text-sm">{name}</span>}
        </div>
        {task && (
          <div className="mt-1.5">
            <TruncatedText text={task} maxLines={15} />
          </div>
        )}
      </div>
    );
  }

  if (toolName === "wait_for_agents") {
    const reason = (args.reason as string) ?? "";
    return (
      <div className="ouro-tool-agents flex items-center gap-2">
        <span className="text-cyan-400/80 font-semibold text-sm">waiting</span>
        {reason && <span className="text-[#888] text-[13px] truncate">{reason}</span>}
      </div>
    );
  }

  if (toolName === "view_agent_graph") {
    return (
      <div className="ouro-tool-agents">
        <span className="text-cyan-400/80 font-semibold text-sm">viewing agents graph</span>
      </div>
    );
  }

  return (
    <div className="ouro-tool-agents">
      <span className="text-cyan-400/80 font-semibold text-sm">{toolName.replace(/_/g, " ")}</span>
    </div>
  );
}
