import React from "react";
import { useOpsPilot } from "../../context/OpsPilotContext";
import {
  Bell,
  Layers,
  Sparkles,
  Flame,
  ShieldCheck,
} from "lucide-react";

export const KpiSummaryBar: React.FC = () => {
  const { alerts, incidents, rca, remediation } = useOpsPilot();

  // Noise Reduction calculation
  const totalAlerts = alerts.length;
  const totalIncidents = incidents.length;
  const noiseReductionPercent =
    totalAlerts > 0
      ? (((totalAlerts - totalIncidents) / totalAlerts) * 100).toFixed(1)
      : "0.0";
  const rootService =
    rca?.root_cause_service ||
    incidents[0]?.correlation_evidence?.causal_chain?.[0]?.service ||
    (totalIncidents > 0 ? "Detecting..." : "None");

  const conditions = remediation?.safety_gate_result?.conditions;
  const passedChecks = conditions ? conditions.filter((c) => c.passed).length : 10;
  const totalChecks = conditions ? conditions.length : 10;
  const isGateEvaluated = !!remediation?.safety_gate_result;
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      {/* 1. Raw Alerts */}
      <div className="bg-surface-card border border-surface-border rounded-xl p-3 flex items-center justify-between shadow-subtle hover:border-surface-border-active transition-all">
        <div>
          <span className="text-[11px] font-medium text-slate-400 block">Raw Alerts</span>
          <div className="text-xl font-bold font-mono text-slate-100 mt-0.5">{totalAlerts}</div>
          <span className="text-[10px] text-rose-400 font-mono flex items-center gap-1 mt-0.5">
            <span className="w-1 h-1 rounded-full bg-rose-400"></span> Live Telemetry Stream
          </span>
        </div>
        <div className="w-8 h-8 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
          <Bell className="w-4 h-4" />
        </div>
      </div>

      {/* 2. Correlated Incidents */}
      <div className="bg-surface-card border border-surface-border rounded-xl p-3 flex items-center justify-between shadow-subtle hover:border-surface-border-active transition-all">
        <div>
          <span className="text-[11px] font-medium text-slate-400 block">Correlated Incidents</span>
          <div className="text-xl font-bold font-mono text-accent-sky mt-0.5">{totalIncidents}</div>
          <span className="text-[10px] text-slate-400 font-mono block mt-0.5">
            Topology Clustered
          </span>
        </div>
        <div className="w-8 h-8 rounded-lg bg-accent-sky/10 border border-accent-sky/20 flex items-center justify-center text-accent-sky">
          <Layers className="w-4 h-4" />
        </div>
      </div>

      {/* 3. Noise Compression */}
      <div className="bg-surface-card border border-surface-border rounded-xl p-3 flex items-center justify-between shadow-subtle hover:border-surface-border-active transition-all">
        <div>
          <span className="text-[11px] font-medium text-slate-400 block">Noise Compression</span>
          <div className="text-xl font-bold font-mono text-emerald-400 mt-0.5">{noiseReductionPercent}%</div>
          <span className="text-[10px] text-emerald-400/80 font-mono block mt-0.5">
            {totalAlerts} alerts → {totalIncidents} {totalIncidents === 1 ? "incident" : "incidents"}
          </span>
        </div>
        <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
          <Sparkles className="w-4 h-4" />
        </div>
      </div>

      {/* 4. Root Cause Origin */}
      <div className="bg-surface-card border border-amber-500/20 rounded-xl p-3 flex items-center justify-between shadow-subtle hover:border-amber-500/40 transition-all">
        <div>
          <span className="text-[11px] font-medium text-slate-400 block">Root-Side Origin</span>
          <div className="text-base font-bold font-mono text-amber-300 truncate max-w-[120px] mt-0.5">
            {rootService}
          </div>
          <span className="text-[10px] text-amber-400/90 font-mono block mt-0.5">
            {rca ? `${(rca.confidence_score * 100).toFixed(0)}% Confidence` : "Topology Root"}
          </span>
        </div>
        <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
          <Flame className="w-4 h-4" />
        </div>
      </div>

      {/* 5. Safety Gate Checks */}
      <div className="bg-surface-card border border-surface-border rounded-xl p-3 flex items-center justify-between shadow-subtle hover:border-surface-border-active transition-all col-span-2 sm:col-span-1">
        <div>
          <span className="text-[11px] font-medium text-slate-400 block">Safety Policy Gate</span>
          <div className="text-xl font-bold font-mono text-slate-100 mt-0.5">
            {isGateEvaluated ? `${passedChecks}/${totalChecks}` : "10 Rules"}
          </div>
          <span className="text-[10px] text-accent-purple font-mono block mt-0.5">
            {isGateEvaluated ? `Gate: ${remediation?.safety_gate_result?.decision || "Evaluated"}` : "Deterministic Matrix"}
          </span>
        </div>
        <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
          <ShieldCheck className="w-4 h-4" />
        </div>
      </div>
    </div>
  );
};
