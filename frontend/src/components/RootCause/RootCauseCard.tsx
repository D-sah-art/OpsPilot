import React, { useState } from "react";
import { useOpsPilot } from "../../context/OpsPilotContext";
import { ConfidenceBreakdown } from "./ConfidenceBreakdown";
import {
  Target,
  Brain,
  ArrowRight,
  RefreshCw,
  SlidersHorizontal,
  Flame,
  CheckCircle2,
  Sparkles,
} from "lucide-react";

export const RootCauseCard: React.FC = () => {
  const { rca, selectedIncident, triggerRca, isActionLoading } = useOpsPilot();
  const [showBreakdown, setShowBreakdown] = useState<boolean>(false);

  if (!selectedIncident) {
    return (
      <div className="bg-surface-card border border-surface-border rounded-xl p-5 text-center text-slate-500 font-mono text-xs">
        Select an incident to view root-cause analysis.
      </div>
    );
  }

  if (!rca) {
    return (
      <div className="bg-surface-card border border-surface-border rounded-xl p-5 text-center shadow-panel">
        <div className="w-10 h-10 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto text-amber-400 mb-2">
          <Brain className="w-5 h-5 animate-pulse" />
        </div>
        <h4 className="text-xs font-semibold text-slate-200">Root Cause Diagnosis Pending</h4>
        <p className="text-[11px] text-slate-400 mt-1 max-w-sm mx-auto">
          Execute topology & evidence-grounded root-cause diagnosis.
        </p>
        <button
          onClick={() => triggerRca(true, false)}
          disabled={isActionLoading}
          className="mt-3 px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-accent-blue hover:bg-blue-500 text-white shadow-sm transition-all disabled:opacity-50"
        >
          Diagnose Root Cause
        </button>
      </div>
    );
  }

  const confidencePercent = (rca.confidence_score * 100).toFixed(0);
  const isFallback = rca.analysis_mode === "deterministic_fallback";

  return (
    <div className="bg-surface-card border border-surface-border rounded-xl overflow-hidden shadow-panel flex flex-col">
      {/* Header */}
      <div className="px-4 py-2.5 border-b border-surface-border bg-surface-panel/80 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Target className="w-3.5 h-3.5 text-amber-400" />
          <h3 className="text-xs font-semibold text-slate-100">
            Probable Root Cause & Diagnosis
          </h3>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-elevated text-slate-300 border border-surface-border flex items-center gap-1">
            <Sparkles className="w-2.5 h-2.5 text-accent-purple" />
            <span>{isFallback ? "Deterministic Fallback" : `AI Model: ${rca.model_used || "Grounded"}`}</span>
          </span>

          <button
            onClick={() => triggerRca(true, false)}
            disabled={isActionLoading}
            className="p-1 rounded hover:bg-surface-elevated text-slate-400 hover:text-slate-200 transition-all"
            title="Re-run Diagnosis"
          >
            <RefreshCw className={`w-3 h-3 ${isActionLoading ? "animate-spin text-amber-400" : ""}`} />
          </button>
        </div>
      </div>

      <div className="p-4 space-y-3.5">
        {/* Origin Spotlight Box */}
        <div className="p-3.5 rounded-lg bg-surface-panel/90 border border-amber-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
          <div className="space-y-0.5">
            <div className="text-[10px] font-mono text-amber-400 uppercase tracking-wider flex items-center gap-1 font-semibold">
              <Flame className="w-3 h-3" />
              <span>Root-Side Fault Origin</span>
            </div>
            <div className="text-lg font-bold font-mono text-white">
              {rca.root_cause_service}
            </div>
            <div className="text-[11px] text-slate-400 font-sans line-clamp-1">
              {rca.root_cause_summary}
            </div>
          </div>

          {/* Compact Confidence Badge */}
          <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
            <div className="text-right font-mono">
              <div className="text-[9px] text-slate-500 uppercase">Confidence</div>
              <div className="text-lg font-bold text-amber-300">{confidencePercent}%</div>
            </div>
            <button
              onClick={() => setShowBreakdown((prev) => !prev)}
              className="p-1.5 rounded bg-surface-elevated hover:bg-surface-border text-slate-300 border border-surface-border text-xs transition-all"
              title="Toggle mathematical breakdown"
            >
              <SlidersHorizontal className="w-3.5 h-3.5 text-accent-sky" />
            </button>
          </div>
        </div>

        {/* Confidence Breakdown Accordion */}
        {showBreakdown && (
          <ConfidenceBreakdown
            breakdown={rca.confidence_breakdown}
            totalScore={rca.confidence_score}
          />
        )}

        {/* Why / Grounded Causal Narrative */}
        <div className="space-y-1">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">
            Causal Explanation
          </span>
          <div className="p-3 rounded-lg bg-surface-panel/80 border border-surface-border text-xs text-slate-300 font-sans leading-relaxed">
            {rca.causal_narrative}
          </div>
        </div>

        {/* Recommended Action */}
        <div className="pt-2 border-t border-surface-border flex items-center justify-between text-xs font-mono">
          <span className="text-slate-400 text-[11px]">Recommended Action:</span>
          <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-bold text-[11px]">
            {rca.recommended_action}
          </span>
        </div>
      </div>
    </div>
  );
};
