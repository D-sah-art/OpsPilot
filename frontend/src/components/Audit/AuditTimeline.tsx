import React, { useState } from "react";
import { useOpsPilot } from "../../context/OpsPilotContext";
import {
  Lock,
  FileText,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

export const AuditTimeline: React.FC = () => {
  const { audits, selectedIncident } = useOpsPilot();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (!selectedIncident) return null;

  return (
    <div className="bg-surface-card border border-surface-border rounded-xl overflow-hidden shadow-panel flex flex-col">
      {/* Header */}
      <div className="px-4 py-2.5 border-b border-surface-border bg-surface-panel/80 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Lock className="w-3.5 h-3.5 text-accent-sky" />
          <h3 className="text-xs font-semibold text-slate-100">
            Immutable Remediation Audit Trail
          </h3>
        </div>

        <span className="text-[10px] px-2 py-0.5 rounded bg-surface-elevated text-slate-400 border border-surface-border font-mono">
          SQLite Append-Only ({audits.length} Records)
        </span>
      </div>

      <div className="p-3">
        {audits.length === 0 ? (
          <div className="p-4 rounded-lg bg-surface-panel border border-surface-border text-center font-mono text-xs text-slate-500">
            No remediation actions executed yet for this incident.
          </div>
        ) : (
          <div className="space-y-2 font-mono text-xs">
            {audits.map((audit) => {
              const isExpanded = expandedId === audit.audit_id;

              return (
                <div
                  key={audit.audit_id}
                  className="rounded-lg border border-surface-border bg-surface-panel/90 overflow-hidden"
                >
                  <div
                    onClick={() => setExpandedId(isExpanded ? null : audit.audit_id)}
                    className="p-2.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 cursor-pointer hover:bg-surface-elevated transition-all"
                  >
                    <div className="flex items-center gap-2">
                      <span className="p-1 rounded bg-accent-sky/10 border border-accent-sky/20 text-accent-sky">
                        <FileText className="w-3.5 h-3.5" />
                      </span>
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className="font-bold text-slate-200">{audit.action}</span>
                          <span className="text-slate-500">→</span>
                          <span className="text-amber-300 font-semibold">{audit.target_service}</span>
                          <span className="text-[9px] px-1 py-0.2 rounded bg-surface-bg border border-surface-border text-slate-400">
                            {audit.execution_mode}
                          </span>
                        </div>
                        <div className="text-[10px] text-slate-500 mt-0.5">
                          {audit.audit_id} • {new Date(audit.timestamp).toLocaleTimeString()}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <span
                        className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                          audit.decision === "APPROVED"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                        }`}
                      >
                        Gate: {audit.decision}
                      </span>

                      <span
                        className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                          audit.recovery_status === "RECOVERED"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        }`}
                      >
                        Recovery: {audit.recovery_status}
                      </span>

                      {isExpanded ? (
                        <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
                      ) : (
                        <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                      )}
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="p-2.5 bg-surface-bg border-t border-surface-border space-y-1.5">
                      <div className="text-[10px] text-slate-400 flex items-center justify-between">
                        <span>Audit Record Payload:</span>
                        <span>Confidence: {(audit.confidence * 100).toFixed(0)}%</span>
                      </div>
                      <pre className="p-2 rounded bg-surface-panel border border-surface-border text-[9px] text-accent-sky overflow-x-auto max-h-40">
                        {JSON.stringify(audit.raw_payload || audit, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
