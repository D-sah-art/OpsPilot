import React, { useState, useEffect } from "react";
import { useOpsPilot } from "../../context/OpsPilotContext";
import { SafetyGateMatrix } from "./SafetyGateMatrix";
import {
  Shield,
  Play,
  CheckCircle,
  RefreshCw,
  Lock,
} from "lucide-react";

export const RemediationControl: React.FC = () => {
  const {
    selectedIncident,
    rca,
    remediation,
    triggerRemediation,
    isActionLoading,
  } = useOpsPilot();

  const [selectedAction, setSelectedAction] = useState<string>("reset_connections");
  const [selectedService, setSelectedService] = useState<string>("postgresql");
  const [executionMode, setExecutionMode] = useState<"SIMULATION" | "REAL">("SIMULATION");

  // Sync default service & action from RCA
  useEffect(() => {
    if (rca?.root_cause_service) {
      setSelectedService(rca.root_cause_service);
    }
    if (rca?.recommended_action) {
      if (rca.recommended_action === "reset_connections" || rca.recommended_action === "restart_service") {
        setSelectedAction(rca.recommended_action);
      } else if (rca.root_cause_service === "postgresql") {
        setSelectedAction("reset_connections");
      }
    }
  }, [rca]);

  if (!selectedIncident) {
    return (
      <div className="bg-surface-card border border-surface-border rounded-xl p-5 text-center text-slate-500 font-mono text-xs">
        Select an incident to configure safety-gated remediation.
      </div>
    );
  }

  const handleExecute = () => {
    triggerRemediation({
      action: selectedAction,
      target_service: selectedService,
      mode: executionMode,
      force: true,
    });
  };

  const hasResult = !!remediation;
  const safetyGate = remediation?.safety_gate_result;

  return (
    <div className="bg-surface-card border border-surface-border rounded-xl overflow-hidden shadow-panel flex flex-col">
      {/* Header */}
      <div className="px-4 py-2.5 border-b border-surface-border bg-surface-panel/80 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="w-3.5 h-3.5 text-accent-purple" />
          <h3 className="text-xs font-semibold text-slate-100">
            Safety-Gated Remediation Engine
          </h3>
        </div>

        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-elevated text-accent-purple border border-surface-border">
          Deterministic Allow-List
        </span>
      </div>

      <div className="p-4 space-y-3.5">
        {/* Configuration Row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
          {/* Action */}
          <div>
            <label className="text-[10px] font-mono text-slate-400 uppercase mb-1 block">
              Allow-Listed Action
            </label>
            <select
              value={selectedAction}
              onChange={(e) => setSelectedAction(e.target.value)}
              className="w-full bg-surface-panel border border-surface-border rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-accent-sky"
            >
              <option value="reset_connections">reset_connections</option>
              <option value="restart_service">restart_service</option>
            </select>
          </div>

          {/* Target Service */}
          <div>
            <label className="text-[10px] font-mono text-slate-400 uppercase mb-1 block">
              Target Service
            </label>
            <select
              value={selectedService}
              onChange={(e) => setSelectedService(e.target.value)}
              className="w-full bg-surface-panel border border-surface-border rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-accent-sky"
            >
              {selectedIncident.affected_services?.map((svc) => (
                <option key={svc} value={svc}>
                  {svc}
                </option>
              )) || <option value="postgresql">postgresql</option>}
            </select>
          </div>

          {/* Execution Safety Mode */}
          <div>
            <label className="text-[10px] font-mono text-slate-400 uppercase mb-1 block">
              Safety Mode
            </label>
            <div className="grid grid-cols-2 gap-1">
              <button
                type="button"
                onClick={() => setExecutionMode("SIMULATION")}
                className={`py-1.5 px-2 rounded-lg text-xs font-mono font-semibold transition-all ${
                  executionMode === "SIMULATION"
                    ? "bg-accent-sky/20 text-accent-sky border border-accent-sky/40"
                    : "bg-surface-panel text-slate-400 border border-surface-border"
                }`}
              >
                SIMULATION
              </button>
              <button
                type="button"
                onClick={() => setExecutionMode("REAL")}
                className={`py-1.5 px-2 rounded-lg text-xs font-mono font-semibold transition-all ${
                  executionMode === "REAL"
                    ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                    : "bg-surface-panel text-slate-400 border border-surface-border"
                }`}
              >
                REAL (Live)
              </button>
            </div>
          </div>
        </div>

        {/* Action Trigger Button */}
        <div className="flex justify-end pt-1">
          <button
            onClick={handleExecute}
            disabled={isActionLoading}
            className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold rounded-lg bg-accent-blue hover:bg-blue-500 text-white shadow-sm transition-all disabled:opacity-50"
          >
            {isActionLoading ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Evaluating Gate...</span>
              </>
            ) : (
              <>
                <Play className="w-3 h-3 fill-white" />
                <span>Execute Gated Remediation ({executionMode})</span>
              </>
            )}
          </button>
        </div>

        {/* Safety Gate Condition Matrix */}
        {safetyGate && (
          <SafetyGateMatrix
            conditions={safetyGate.conditions}
            decision={safetyGate.decision}
          />
        )}

        {/* Execution Result Banner */}
        {hasResult && (
          <div className="p-3 rounded-lg bg-surface-panel border border-surface-border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs font-mono">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
              <div>
                <span className="text-slate-200 font-bold">
                  Status: {remediation.execution_status}
                </span>
                <span className="text-slate-400 ml-1.5">({remediation.action} on {remediation.target_service})</span>
                <div className="text-[10px] text-slate-400 mt-0.5">{remediation.reason}</div>
              </div>
            </div>

            <span className="text-[10px] text-slate-500 shrink-0">
              Audit ID: {remediation.audit_id}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
