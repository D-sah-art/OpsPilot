import React, { useState } from "react";
import { useOpsPilot } from "../../context/OpsPilotContext";
import {
  Bell,
  Search,
  AlertTriangle,
  AlertOctagon,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

export const AlertFeed: React.FC = () => {
  const { alerts } = useOpsPilot();
  const [filterService, setFilterService] = useState<string>("ALL");
  const [filterSeverity, setFilterSeverity] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [isCollapsed, setIsCollapsed] = useState<boolean>(false);

  // Unique services
  const uniqueServices = Array.from(new Set(alerts.map((a) => a.service))).sort();

  // Filter alerts
  const filteredAlerts = alerts.filter((alert) => {
    if (filterService !== "ALL" && alert.service !== filterService) return false;
    if (filterSeverity !== "ALL" && alert.severity !== filterSeverity) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        alert.service.toLowerCase().includes(q) ||
        alert.alert_type.toLowerCase().includes(q) ||
        alert.message.toLowerCase().includes(q) ||
        alert.id.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="bg-surface-card border border-surface-border rounded-xl overflow-hidden shadow-panel flex flex-col font-mono text-xs">
      {/* Header */}
      <div
        onClick={() => setIsCollapsed((prev) => !prev)}
        className="px-4 py-2.5 border-b border-surface-border bg-surface-panel/80 flex items-center justify-between cursor-pointer hover:bg-surface-elevated transition-all"
      >
        <div className="flex items-center gap-2">
          <Bell className="w-3.5 h-3.5 text-rose-400" />
          <h3 className="text-xs font-semibold text-slate-100 font-sans">
            Raw Telemetry Alert Feed ({alerts.length})
          </h3>
        </div>

        <div className="flex items-center gap-2.5">
          <span className="text-[10px] px-2 py-0.5 rounded bg-rose-500/10 text-rose-300 border border-rose-500/20">
            Real Ingestion Stream
          </span>
          {isCollapsed ? (
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          ) : (
            <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
          )}
        </div>
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className="p-3 space-y-2.5">
          {/* Filters */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <div className="relative">
              <Search className="w-3 h-3 text-slate-500 absolute left-2.5 top-2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Filter alerts..."
                className="w-full pl-7 pr-2.5 py-1 rounded-md bg-surface-panel border border-surface-border text-slate-200 placeholder-slate-500 focus:outline-none focus:border-accent-sky text-xs"
              />
            </div>

            <select
              value={filterService}
              onChange={(e) => setFilterService(e.target.value)}
              className="bg-surface-panel border border-surface-border rounded-md px-2 py-1 text-slate-300 focus:outline-none focus:border-accent-sky text-xs"
            >
              <option value="ALL">All Services ({alerts.length})</option>
              {uniqueServices.map((svc) => (
                <option key={svc} value={svc}>
                  {svc} ({alerts.filter((a) => a.service === svc).length})
                </option>
              ))}
            </select>

            <select
              value={filterSeverity}
              onChange={(e) => setFilterSeverity(e.target.value)}
              className="bg-surface-panel border border-surface-border rounded-md px-2 py-1 text-slate-300 focus:outline-none focus:border-accent-sky text-xs"
            >
              <option value="ALL">All Severities</option>
              <option value="CRITICAL">CRITICAL</option>
              <option value="WARNING">WARNING</option>
              <option value="INFO">INFO</option>
            </select>
          </div>

          {/* List of Alerts */}
          <div className="max-h-60 overflow-y-auto space-y-1.5 pr-1">
            {filteredAlerts.length === 0 ? (
              <div className="p-3 rounded-lg bg-surface-panel text-center text-slate-500 text-xs font-sans">
                No alerts match the selected criteria.
              </div>
            ) : (
              filteredAlerts.map((alert) => (
                <div
                  key={alert.id}
                  className="p-2 rounded-lg bg-surface-panel/80 border border-surface-border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-1.5 hover:border-slate-600 transition-all text-[11px]"
                >
                  <div className="flex items-center gap-2">
                    {alert.severity === "CRITICAL" ? (
                      <AlertOctagon className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                    ) : (
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                    )}
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="font-bold text-slate-200">{alert.service}</span>
                        <span className="text-[10px] text-slate-400">({alert.alert_type})</span>
                      </div>
                      <div className="text-[10px] text-slate-400 font-sans line-clamp-1">
                        {alert.message}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2.5 shrink-0 text-[10px] text-slate-400">
                    <span>
                      {alert.metric}: <span className="text-accent-sky font-semibold">{alert.metric_value}</span>
                    </span>
                    <span className="text-slate-500">
                      {new Date(alert.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};
