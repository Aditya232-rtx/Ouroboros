"use client";

import type { ToolRendererProps } from "@/lib/types";
import { CodeBlock } from "./ToolCard";

const MAX_OUTPUT_LINES = 50;
const MAX_LINE_LENGTH = 200;
const HEAD = 25;
const TAIL = 24;

function truncateLine(line: string): string {
  if (line.length > MAX_LINE_LENGTH) return line.slice(0, MAX_LINE_LENGTH - 3) + "...";
  return line;
}

const CHUNK_PREAMBLE_START = /^Chunk ID: [0-9a-f]+\s*$/;
const CHUNK_PREAMBLE_METADATA: RegExp[] = [
  /^Wall time: [\d.]+ seconds\s*$/,
  /^Process exited with code -?\d+\s*$/,
  /^Process running with session ID \d+\s*$/,
  /^Original token count: \d+\s*$/,
];

function stripChunkPreambles(lines: string[]): string[] {
  const out: string[] = [];
  for (let i = 0; i < lines.length; i++) {
    if (CHUNK_PREAMBLE_START.test(lines[i])) {
      let j = i + 1;
      while (j < lines.length && CHUNK_PREAMBLE_METADATA.some((p) => p.test(lines[j]))) j++;
      if (j < lines.length && lines[j].trim() === "Output:") j++;
      i = j - 1;
      continue;
    }
    out.push(lines[i]);
  }
  return out;
}

function cleanOutput(raw: string): string {
  const stripped = raw.replace(/\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])/g, "").replace(/\r/g, "");
  return stripChunkPreambles(stripped.split("\n")).join("\n").trim();
}

function formatOutput(output: string): string {
  const lines = output.split("\n");
  if (lines.length <= MAX_OUTPUT_LINES) return lines.map(truncateLine).join("\n");
  const hiddenCount = lines.length - HEAD - TAIL;
  return [
    ...lines.slice(0, HEAD).map(truncateLine),
    `... ${hiddenCount} lines truncated ...`,
    ...lines.slice(-TAIL).map(truncateLine),
  ].join("\n");
}

export default function TerminalRenderer({ toolName, args, result }: ToolRendererProps) {
  const isStdin = toolName === "write_stdin";
  const command = isStdin
    ? ((args.chars as string) ?? (args.input as string) ?? "")
    : ((args.command as string) ?? (args.cmd as string) ?? "");

  const res = result as Record<string, unknown> | string | null;
  let content: string | null = null;
  let error: string | null = null;
  let exitCode: number | null = null;

  if (res && typeof res === "object") {
    content = typeof res.content === "string" ? res.content : null;
    error = typeof res.error === "string" ? res.error : null;
    exitCode = typeof res.exit_code === "number" ? res.exit_code : null;
  } else if (typeof res === "string") {
    content = res;
  }

  const output = content ? formatOutput(cleanOutput(content)) : null;

  return (
    <div className="ouro-tool-terminal">
      <span className="text-emerald-400/80 font-semibold text-sm">{isStdin ? "Terminal input" : "Terminal"}</span>
      {command && <CodeBlock className="text-emerald-300/80">{command}</CodeBlock>}
      {error && <CodeBlock className="text-red-400/70">{error}</CodeBlock>}
      {output && <CodeBlock className="text-[#666]">{output}</CodeBlock>}
      {exitCode != null && exitCode !== 0 && (
        <div className="font-mono text-[13px] text-red-400/70 mt-0.5">exit code {exitCode}</div>
      )}
    </div>
  );
}
