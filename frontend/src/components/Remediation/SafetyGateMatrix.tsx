import React from "react";
import type { SafetyConditionCheck } from "../../api/types";
import { ShieldCheck, CheckCircle2, XCircle } from "lucide-react";

interface Props {
  conditions: SafetyConditionCheck[];
  decision: string;
}

export const SafetyGateMatrix: React.FC<Props> = ({ conditions, decision }) => {
  if (!conditions || conditions.length === 0) return null;

  const passedCount = conditions.filter((c) => c.passed).length;
  const totalCount = conditions.length;

  return (
    <div className="bg-surface-panel/90 border border-surface-border rounded-lg p-3 space-y-2.5 font-mono text-xs">
      {/* Header */}
      <div className="flex items-center justify-between pb-1.5 border-b border-surface-border">
        <div className="flex items-center gap-1.5 text-[11px] font-sans font-semibold text-slate-300">
          <ShieldCheck className="w-3.5 h-3.5 text-accent-purple" />
          <span>Safety Gate Policy Verification Matrix</span>
        </div>
        <div
          className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
            decision === "APPROVED"
              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
              : decision === "HUMAN_REVIEW"
              ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
              : "bg-rose-500/10 text-rose-400 border-rose-500/20"
          }`}
        >
          {passedCount} / {totalCount} Checks Passed ({decision})
        </div>
      </div>

      {/* Compact 2-Column Checklist */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
        {conditions.map((cond) => (
          <div
            key={cond.condition_number}
            className={`px-2 py-1.5 rounded border text-[10px] flex items-center gap-1.5 ${
              cond.passed
                ? "bg-surface-card border-surface-border text-slate-300"
                : "bg-rose-950/20 border-rose-800/30 text-rose-300"
            }`}
          >
            {cond.passed ? (
              <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />
            ) : (
              <XCircle className="w-3 h-3 text-rose-400 shrink-0" />
            )}
            <span className="truncate">
              #{cond.condition_number} {cond.name}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
