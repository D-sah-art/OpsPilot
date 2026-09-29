import React, { useMemo, useEffect, useState, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  useReactFlow,
  ReactFlowProvider,
  type Node,
  type Edge,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { ServiceNode, type ServiceNodeData } from "./ServiceNode";
import { useOpsPilot } from "../../context/OpsPilotContext";
import { Network, Flame, Crosshair } from "lucide-react";

const nodeTypes = {
  serviceNode: ServiceNode,
};

const IGNORED_SERVICES = new Set(["chaos-engine", "chaos_engine", "test-runner", "probe-client", "redis-client"]);

interface TopologyFlowInnerProps {
  initialNodes: Node[];
  initialEdges: Edge[];
  fitTrigger: number;
}

const TopologyFlowInner: React.FC<TopologyFlowInnerProps> = ({
  initialNodes,
  initialEdges,
  fitTrigger,
}) => {
  const { fitView } = useReactFlow();
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Sync state when props change
  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  // Auto-fit view whenever nodes are updated or fitTrigger is clicked
  useEffect(() => {
    if (nodes.length > 0) {
      const timer = setTimeout(() => {
        fitView({ padding: 0.18, duration: 300 });
      }, 60);
      return () => clearTimeout(timer);
    }
  }, [nodes.length, fitTrigger, fitView]);

  return (
    <div className="flex-1 w-full h-full min-h-0 relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.18 }}
        minZoom={0.3}
        maxZoom={1.5}
        zoomOnScroll={false}
        panOnScroll={false}
        zoomOnPinch={true}
        panOnDrag={true}
        preventScrolling={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#1a2436" gap={18} size={1} />
        <Controls showInteractive={false} position="bottom-right" />
      </ReactFlow>
    </div>
  );
};

export const TopologyGraph: React.FC = () => {
  const { topology, alerts, selectedIncident, rca } = useOpsPilot();
  const [highlightCascade, setHighlightCascade] = useState<boolean>(true);
  const [fitTrigger, setFitTrigger] = useState<number>(0);

  // Compute alert count per service
  const alertCountMap = useMemo(() => {
    const map: Record<string, number> = {};
    alerts.forEach((alt) => {
      map[alt.service] = (map[alt.service] || 0) + 1;
    });
    return map;
  }, [alerts]);

  // Affected services set
  const affectedSet = useMemo(() => {
    return new Set(selectedIncident?.affected_services || []);
  }, [selectedIncident]);

  // Root cause service ID
  const rootCauseService =
    rca?.root_cause_service ||
    selectedIncident?.correlation_evidence?.causal_chain?.[0]?.service ||
    "";

  // Propagation path set
  const propagationPath = useMemo(() => {
    return rca?.propagation_path || [];
  }, [rca]);

  // Build React Flow Nodes & Edges dynamically from topology data
  const { initialNodes, initialEdges } = useMemo(() => {
    if (!topology || !topology.nodes) {
      return { initialNodes: [], initialEdges: [] };
    }

    // Filter out internal chaos / probe test actors
    const filteredNodes = topology.nodes.filter(
      (node) => !IGNORED_SERVICES.has(node.id.toLowerCase())
    );

    // Precise Left-to-Right DAG layout
    // Rank 0: Presentation (ShopFlow Frontend)
    // Rank 1: Edge (API Gateway)
    // Rank 2: Core Ingress (Checkout API, Product API, Auth Service)
    // Rank 3: Internal / Core (Order API, Redis Cache)
    // Rank 4: Data (PostgreSQL Database)
    const getColumnRank = (nodeId: string, tier?: string) => {
      const id = nodeId.toLowerCase();
      if (id.includes("frontend") || tier === "presentation") return 0;
      if (id.includes("gateway") || tier === "edge") return 1;
      if (id.includes("checkout") || id.includes("product") || id.includes("auth")) return 2;
      if (id.includes("order") || id.includes("redis") || id.includes("cache")) return 3;
      if (id.includes("postgres") || id.includes("db") || tier === "data") return 4;
      return 2;
    };

    // Group nodes by column
    const columns: Record<number, typeof filteredNodes> = { 0: [], 1: [], 2: [], 3: [], 4: [] };
    filteredNodes.forEach((node) => {
      const rank = getColumnRank(node.id, node.tier);
      if (!columns[rank]) columns[rank] = [];
      columns[rank].push(node);
    });

    const flowNodes: Node[] = [];
    const colXSpacing = 220;
    const rowYSpacing = 110;

    Object.entries(columns).forEach(([rankStr, nodesInCol]) => {
      const colIndex = parseInt(rankStr, 10);
      const totalInCol = nodesInCol.length;
      const startY = 40 + Math.max(0, (3 - totalInCol) * 45);

      nodesInCol.forEach((node, rowIndex) => {
        const isRoot = rootCauseService === node.id;
        const isAffected = affectedSet.has(node.id);
        const nodeAlerts = alertCountMap[node.id] || 0;

        flowNodes.push({
          id: node.id,
          type: "serviceNode",
          position: {
            x: 30 + colIndex * colXSpacing,
            y: startY + rowIndex * rowYSpacing,
          },
          data: {
            id: node.id,
            name: node.name || node.id,
            tier: node.tier,
            criticality: node.criticality,
            status: node.status,
            alertCount: nodeAlerts,
            isRootCause: isRoot,
            isAffected: isAffected,
          } as ServiceNodeData,
        });
      });
    });

    const activeNodeIds = new Set(flowNodes.map((n) => n.id));

    // Build flow edges, filtering out edges connected to excluded services
    const flowEdges: Edge[] = (topology.edges || [])
      .filter((edge) => activeNodeIds.has(edge.source) && activeNodeIds.has(edge.target))
      .map((edge, idx) => {
        const isCascadeEdge =
          highlightCascade &&
          propagationPath.length > 1 &&
          ((propagationPath.includes(edge.source) && propagationPath.includes(edge.target)) ||
            (affectedSet.has(edge.source) && affectedSet.has(edge.target)));

        return {
          id: `e-${edge.source}-${edge.target}-${idx}`,
          source: edge.source,
          target: edge.target,
          animated: isCascadeEdge,
          style: {
            stroke: isCascadeEdge ? "#f43f5e" : "#2a3b5c",
            strokeWidth: isCascadeEdge ? 2 : 1.2,
            opacity: isCascadeEdge ? 1.0 : 0.6,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: isCascadeEdge ? "#f43f5e" : "#3b82f6",
            width: 14,
            height: 14,
          },
          label: edge.observed && edge.confidence
            ? `${edge.protocol || "HTTP"} (${Math.round(edge.confidence * 100)}%)`
            : edge.protocol || undefined,
          labelStyle: { fill: isCascadeEdge ? "#f43f5e" : "#64748b", fontSize: 9, fontFamily: "monospace" },
          labelBgStyle: { fill: "#080c14", fillOpacity: 0.9 },
        };
      });

    return { initialNodes: flowNodes, initialEdges: flowEdges };
  }, [topology, alertCountMap, affectedSet, rootCauseService, propagationPath, highlightCascade]);

  const handleCenterView = useCallback(() => {
    setFitTrigger((prev) => prev + 1);
  }, []);

  return (
    <div className="bg-surface-card border border-surface-border rounded-xl overflow-hidden shadow-panel flex flex-col h-[520px]">
      {/* Topology Header */}
      <div className="px-4 py-3 border-b border-surface-border bg-surface-panel/80 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-md bg-accent-sky/10 border border-accent-sky/20 text-accent-sky">
            <Network className="w-3.5 h-3.5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-semibold text-slate-100">
                Live Dependency Topology
              </h3>
              {topology?.source === "discovered" ? (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/50 text-emerald-300 border border-emerald-800/60 flex items-center gap-1 font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  DYNAMICALLY DISCOVERED
                </span>
              ) : (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-elevated text-slate-400 border border-surface-border font-normal">
                  CONFIGURED FALLBACK
                </span>
              )}
              {topology?.grafana_connected ? (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-950/40 text-amber-300 border border-amber-800/50">
                  Grafana: Connected
                </span>
              ) : (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900/80 text-slate-500 border border-surface-border">
                  Grafana: Offline (Safe)
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-400 font-mono mt-0.5">
              Source: {topology?.discovery_source || "Configured Topology"} • {initialNodes.length} Nodes • {initialEdges.length} Edges
              {topology?.evidence?.average_edge_confidence ? ` • Avg Conf: ${Math.round(topology.evidence.average_edge_confidence * 100)}%` : ""}
            </p>
          </div>
        </div>

        {/* Legend & Controls */}
        <div className="flex items-center gap-2.5 text-xs font-mono">
          <button
            onClick={handleCenterView}
            title="Center and fit topology graph in view"
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs bg-surface-elevated text-slate-300 border-surface-border hover:border-slate-500 hover:text-white transition-all shadow-sm"
          >
            <Crosshair className="w-3 h-3 text-accent-sky" />
            <span>Center View</span>
          </button>

          <button
            onClick={() => setHighlightCascade((prev) => !prev)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs transition-all ${
              highlightCascade
                ? "bg-rose-950/30 text-rose-300 border-rose-800/50"
                : "bg-surface-elevated text-slate-400 border-surface-border"
            }`}
          >
            <Flame className="w-3 h-3 text-rose-400" />
            <span>Cascade Flow</span>
          </button>

          <div className="hidden xl:flex items-center gap-2.5 text-[11px] text-slate-400 border-l border-surface-border pl-3">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded bg-amber-400"></span> Root-Side
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded bg-rose-500"></span> Cascaded
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded bg-emerald-400"></span> Nominal
            </span>
          </div>
        </div>
      </div>

      {/* React Flow Canvas wrapped in ReactFlowProvider */}
      <ReactFlowProvider>
        <TopologyFlowInner
          initialNodes={initialNodes}
          initialEdges={initialEdges}
          fitTrigger={fitTrigger}
        />
      </ReactFlowProvider>
    </div>
  );
};
