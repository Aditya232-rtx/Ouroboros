import type { ToolRendererProps } from "@/lib/types";
import { CodeBlock } from "./ToolCard";

function pretty(value: unknown): string | null {
  if (value == null) return null;
  if (typeof value === "string") return value.trim() ? value : null;
  if (typeof value === "object") {
    const rec = value as Record<string, unknown>;
    if (Object.keys(rec).length === 0) return null;
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  }
  return String(value);
}

export default function FallbackRenderer({ toolName, args, result }: ToolRendererProps) {
  const argsText = pretty(args);
  const resultText = pretty(result);
  return (
    <div className="ouro-tool-generic">
      <span className="text-[#888] font-semibold text-sm">{toolName.replace(/_/g, " ")}</span>
      {argsText && <CodeBlock className="text-[#777]">{argsText}</CodeBlock>}
      {resultText && <CodeBlock className="text-[#666]">{resultText}</CodeBlock>}
    </div>
  );
}
