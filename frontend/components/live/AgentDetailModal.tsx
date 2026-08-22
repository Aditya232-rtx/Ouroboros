"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import { AgentTranscript } from "./AgentTranscript";
import type { TranscriptAgent, TranscriptEvent } from "@/lib/types";

const STATUS_DOT: Record<string, string> = {
  completed: "bg-emerald-400",
  running: "bg-blue-400",
  stopped: "bg-[#888]",
  failed: "bg-red-400",
};

const NEAR_BOTTOM_PX = 80;

export function AgentDetailModal({
  open,
  agent,
  events,
  onClose,
}: {
  open: boolean;
  agent: TranscriptAgent | null;
  events: TranscriptEvent[];
  onClose: () => void;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const nearBottom = useRef(false);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const previouslyFocusedRef = useRef<HTMLElement | null>(null);

  const [render, setRender] = useState(open);
  const [state, setState] = useState<"open" | "closed">(open ? "open" : "closed");
  const [contentReady, setContentReady] = useState(false);

  const lastAgentRef = useRef<TranscriptAgent | null>(agent);
  useEffect(() => {
    if (agent) lastAgentRef.current = agent;
  }, [agent]);
  const shownAgent = agent ?? lastAgentRef.current;

  useEffect(() => {
    if (open) {
      previouslyFocusedRef.current = document.activeElement as HTMLElement | null;
      setRender(true);
      setState("open");
      return;
    }
    setState("closed");
    const t = setTimeout(() => {
      setRender(false);
      previouslyFocusedRef.current?.focus?.();
    }, 140);
    return () => clearTimeout(t);
  }, [open]);

  // Move focus into the dialog once it's mounted and painted.
  useEffect(() => {
    if (!open || !render) return;
    const id = requestAnimationFrame(() => closeButtonRef.current?.focus());
    return () => cancelAnimationFrame(id);
  }, [open, render]);

  useEffect(() => {
    if (!render) {
      setContentReady(false);
      return;
    }
    const id = requestAnimationFrame(() => setContentReady(true));
    return () => cancelAnimationFrame(id);
  }, [render]);

  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    nearBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_PX;
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el || !nearBottom.current) return;
    requestAnimationFrame(() => {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    });
  }, [events]);

  useEffect(() => {
    if (!render) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [render, onClose]);

  if (!render || !shownAgent) return null;

  return (
    <div
      data-state={state}
      className="agent-modal fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 sm:p-8"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`Agent ${shownAgent.name}`}
    >
      <div
        className="agent-modal__panel relative flex h-[68vh] w-[calc(100vw-4rem)] max-w-6xl flex-col overflow-hidden rounded-xl shadow-2xl"
        style={{ border: "1px solid #4a4530", background: "#161a0f" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-3 px-5 py-3" style={{ borderBottom: "1px solid #3a3624" }}>
          <div className="flex min-w-0 items-center gap-2">
            <span className={`h-2 w-2 flex-shrink-0 rounded-full ${STATUS_DOT[shownAgent.status] ?? "bg-[#888]"}`} />
            <span className="truncate text-sm font-semibold" style={{ color: "#fdf9ec", fontFamily: "var(--font-pixel)" }}>
              {shownAgent.name}
            </span>
            <span className="flex-shrink-0 font-mono text-xs" style={{ color: "#a89d78" }}>{shownAgent.id}</span>
          </div>
          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            aria-label="Close agent transcript"
            className="agent-modal__close flex-shrink-0 flex items-center justify-center w-11 h-11 rounded-md"
            style={{ color: "#a89d78" }}
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div ref={scrollRef} onScroll={handleScroll} className="flex-1 overflow-y-auto p-5">
          {contentReady && <AgentTranscript agent={shownAgent} events={events} showHeader={false} />}
        </div>
      </div>
    </div>
  );
}

export default AgentDetailModal;
