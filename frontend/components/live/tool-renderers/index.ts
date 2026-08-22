import type { ComponentType } from "react";
import type { ToolRendererProps } from "@/lib/types";
import { Terminal, Brain, Bot, ListTodo, Wrench, StickyNote } from "lucide-react";

import TerminalRenderer from "./TerminalRenderer";
import ThinkRenderer from "./ThinkRenderer";
import AgentCommsRenderer from "./AgentCommsRenderer";
import TodoRenderer from "./TodoRenderer";
import FallbackRenderer from "./FallbackRenderer";

/**
 * Tool-renderer mapping — mirrors Fang's own registry, scoped to the tool
 * families our real Strix runs actually emit (exec_command, think, create_agent,
 * todos, notes). Anything unrecognized falls back to a generic name+args+result
 * dump so the transcript never breaks on a new tool name.
 */

export type ToolCategory = "terminal" | "thinking" | "agents" | "todos" | "notes" | "other";

export interface ToolIconMeta {
  icon: ComponentType<{ className?: string }>;
  color: string;
}

interface CategoryMeta {
  renderer: ComponentType<ToolRendererProps>;
  icon: ComponentType<{ className?: string }>;
  color: string;
  match?: RegExp;
}

const CATEGORY_META: Record<ToolCategory, CategoryMeta> = {
  terminal: { renderer: TerminalRenderer, icon: Terminal, color: "text-emerald-400" },
  thinking: { renderer: ThinkRenderer, icon: Brain, color: "text-purple-400" },
  agents: { renderer: AgentCommsRenderer, icon: Bot, color: "text-cyan-400", match: /agent/ },
  todos: { renderer: TodoRenderer, icon: ListTodo, color: "text-purple-400", match: /todo/ },
  notes: { renderer: FallbackRenderer, icon: StickyNote, color: "text-amber-400", match: /note/ },
  other: { renderer: FallbackRenderer, icon: Wrench, color: "text-[#555]" },
};

const CATEGORY_TOOLS: Record<ToolCategory, readonly string[]> = {
  terminal: ["exec_command", "write_stdin", "terminal_execute"],
  thinking: ["think"],
  agents: ["create_agent", "agent_finish", "send_message_to_agent", "wait_for_agents", "view_agent_graph", "stop_agent"],
  todos: ["create_todo", "list_todos", "update_todo", "todo_update", "mark_todo_done", "mark_todo_pending", "mark_todo_in_progress", "delete_todo"],
  notes: ["create_note", "delete_note", "update_note", "list_notes", "get_note"],
  other: [],
};

const TOOL_CATEGORY: Record<string, ToolCategory> = Object.fromEntries(
  (Object.entries(CATEGORY_TOOLS) as [ToolCategory, readonly string[]][]).flatMap(([category, names]) =>
    names.map((name) => [name, category] as const)
  )
);

const FALLBACK_META: CategoryMeta = CATEGORY_META.other;

function resolveCategory(toolName: string): ToolCategory | null {
  const direct = TOOL_CATEGORY[toolName];
  if (direct) return direct;
  for (const [category, meta] of Object.entries(CATEGORY_META) as [ToolCategory, CategoryMeta][]) {
    if (meta.match?.test(toolName)) return category;
  }
  return null;
}

export function getToolRenderer(toolName: string): ComponentType<ToolRendererProps> {
  const category = resolveCategory(toolName);
  return category ? CATEGORY_META[category].renderer : FallbackRenderer;
}

export function getToolIcon(toolName: string): ToolIconMeta {
  const category = resolveCategory(toolName);
  const meta = category ? CATEGORY_META[category] : FALLBACK_META;
  return { icon: meta.icon, color: meta.color };
}
