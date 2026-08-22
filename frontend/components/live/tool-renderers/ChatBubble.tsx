"use client";

import { TruncatedText } from "./ToolCard";

const MAX_LINES = 30;

export default function ChatBubble({ role, content }: { role: string; content: string }) {
  const isUser = role === "user" || role === "human";

  return (
    <div
      style={{
        borderLeft: `2px solid ${isUser ? "rgba(96, 165, 250, 0.32)" : "rgba(192, 132, 252, 0.3)"}`,
        paddingLeft: "11px",
      }}
    >
      <span className={`font-semibold text-sm ${isUser ? "text-blue-400/80" : "text-purple-400/80"}`}>
        {isUser ? "User" : "Thinking"}
      </span>
      <div className="mt-1.5 italic text-[#888]">
        <TruncatedText text={content} maxLines={MAX_LINES} />
      </div>
    </div>
  );
}
