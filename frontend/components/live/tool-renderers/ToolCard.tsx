"use client";

import { useState, type ReactNode } from "react";

const OUTPUT_PREVIEW_LINES = 6;

/** Truncatable plain text with "Show more" */
export function TruncatedText({ text, maxLines = 20 }: { text: string; maxLines?: number }) {
  const [expanded, setExpanded] = useState(false);
  const lines = text.trimEnd().split("\n");
  const needsTruncation = lines.length > maxLines;

  return (
    <div>
      <div
        className={expanded && needsTruncation ? "max-h-[1200px] overflow-auto" : ""}
        style={
          !expanded && needsTruncation
            ? { display: "-webkit-box", WebkitLineClamp: maxLines, WebkitBoxOrient: "vertical", overflow: "hidden" }
            : undefined
        }
      >
        <p className="whitespace-pre-wrap break-words text-[13px] leading-relaxed">{text}</p>
      </div>
      {needsTruncation && (
        <button onClick={() => setExpanded(!expanded)} className="text-xs text-[#555] hover:text-[#888] mt-1">
          {expanded ? "Show less" : "Show more"}
        </button>
      )}
    </div>
  );
}

/** Code/output block — truncates to a few lines with "Show more" */
export function CodeBlock({ children, className = "" }: { children: ReactNode; className?: string }) {
  const [expanded, setExpanded] = useState(false);

  const isString = typeof children === "string";
  const lines = isString ? (children as string).trimEnd().split("\n") : null;
  const needsTruncation = lines !== null && lines.length > OUTPUT_PREVIEW_LINES;
  const displayContent = needsTruncation && !expanded ? lines!.slice(0, OUTPUT_PREVIEW_LINES).join("\n") : children;

  return (
    <div>
      <pre
        className={`font-mono text-[13px] leading-relaxed whitespace-pre-wrap break-words mt-1 ${
          expanded ? "overflow-auto max-h-[1200px]" : "overflow-hidden"
        } ${className}`}
      >
        {displayContent}
      </pre>
      {needsTruncation && (
        <button onClick={() => setExpanded(!expanded)} className="text-xs text-[#555] hover:text-[#888] mt-0.5">
          {expanded ? "Show less" : "Show more"}
        </button>
      )}
    </div>
  );
}
