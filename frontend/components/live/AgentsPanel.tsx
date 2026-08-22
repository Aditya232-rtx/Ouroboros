"use client";

import { useEffect, useRef, useState } from "react";
import AgentGraph from "./AgentGraph";
import { AgentDetailModal } from "./AgentDetailModal";
import { buildGraphAgents } from "./AgentTranscript";
import { getScanTranscript } from "@/lib/api";
import type { TranscriptAgent, TranscriptEvent, AgentGraphNode } from "@/lib/types";
import "./live.css";

const POLL_MS = 1500;

interface AgentsPanelProps {
  runId: string | null;
  /** Enlarged full-height mode while recon is running vs. the compact card once findings arrive. */
  large?: boolean;
  /** Reports live agents + events on every poll so the parent dashboard can derive real stats from the same data, without a second poll loop. */
  onUpdate?: (data: { agents: TranscriptAgent[]; graphAgents: Map<string, AgentGraphNode> }) => void;
}

export default function AgentsPanel({ runId, large = false, onUpdate }: AgentsPanelProps) {
  const [agents, setAgents] = useState<TranscriptAgent[]>([]);
  const [events, setEvents] = useState<TranscriptEvent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stoppedRef = useRef(false);
  const onUpdateRef = useRef(onUpdate);
  onUpdateRef.current = onUpdate;

  useEffect(() => {
    stoppedRef.current = false;
    setAgents([]);
    setEvents([]);
    setSelectedAgentId(null);
    if (!runId) return;

    async function poll() {
      try {
        const data = await getScanTranscript(runId!);
        if (stoppedRef.current) return;
        setAgents(data.agents);
        setEvents(data.events);
        onUpdateRef.current?.({ agents: data.agents, graphAgents: buildGraphAgents(data.agents, data.events) });
      } catch {
        // transient — keep polling
      }
      if (!stoppedRef.current) {
        pollRef.current = setTimeout(poll, POLL_MS);
      }
    }
    poll();

    return () => {
      stoppedRef.current = true;
      if (pollRef.current) clearTimeout(pollRef.current);
    };
  }, [runId]);

  const graphAgents = buildGraphAgents(agents, events);
  const selectedAgent = agents.find((a) => a.id === selectedAgentId) ?? null;

  return (
    <div
      className="ouro-agents-panel glass"
      style={{ height: large ? "86vh" : "520px" }}
    >
      <div className="ouro-agents-panel__header">
        <span className="ouro-agents-panel__dot">
          <span className="ouro-agents-panel__dot-ping" />
          <span className="ouro-agents-panel__dot-core" />
        </span>
        <span className="ouro-agents-panel__label">Fang Agents Live</span>
      </div>
      <AgentGraph agents={graphAgents} selectedAgentId={selectedAgentId} onSelectAgent={setSelectedAgentId} />
      <AgentDetailModal
        open={selectedAgentId !== null}
        agent={selectedAgent}
        events={events}
        onClose={() => setSelectedAgentId(null)}
      />
    </div>
  );
}
