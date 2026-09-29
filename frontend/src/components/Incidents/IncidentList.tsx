import React from "react";
import { useOpsPilot } from "../../context/OpsPilotContext";
import type { Incident } from "../../api/types";
import {
  Layers,
  AlertOctagon,
  ChevronRight,
  Shield,
  Activity,
  Network,
} from "lucide-react";

export const IncidentList: React.FC = () => {
  const { alerts, incidents, selectedIncident, selectIncident } = useOpsPilot();

  const totalAlerts = alerts.length;
  const totalIncidents = incidents.length;
  const noiseReductionPercent =
    totalAlerts > 0
      ? (((totalAlerts - totalIncidents) / totalAlerts) * 100).toFixed(1)
      : "0.0";

  if (incidents.length === 0) {
    return (
      <div className="bg-surface-card border border-surface-border rounded-xl p-5 text-center shadow-panel">
        <div className="w-10 h-10 rounded-lg bg-surface-elevated border border-surface-border flex items-center justify-center mx-auto text-slate-500 mb-2">
          <Layers className="w-5 h-5" />
        </div>
        <h4 className="text-xs font-semibold text-slate-300">No Active Incidents</h4>
        <p className="text-[11px] text-slate-500 mt-1 max-w-xs mx-auto">
          Click "Correlate Alerts" to execute dependency-aware clustering.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-surface-card border border-surface-border rounded-xl overflow-hidden shadow-panel flex flex-col">
      {/* Header */}
      <div className="px-4 py-2.5 border-b border-surface-border bg-surface-panel/80 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="w-3.5 h-3.5 text-accent-sky" />
          <h3 className="text-xs font-semibold text-slate-100">
            Correlated Incidents ({incidents.length})
          </h3>
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded bg-accent-sky/10 text-accent-sky border border-accent-sky/20 font-mono">
          {noiseReductionPercent}% Noise Reduction
        </span>
      </div>

      {/* Incident List */}
      <div className="p-3 space-y-2">
        {incidents.map((incident) => {
          const isSelected = selectedIncident?.incident_id === incident.incident_id;

          return (
            <div
              key={incident.incident_id}
              onClick={() => selectIncident(incident)}
              className={`p-3 rounded-lg border transition-all cursor-pointer ${
                isSelected
                  ? "bg-surface-elevated border-accent-sky/50 shadow-sm ring-1 ring-accent-sky/30"
                  : "bg-surface-card/60 border-surface-border hover:border-slate-600 hover:bg-surface-elevated/40"
              }`}
            >
              {/* Header: Title & Severity */}
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-start gap-2">
                  <span className="p-1 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 mt-0.5 shrink-0">
                    <AlertOctagon className="w-3.5 h-3.5" />
                  </span>
                  <div>
                    <h4 className="text-xs font-semibold text-slate-100 leading-snug line-clamp-1">
                      {incident.title}
                    </h4>
                    <div className="text-[10px] text-slate-400 font-mono flex items-center gap-2 mt-0.5">
                      <span>{incident.incident_id}</span>
                      <span>•</span>
                      <span>{new Date(incident.created_at).toLocaleTimeString()}</span>
                    </div>
                  </div>
                </div>

                <span
                  className={`text-[10px] font-bold font-mono px-1.5 py-0.5 rounded uppercase shrink-0 ${
                    incident.severity === "CRITICAL"
                      ? "bg-rose-500/15 text-rose-300 border border-rose-500/30"
                      : "bg-amber-500/15 text-amber-300 border border-amber-500/30"
                  }`}
                >
                  {incident.severity}
                </span>
              </div>

              {/* Meta Stats: Alerts, Cohesion, Method */}
              <div className="mt-2.5 pt-2 border-t border-surface-border/80 flex items-center justify-between text-[11px] font-mono">
                <div className="flex items-center gap-2">
                  <span className="text-rose-400 font-bold bg-rose-950/30 px-1.5 py-0.5 rounded border border-rose-900/40 text-[10px]">
                    {incident.alert_count} Alerts
                  </span>
                  <span className="text-slate-300 text-[10px]">
                    Cohesion: <span className="text-emerald-400 font-semibold">{(incident.correlation_score * 100).toFixed(0)}%</span>
                  </span>
                </div>

                <div className="text-[10px] text-accent-sky font-sans flex items-center gap-0.5">
                  <span>Selected</span>
                  <ChevronRight className="w-3 h-3" />
                </div>
              </div>

              {/* Affected Services Chips */}
              {incident.affected_services && incident.affected_services.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {incident.affected_services.map((svc) => (
                    <span
                      key={svc}
                      className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-surface-bg border border-surface-border text-slate-300"
                    >
                      {svc}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
