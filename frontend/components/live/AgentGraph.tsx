"use client";

import { useCallback, useEffect, useRef } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  useReactFlow,
  type Node,
  type Edge,
} from "@xyflow/react";
import dagre from "@dagrejs/dagre";
import AgentNodeComponent from "./AgentNode";
import GraphSkeleton from "./GraphSkeleton";
import type { AgentGraphNode } from "@/lib/types";

import "@xyflow/react/dist/style.css";

const NODE_WIDTH = 300;
const NODE_HEIGHT = 92;
const ZOOM_DURATION = 300;

const nodeTypes = { agentNode: AgentNodeComponent };

function getLayoutedElements(agents: Map<string, AgentGraphNode>, selectedAgentId: string | null) {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", nodesep: 72, ranksep: 96 });

  const nodes: Node[] = [];
  const edges: Edge[] = [];

  for (const [id, agent] of agents) {
    g.setNode(id, { width: NODE_WIDTH, height: NODE_HEIGHT });
    nodes.push({
      id,
      type: "agentNode",
      position: { x: 0, y: 0 },
      data: { ...agent, isSelected: id === selectedAgentId },
    });

    if (agent.parentId && agents.has(agent.parentId)) {
      const edgeId = `${agent.parentId}->${id}`;
      g.setEdge(agent.parentId, id);
      edges.push({
        id: edgeId,
        source: agent.parentId,
        target: id,
        style: { stroke: "#8a7a52", strokeWidth: 1.5 },
      });
    }
  }

  dagre.layout(g);

  for (const node of nodes) {
    const pos = g.node(node.id);
    if (pos) {
      node.position = { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 };
    }
  }

  return { nodes, edges };
}

function CenterOnRoot({ nodes }: { nodes: Node[] }) {
  const { setCenter } = useReactFlow();
  const hasCentered = useRef(false);
  useEffect(() => {
    if (nodes.length > 0 && !hasCentered.current) {
      const root = nodes.find((n) => !(n.data as Record<string, unknown>).parentId);
      const target = root ?? nodes[0];
      hasCentered.current = true;
      const cx = target.position.x + NODE_WIDTH / 2;
      const cy = target.position.y + NODE_HEIGHT / 2;
      setTimeout(() => setCenter(cx, cy, { zoom: 0.85, duration: 400 }), 60);
    }
  }, [nodes, setCenter]);
  return null;
}

function SmoothControls() {
  const { zoomIn, zoomOut, fitView } = useReactFlow();
  return (
    <Controls
      position="bottom-right"
      showZoom={false}
      showFitView={false}
      showInteractive={false}
      className="!bg-transparent !border-none !shadow-none"
    >
      <div className="flex flex-col overflow-hidden rounded-lg border" style={{ borderColor: "#4a4530" }}>
        <button
          onClick={() => zoomIn({ duration: ZOOM_DURATION })}
          className="ouro-zoom-btn flex items-center justify-center w-8 h-8"
          style={{ background: "#1c2114", color: "#e9d494" }}
          title="Zoom in"
          aria-label="Zoom in"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
            <path d="M12 5v14M5 12h14" />
          </svg>
        </button>
        <button
          onClick={() => zoomOut({ duration: ZOOM_DURATION })}
          className="ouro-zoom-btn flex items-center justify-center w-8 h-8 border-y"
          style={{ background: "#1c2114", color: "#e9d494", borderColor: "#4a4530" }}
          title="Zoom out"
          aria-label="Zoom out"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
            <path d="M5 12h14" />
          </svg>
        </button>
        <button
          onClick={() => fitView({ padding: 0.3, duration: ZOOM_DURATION })}
          className="ouro-zoom-btn flex items-center justify-center w-8 h-8"
          style={{ background: "#1c2114", color: "#e9d494" }}
          title="Fit view"
          aria-label="Fit view to all agents"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
            <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
          </svg>
        </button>
      </div>
    </Controls>
  );
}

interface AgentGraphProps {
  agents: Map<string, AgentGraphNode>;
  selectedAgentId: string | null;
  onSelectAgent: (id: string | null) => void;
}

export default function AgentGraph({ agents, selectedAgentId, onSelectAgent }: AgentGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  useEffect(() => {
    if (agents.size === 0) return;
    const { nodes: ln, edges: le } = getLayoutedElements(agents, selectedAgentId);
    setNodes(ln);
    setEdges(le);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agents.size, setNodes, setEdges]);

  useEffect(() => {
    if (agents.size === 0) return;
    setNodes((nds) =>
      nds.map((n) => {
        const agent = agents.get(n.id);
        if (!agent) return n;
        return { ...n, data: { ...agent, isSelected: n.id === selectedAgentId } };
      })
    );
  }, [agents, selectedAgentId, setNodes]);

  const nodeClickedRef = useRef(false);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      nodeClickedRef.current = true;
      onSelectAgent(node.id);
    },
    [onSelectAgent]
  );

  const onPaneClick = useCallback(() => {
    if (nodeClickedRef.current) {
      nodeClickedRef.current = false;
      return;
    }
    onSelectAgent(null);
  }, [onSelectAgent]);

  // React Flow's node wrapper is tabbable (role="group") but doesn't wire
  // Enter/Space to activation by default — only mouse clicks reach
  // onNodeClick. Without this, a keyboard user can focus a node but never
  // open its transcript.
  const onGraphKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (e.key !== "Enter" && e.key !== " ") return;
      const nodeEl = (e.target as HTMLElement).closest<HTMLElement>("[data-id]");
      const nodeId = nodeEl?.dataset.id;
      if (!nodeId || !agents.has(nodeId)) return;
      e.preventDefault();
      onSelectAgent(nodeId);
    },
    [agents, onSelectAgent]
  );

  const showGraph = agents.size > 0;

  return (
    <div className="relative h-full">
      <div
        className={`absolute inset-0 z-10 transition-opacity duration-500 ${
          showGraph ? "opacity-0 pointer-events-none" : "opacity-100"
        }`}
      >
        <GraphSkeleton />
      </div>

      <div
        className={`h-full transition-opacity duration-500 ${showGraph ? "opacity-100" : "opacity-0"}`}
        onKeyDown={onGraphKeyDown}
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          nodeTypes={nodeTypes}
          nodesConnectable={false}
          edgesFocusable={false}
          edgesReconnectable={false}
          minZoom={0.15}
          maxZoom={1.5}
          proOptions={{ hideAttribution: true }}
          style={{ background: "#151810" }}
        >
          <Background color="#3a3624" gap={22} />
          <CenterOnRoot nodes={nodes} />
          <SmoothControls />
          <MiniMap
            position="bottom-left"
            nodeColor={(n) => {
              const status = (n.data as Record<string, unknown>)?.status as string;
              if (status === "running") return "#3b82f6";
              if (status === "completed") return "#10b981";
              if (status === "failed" || status === "error") return "#ef4444";
              return "#8a8060";
            }}
            maskColor="rgba(10, 12, 6, 0.82)"
            style={{ width: 96, height: 60, background: "#1c2114", border: "1px solid #4a4530" }}
          />
        </ReactFlow>
      </div>
    </div>
  );
}
