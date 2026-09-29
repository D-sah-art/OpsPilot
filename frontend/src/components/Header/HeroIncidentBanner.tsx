import React from "react";
import { useOpsPilot } from "../../context/OpsPilotContext";
import {
  AlertOctagon,
  Clock,
  Server,
  Layers,
  Flame,
  ArrowRight,
} from "lucide-react";

export const HeroIncidentBanner: React.FC = () => {
  const { selectedIncident, incidents, alerts, rca } = useOpsPilot();

  if (!selectedIncident) {
    return (
      <div className="bg-surface-card border border-surface-border rounded-xl p-3.5 flex items-center justify-between text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
          <span className="font-medium text-slate-200">System Normal</span>
          <span className="text-slate-500">• All upstream and downstream dependencies nominal</span>
        </div>
      </div>
    );
  }

  const alertCount = selectedIncident.alert_count || alerts.length;
  const timeSpan = selectedIncident.correlation_evidence?.temporal_span_seconds;
  const rootService =
    rca?.root_cause_service ||
    selectedIncident.correlation_evidence?.causal_chain?.[0]?.service ||
    "Detecting...";
  const affectedCount = selectedIncident.affected_services?.length || 0;

  return (
    <div className="relative bg-gradient-to-r from-rose-950/40 via-surface-card to-surface-card border border-rose-500/30 rounded-xl p-4 shadow-panel overflow-hidden">
      {/* Background subtle tint glow */}
      <div className="absolute top-0 left-0 w-32 h-full bg-gradient-to-r from-rose-500/10 to-transparent pointer-events-none" />

      <div className="relative flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Left: Active Live Badge & Incident Title */}
        <div className="space-y-1.5 max-w-3xl">
          <div className="flex items-center gap-2.5">
            {/* Live Indicator */}
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-rose-500/15 border border-rose-500/30 text-rose-300 text-[11px] font-semibold tracking-wide">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-400 animate-pulse"></span>
              <span>INCIDENT ACTIVE</span>
            </div>

            {/* Severity Pill */}
            <span className="px-2 py-0.5 rounded bg-rose-600/20 text-rose-300 border border-rose-500/40 text-[11px] font-mono font-bold uppercase">
              {selectedIncident.severity || "CRITICAL"}
            </span>

            {/* Status Pill */}
            <span className="px-2 py-0.5 rounded bg-surface-elevated text-slate-300 border border-surface-border text-[11px] font-mono">
              Status: {selectedIncident.status || "OPEN"}
            </span>

            {/* Incident ID */}
            <span className="text-[11px] font-mono text-slate-400 hidden sm:inline">
              {selectedIncident.incident_id}
            </span>
          </div>

          {/* Primary Title */}
          <h2 className="text-base sm:text-lg font-bold text-slate-100 tracking-tight leading-snug">
            {selectedIncident.title || "Active Incident Cluster"}
          </h2>
        </div>

        {/* Right: Quick Meta Stats Strip */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-3 text-xs font-mono">
          {/* Alerts in Incident */}
          <div className="bg-surface-elevated/80 border border-surface-border px-3 py-1.5 rounded-lg">
            <span className="text-slate-400 text-[10px] uppercase block leading-none">Cluster Volume</span>
            <span className="font-bold text-rose-400 text-sm">{alertCount} Alerts</span>
          </div>

          {/* Root-side Origin */}
          <div className="bg-surface-elevated/80 border border-amber-500/30 px-3 py-1.5 rounded-lg flex items-center gap-1.5">
            <div>
              <span className="text-amber-400/80 text-[10px] uppercase block leading-none flex items-center gap-1">
                <Flame className="w-2.5 h-2.5 text-amber-400" /> Root-Side
              </span>
              <span className="font-bold text-amber-300 text-sm">{rootService}</span>
            </div>
          </div>

          {/* Temporal Span */}
          <div className="bg-surface-elevated/80 border border-surface-border px-3 py-1.5 rounded-lg">
            <span className="text-slate-400 text-[10px] uppercase block leading-none">Cascade Duration</span>
            <span className="font-bold text-slate-200 text-sm">
              {timeSpan !== undefined ? `${timeSpan.toFixed(1)}s` : "—"}
            </span>
          </div>

          {/* Affected Services */}
          <div className="bg-surface-elevated/80 border border-surface-border px-3 py-1.5 rounded-lg">
            <span className="text-slate-400 text-[10px] uppercase block leading-none">Blast Radius</span>
            <span className="font-bold text-slate-200 text-sm">{affectedCount} Services</span>
          </div>
        </div>
      </div>
    </div>
  );
};
