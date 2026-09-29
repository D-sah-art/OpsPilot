import React from "react";
import type { ConfidenceBreakdown as BreakdownType } from "../../api/types";
import { Calculator } from "lucide-react";

interface Props {
  breakdown?: BreakdownType | null;
  totalScore: number;
}

export const ConfidenceBreakdown: React.FC<Props> = ({ breakdown, totalScore }) => {
  if (!breakdown) return null;

  const items = [
    {
      name: "Topological Clarity",
      value: breakdown.topological_clarity,
      weight: "30%",
    },
    {
      name: "Causal Consistency",
      value: breakdown.causal_consistency,
      weight: "25%",
    },
    {
      name: "Evidence Completeness",
      value: breakdown.evidence_completeness,
      weight: "20%",
    },
    {
      name: "Symptom Breadth",
      value: breakdown.symptom_breadth,
      weight: "15%",
    },
    {
      name: "Correlation Cohesion",
      value: breakdown.correlation_cohesion,
      weight: "10%",
    },
  ];

  return (
    <div className="bg-surface-panel/90 border border-surface-border rounded-lg p-3 space-y-2 font-mono text-xs">
      <div className="flex items-center justify-between pb-1.5 border-b border-surface-border">
        <span className="text-[11px] font-sans font-semibold text-slate-300 flex items-center gap-1.5">
          <Calculator className="w-3 h-3 text-accent-sky" />
          <span>Evidence-Derived Confidence Breakdown</span>
        </span>
        <span className="text-[11px] font-bold text-amber-300">
          Total: {(totalScore * 100).toFixed(1)}%
        </span>
      </div>

      <div className="space-y-1.5 pt-1">
        {items.map((item) => {
          const scorePercent = (item.value * 100).toFixed(0);
          return (
            <div key={item.name} className="space-y-0.5">
              <div className="flex justify-between text-[10px]">
                <span className="text-slate-400">
                  {item.name} <span className="text-slate-500 font-normal">({item.weight})</span>
                </span>
                <span className="text-accent-sky font-bold">{scorePercent}%</span>
              </div>
              <div className="w-full h-1 rounded-full bg-surface-elevated overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-accent-sky to-accent-blue transition-all duration-300"
                  style={{ width: `${scorePercent}%` }}
                ></div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="pt-1.5 border-t border-surface-border text-[9px] text-slate-500 truncate">
        Formula: {breakdown.formula}
      </div>
    </div>
  );
};
