import React, { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import {
  Database,
  Server,
  Globe,
  Bell,
  CheckCircle2,
  AlertTriangle,
  Flame,
  Shield,
  Layers,
} from "lucide-react";

export interface ServiceNodeData {
  id: string;
  name: string;
  type?: string;
  tier?: string;
  criticality?: string;
  status?: string;
  alertCount?: number;
  isRootCause?: boolean;
  isAffected?: boolean;
  isCascadePath?: boolean;
  [key: string]: unknown;
}

export const ServiceNode: React.FC<NodeProps> = memo(({ data }) => {
  const nodeData = data as ServiceNodeData;
  const isRoot = nodeData.isRootCause;
  const isAffected = nodeData.isAffected;
  const alertCount = nodeData.alertCount || 0;

  // Icon based on type/id
  const getIcon = () => {
    const id = nodeData.id?.toLowerCase() || "";
    if (id.includes("db") || id.includes("postgres") || nodeData.tier === "data") {
      return <Database className="w-4 h-4 text-amber-400" />;
    }
    if (id.includes("gateway") || nodeData.tier === "edge") {
      return <Globe className="w-4 h-4 text-accent-sky" />;
    }
    if (id.includes("frontend") || nodeData.tier === "presentation") {
      return <Layers className="w-4 h-4 text-slate-300" />;
    }
    if (id.includes("auth") || id.includes("security")) {
      return <Shield className="w-4 h-4 text-accent-purple" />;
    }
    return <Server className="w-4 h-4 text-blue-400" />;
  };

  return (
    <div
      className={`relative px-3.5 py-2.5 rounded-xl border transition-all duration-200 min-w-[170px] backdrop-blur-md shadow-sm ${
        isRoot
          ? "bg-surface-card border-amber-500/80 shadow-halo-amber ring-2 ring-amber-500/20"
          : isAffected
          ? "bg-surface-card border-rose-500/60 shadow-sm"
          : "bg-surface-card/90 border-surface-border hover:border-slate-600"
      }`}
    >
      {/* Target Handle (Incoming Calls) */}
      <Handle
        type="target"
        position={Position.Left}
        className="w-2 h-2 !bg-accent-sky !border-surface-bg"
      />
      {/* Source Handle (Outgoing Dependencies) */}
      <Handle
        type="source"
        position={Position.Right}
        className="w-2 h-2 !bg-accent-blue !border-surface-bg"
      />

      {/* Root Cause Tag Badge */}
      {isRoot && (
        <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded-full bg-amber-500 text-slate-950 text-[9px] font-bold tracking-wider font-mono uppercase shadow-sm flex items-center gap-1">
          <Flame className="w-2.5 h-2.5 fill-slate-950 text-slate-950" />
          <span>Root-Side Origin</span>
        </div>
      )}

      {/* Node Header */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-surface-elevated border border-surface-border">
            {getIcon()}
          </div>
          <div>
            <div className="text-xs font-semibold text-slate-100 font-sans truncate max-w-[105px]">
              {nodeData.name || nodeData.id}
            </div>
            <div className="text-[10px] text-slate-400 font-mono uppercase">
              {nodeData.tier || "service"}
            </div>
          </div>
        </div>

        {/* Live Status Dot */}
        <div>
          {isRoot ? (
            <span className="flex h-2.5 w-2.5 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-400"></span>
            </span>
          ) : isAffected ? (
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
            </span>
          ) : (
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-400"></span>
          )}
        </div>
      </div>

      {/* Node Footer */}
      <div className="mt-2 pt-1.5 border-t border-surface-border flex items-center justify-between text-[10px] font-mono">
        <span className="text-slate-400 capitalize">
          {nodeData.criticality || "core"}
        </span>

        {alertCount > 0 ? (
          <span className="px-1.5 py-0.2 rounded bg-rose-500/15 border border-rose-500/30 text-rose-300 font-bold flex items-center gap-1">
            <Bell className="w-2.5 h-2.5" />
            <span>{alertCount}</span>
          </span>
        ) : (
          <span className="text-emerald-400 flex items-center gap-0.5">
            <CheckCircle2 className="w-2.5 h-2.5" /> OK
          </span>
        )}
      </div>
    </div>
  );
});

ServiceNode.displayName = "ServiceNode";
