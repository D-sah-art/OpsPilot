import React from "react";
import { useOpsPilot } from "../../context/OpsPilotContext";
import {
  Clock,
  Network,
  TrendingDown,
  ArrowDown,
  ArrowRight,
  AlertTriangle,
} from "lucide-react";

export const CorrelationEvidence: React.FC = () => {
  const { selectedIncident } = useOpsPilot();

  if (!selectedIncident || !selectedIncident.correlation_evidence) {
    return (
      <div className="bg-surface-card border border-surface-border rounded-xl p-4 text-center text-slate-500 font-mono text-xs">
        Select an incident to view correlation evidence.
      </div>
    );
  }

  const evidence = selectedIncident.correlation_evidence;
  const causalChain = evidence.causal_chain || [];
  const dependencyPaths = evidence.dependency_paths || [];
  const alertTypes = evidence.alert_type_breakdown || {};

  return (
    <div className="bg-surface-card border border-surface-border rounded-xl overflow-hidden shadow-panel flex flex-col">
      {/* Header */}
      <div className="px-4 py-2.5 border-b border-surface-border bg-surface-panel/80 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Network className="w-3.5 h-3.5 text-accent-sky" />
          <h3 className="text-xs font-semibold text-slate-100">
            Temporal & Causal Chain
          </h3>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-400">
          <Clock className="w-3 h-3 text-accent-sky" />
          <span>Span: {evidence.temporal_span_seconds !== undefined ? `${evidence.temporal_span_seconds.toFixed(1)}s` : "—"}</span>
        </div>
      </div>

      <div className="p-3.5 space-y-3">
        {/* Vertical Causal Progression Flow */}
        <div className="space-y-1.5">
          {causalChain.length > 0 ? (
            causalChain.slice(0, 4).map((step, idx) => (
              <div key={idx} className="relative">
                <div className="flex items-center justify-between bg-surface-panel/90 border border-surface-border rounded-lg p-2 text-xs">
                  <div className="flex items-center gap-2.5">
                    <span className="w-5 h-5 rounded bg-surface-elevated border border-surface-border text-accent-sky font-mono font-bold text-[10px] flex items-center justify-center shrink-0">
                      T{idx}
                    </span>
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-slate-100 font-semibold font-mono text-xs">
                          {step.service || "service"}
                        </span>
                        <span className="text-slate-400 font-mono text-[10px]">
                          ({step.alert_type || step.metric || "alert"})
                        </span>
                      </div>
                    </div>
                  </div>

                  <span
                    className={`text-[9px] font-mono font-bold px-1.5 py-0.2 rounded uppercase ${
                      step.severity === "CRITICAL"
                        ? "bg-rose-500/15 text-rose-300 border border-rose-500/30"
                        : "bg-amber-500/15 text-amber-300 border border-amber-500/30"
                    }`}
                  >
                    {step.severity || "CRITICAL"}
                  </span>
                </div>

                {/* Down connector arrow */}
                {idx < Math.min(causalChain.length - 1, 3) && (
                  <div className="flex justify-center my-0.5">
                    <ArrowDown className="w-3 h-3 text-rose-500/60 animate-pulse" />
                  </div>
                )}
              </div>
            ))
          ) : (
            <div className="text-xs text-slate-500 font-mono">
              Single tier or aggregate event set.
            </div>
          )}

          {/* Customer Impact Terminal Node */}
          {causalChain.length >= 4 && (
            <div className="pt-1">
              <div className="flex items-center justify-between bg-rose-950/20 border border-rose-500/30 rounded-lg p-2 text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-rose-500"></span>
                  <span className="font-semibold text-rose-300 text-xs">Customer Impact</span>
                  <span className="text-slate-400 text-[10px] font-mono">Checkout Degraded (504)</span>
                </div>
                <span className="text-[9px] font-mono font-bold px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-300 uppercase">
                  CRITICAL
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Validated Dependency Path Breadcrumbs */}
        {dependencyPaths.length > 0 && (
          <div className="pt-2 border-t border-surface-border">
            <span className="text-[10px] text-slate-400 font-mono uppercase block mb-1">
              Validated Dependency Path
            </span>
            <div className="bg-surface-panel border border-surface-border rounded-lg p-2 flex flex-wrap items-center gap-1.5 text-xs font-mono">
              {dependencyPaths[0].map((node, i) => (
                <React.Fragment key={node}>
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] ${
                      i === dependencyPaths[0].length - 1
                        ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold"
                        : "bg-surface-elevated text-slate-300 border border-surface-border"
                    }`}
                  >
                    {node}
                  </span>
                  {i < dependencyPaths[0].length - 1 && (
                    <ArrowRight className="w-2.5 h-2.5 text-accent-sky" />
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>
        )}

        {/* Alert Types Breakdown */}
        <div className="pt-2 border-t border-surface-border">
          <span className="text-[10px] text-slate-400 font-mono uppercase block mb-1">
            Dominant Alert Signatures
          </span>
          <div className="flex flex-wrap gap-1">
            {Object.entries(alertTypes)
              .slice(0, 5)
              .map(([type, count]) => (
                <span
                  key={type}
                  className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-surface-panel border border-surface-border text-slate-300 flex items-center gap-1"
                >
                  <span>{type}:</span>
                  <span className="text-accent-sky font-bold">{count}</span>
                </span>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
};
