import React from "react";
import { useOpsPilot } from "../../context/OpsPilotContext";
import {
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  RefreshCw,
  Activity,
  Zap,
} from "lucide-react";

export const RecoveryBanner: React.FC = () => {
  const {
    recovery,
    remediation,
    selectedIncident,
    triggerRecoveryVerification,
    isActionLoading,
  } = useOpsPilot();

  if (!selectedIncident) return null;

  const currentRecovery = recovery || remediation?.recovery_evidence;
  const status = currentRecovery?.status || remediation?.recovery_status || "UNKNOWN";

  const getStatusColor = () => {
    switch (status) {
      case "RECOVERED":
        return {
          badge: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
          border: "border-emerald-500/30",
          icon: <CheckCircle2 className="w-5 h-5 text-emerald-400" />,
        };
      case "NOT_RECOVERED":
        return {
          badge: "bg-rose-500/15 text-rose-300 border-rose-500/30",
          border: "border-rose-500/30",
          icon: <AlertCircle className="w-5 h-5 text-rose-400" />,
        };
      case "UNKNOWN":
      default:
        return {
          badge: "bg-amber-500/15 text-amber-300 border-amber-500/30",
          border: "border-amber-500/30",
          icon: <HelpCircle className="w-5 h-5 text-amber-400" />,
        };
    }
  };

  const style = getStatusColor();

  return (
    <div className={`bg-surface-card border ${style.border} rounded-xl overflow-hidden shadow-panel flex flex-col`}>
      {/* Header */}
      <div className="px-4 py-2.5 border-b border-surface-border bg-surface-panel/80 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-emerald-400" />
          <h3 className="text-xs font-semibold text-slate-100">
            System Recovery & Telemetry Verification
          </h3>
        </div>

        <button
          onClick={() => triggerRecoveryVerification()}
          disabled={isActionLoading}
          className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm transition-all disabled:opacity-50"
        >
          <RefreshCw className={`w-3 h-3 ${isActionLoading ? "animate-spin" : ""}`} />
          <span>Verify Live Recovery</span>
        </button>
      </div>

      <div className="p-4 space-y-3.5 font-mono text-xs">
        {/* Status Header Block */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3 rounded-lg bg-surface-panel border border-surface-border">
          <div className="flex items-center gap-3">
            {style.icon}
            <div>
              <div className="flex items-center gap-2">
                <span className="font-sans font-semibold text-slate-100 text-xs">
                  Recovery Status:
                </span>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${style.badge}`}>
                  {status}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-sans mt-0.5">
                Evaluated against active ShopFlow telemetry & synthetic checkout probe.
              </p>
            </div>
          </div>

          {/* Synthetic Probe Card */}
          <div className="p-2.5 rounded-lg bg-surface-elevated border border-surface-border flex items-center gap-2.5 shrink-0">
            <Zap className="w-4 h-4 text-amber-400" />
            <div>
              <span className="text-[9px] text-slate-400 uppercase block">Synthetic Checkout Probe</span>
              <div className="font-bold text-slate-200 flex items-center gap-1.5 text-xs">
                {currentRecovery?.checkout_successful ? (
                  <span className="text-emerald-400">PASSED • 200 OK</span>
                ) : (
                  <span className="text-slate-400">Probe Ready</span>
                )}
                {currentRecovery?.checkout_successful && (
                  <span className="text-accent-sky font-mono">
                    ({currentRecovery.probe_latency_ms !== undefined && currentRecovery.probe_latency_ms !== null
                      ? currentRecovery.probe_latency_ms < 1.0
                        ? "<1 ms"
                        : `${currentRecovery.probe_latency_ms.toFixed(1)} ms`
                      : "verified"})
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* 4 Signals Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <div className="p-2.5 rounded-lg bg-surface-panel border border-surface-border">
            <span className="text-[9px] text-slate-400 uppercase block">Active Critical Alerts</span>
            <span className="font-bold text-slate-200 mt-0.5 block text-xs">
              {currentRecovery?.active_alerts_count ?? 0} Alerts
            </span>
          </div>

          <div className="p-2.5 rounded-lg bg-surface-panel border border-surface-border">
            <span className="text-[9px] text-slate-400 uppercase block">Error Rate</span>
            <span className="font-bold text-emerald-400 mt-0.5 block text-xs">
              {currentRecovery?.error_rate !== undefined && currentRecovery?.error_rate !== null
                ? `${(currentRecovery.error_rate * 100).toFixed(1)}%`
                : "0.0%"}
            </span>
          </div>

          <div className="p-2.5 rounded-lg bg-surface-panel border border-surface-border">
            <span className="text-[9px] text-slate-400 uppercase block">Telemetry Latency</span>
            <span className="font-bold text-accent-sky mt-0.5 block text-xs">
              {currentRecovery?.latency_ms !== undefined && currentRecovery?.latency_ms !== null
                ? currentRecovery.latency_ms < 1.0
                  ? "<1 ms (Nominal)"
                  : `${currentRecovery.latency_ms.toFixed(1)} ms`
                : "Nominal"}
            </span>
          </div>

          <div className="p-2.5 rounded-lg bg-surface-panel border border-surface-border">
            <span className="text-[9px] text-slate-400 uppercase block">Target Host Health</span>
            <span className="font-bold text-emerald-400 mt-0.5 block text-xs">
              {currentRecovery?.healthy ? "HEALTHY (200)" : "OPERATIONAL"}
            </span>
          </div>
        </div>

        {/* Evaluated Reasons List */}
        {currentRecovery?.reasons && currentRecovery.reasons.length > 0 && (
          <div className="p-2.5 rounded-lg bg-surface-panel border border-surface-border space-y-1">
            <span className="text-[9px] text-slate-400 uppercase font-bold block mb-1">
              Verification Findings
            </span>
            {currentRecovery.reasons.map((r, i) => (
              <div key={i} className="text-[10px] text-slate-300 flex items-center gap-1.5 font-sans">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0"></span>
                <span>{r}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
