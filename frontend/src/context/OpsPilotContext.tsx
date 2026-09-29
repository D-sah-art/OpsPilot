import React, { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { apiClient } from "../api/client";
import type {
  HealthStatus,
  TopologyData,
  ServiceEntity,
  Alert,
  Incident,
  RootCauseAnalysis,
  RemediationResult,
  RecoveryEvidence,
  RemediationAudit,
  CorrelationBenchmarkResult,
} from "../api/types";

interface OpsPilotContextType {
  health: HealthStatus | null;
  topology: TopologyData | null;
  services: ServiceEntity[];
  alerts: Alert[];
  incidents: Incident[];
  selectedIncident: Incident | null;
  selectedIncidentDetails: Incident | null;
  rca: RootCauseAnalysis | null;
  remediation: RemediationResult | null;
  recovery: RecoveryEvidence | null;
  audits: RemediationAudit[];
  benchmark: { total_alerts: number; benchmark: Record<string, CorrelationBenchmarkResult> } | null;
  isLoading: boolean;
  isActionLoading: boolean;
  isPolling: boolean;
  error: string | null;
  lastUpdated: Date | null;
  
  // Actions
  refreshAll: () => Promise<void>;
  selectIncident: (incident: Incident | null) => Promise<void>;
  triggerSync: () => Promise<void>;
  triggerCorrelation: (strategy?: "dependency_aware" | "time_only") => Promise<void>;
  triggerRca: (forceRefresh?: boolean, forceFallback?: boolean) => Promise<void>;
  triggerRemediation: (params?: {
    action?: string;
    target_service?: string;
    mode?: "SIMULATION" | "REAL";
    force?: boolean;
  }) => Promise<void>;
  triggerRecoveryVerification: () => Promise<void>;
  loadBenchmark: () => Promise<void>;
  triggerReset: () => Promise<void>;
  togglePolling: () => void;
  clearError: () => void;
}

const OpsPilotContext = createContext<OpsPilotContextType | undefined>(undefined);

export const OpsPilotProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [topology, setTopology] = useState<TopologyData | null>(null);
  const [services, setServices] = useState<ServiceEntity[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [selectedIncidentDetails, setSelectedIncidentDetails] = useState<Incident | null>(null);
  const [rca, setRca] = useState<RootCauseAnalysis | null>(null);
  const [remediation, setRemediation] = useState<RemediationResult | null>(null);
  const [recovery, setRecovery] = useState<RecoveryEvidence | null>(null);
  const [audits, setAudits] = useState<RemediationAudit[]>([]);
  const [benchmark, setBenchmark] = useState<{
    total_alerts: number;
    benchmark: Record<string, CorrelationBenchmarkResult>;
  } | null>(null);
  
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isActionLoading, setIsActionLoading] = useState<boolean>(false);
  const [isPolling, setIsPolling] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const clearError = () => setError(null);

  const loadIncidentDetails = useCallback(async (incidentId: string) => {
    try {
      const details = await apiClient.getIncident(incidentId);
      setSelectedIncidentDetails(details);

      // Try fetching RCA
      try {
        const rcaData = await apiClient.getRootCause(incidentId);
        setRca(rcaData);
      } catch {
        setRca(null);
      }

      // Try fetching latest remediation
      try {
        const remData = await apiClient.getLatestRemediation(incidentId);
        setRemediation(remData);
        if (remData && remData.recovery_evidence) {
          setRecovery(remData.recovery_evidence);
        }
      } catch {
        setRemediation(null);
        setRecovery(null);
      }

      // Fetch audit history
      try {
        const auditList = await apiClient.getIncidentAuditTrail(incidentId);
        setAudits(auditList);
      } catch {
        setAudits([]);
      }
    } catch (err: any) {
      console.error("Failed to load incident details:", err);
    }
  }, []);

  const refreshAll = useCallback(async () => {
    try {
      const [h, topo, servs, alts, incs] = await Promise.all([
        apiClient.getHealth().catch(() => null),
        apiClient.getTopology().catch(() => null),
        apiClient.getServices().catch(() => []),
        apiClient.getAlerts(200).catch(() => []),
        apiClient.getIncidents().catch(() => []),
      ]);

      if (h) setHealth(h);
      if (topo) setTopology(topo);
      if (servs) setServices(servs);
      if (alts) setAlerts(alts);
      if (incs) {
        setIncidents(incs);
        // Automatically select the first incident if none selected or if selected is outdated
        if (incs.length > 0) {
          if (!selectedIncident || !incs.some((i) => i.incident_id === selectedIncident.incident_id)) {
            setSelectedIncident(incs[0]);
            loadIncidentDetails(incs[0].incident_id);
          } else {
            // Refresh details for current selected
            loadIncidentDetails(selectedIncident.incident_id);
          }
        } else {
          setSelectedIncident(null);
          setSelectedIncidentDetails(null);
          setRca(null);
          setRemediation(null);
          setRecovery(null);
          setAudits([]);
        }
      }
      setLastUpdated(new Date());
    } catch (err: any) {
      console.error("Error refreshing OpsPilot data:", err);
    } finally {
      setIsLoading(false);
    }
  }, [selectedIncident, loadIncidentDetails]);

  // Initial load
  useEffect(() => {
    refreshAll();
  }, []);

  // Polling loop
  useEffect(() => {
    if (!isPolling) return;
    const timer = setInterval(() => {
      refreshAll();
    }, 1500);
    return () => clearInterval(timer);
  }, [isPolling, refreshAll]);

  const selectIncident = async (incident: Incident | null) => {
    setSelectedIncident(incident);
    if (incident) {
      await loadIncidentDetails(incident.incident_id);
    } else {
      setSelectedIncidentDetails(null);
      setRca(null);
      setRemediation(null);
      setRecovery(null);
      setAudits([]);
    }
  };

  const triggerSync = async () => {
    setIsActionLoading(true);
    setError(null);
    try {
      await apiClient.syncShopFlow();
      await refreshAll();
    } catch (err: any) {
      setError(`Sync failed: ${err.message}`);
    } finally {
      setIsActionLoading(false);
    }
  };

  const triggerCorrelation = async (strategy: "dependency_aware" | "time_only" = "dependency_aware") => {
    setIsActionLoading(true);
    setError(null);
    try {
      // Auto-sync freshest telemetry from ShopFlow immediately
      await apiClient.syncShopFlow().catch(() => {});
      const res = await apiClient.runCorrelation(strategy, true);
      await refreshAll();
      if (res.incidents && res.incidents.length > 0) {
        setSelectedIncident(res.incidents[0]);
        await loadIncidentDetails(res.incidents[0].incident_id);
      }
    } catch (err: any) {
      setError(`Correlation failed: ${err.message}`);
    } finally {
      setIsActionLoading(false);
    }
  };

  const triggerRca = async (forceRefresh: boolean = true, forceFallback: boolean = false) => {
    if (!selectedIncident) return;
    setIsActionLoading(true);
    setError(null);
    try {
      const rcaResult = await apiClient.diagnoseRootCause(
        selectedIncident.incident_id,
        forceRefresh,
        forceFallback
      );
      setRca(rcaResult);
      await refreshAll();
    } catch (err: any) {
      setError(`RCA Diagnosis failed: ${err.message}`);
    } finally {
      setIsActionLoading(false);
    }
  };

  const triggerRemediation = async (params: {
    action?: string;
    target_service?: string;
    mode?: "SIMULATION" | "REAL";
    force?: boolean;
  } = {}) => {
    if (!selectedIncident) return;
    setIsActionLoading(true);
    setError(null);
    try {
      const remResult = await apiClient.remediateIncident(selectedIncident.incident_id, {
        ...params,
        mode: params.mode || "SIMULATION",
      });
      setRemediation(remResult);
      if (remResult.recovery_evidence) {
        setRecovery(remResult.recovery_evidence);
      }
      // Reload audits & details
      const auditList = await apiClient.getIncidentAuditTrail(selectedIncident.incident_id);
      setAudits(auditList);
      await refreshAll();
    } catch (err: any) {
      setError(`Remediation failed: ${err.message}`);
    } finally {
      setIsActionLoading(false);
    }
  };

  const triggerRecoveryVerification = async () => {
    if (!selectedIncident) return;
    setIsActionLoading(true);
    setError(null);
    try {
      const rec = await apiClient.verifyRecovery(selectedIncident.incident_id);
      setRecovery(rec);
      // Also update latest remediation record
      try {
        const remData = await apiClient.getLatestRemediation(selectedIncident.incident_id);
        setRemediation(remData);
      } catch {
        // ignore
      }
      const auditList = await apiClient.getIncidentAuditTrail(selectedIncident.incident_id);
      setAudits(auditList);
    } catch (err: any) {
      setError(`Recovery verification failed: ${err.message}`);
    } finally {
      setIsActionLoading(false);
    }
  };

  const loadBenchmark = async () => {
    setIsActionLoading(true);
    setError(null);
    try {
      const data = await apiClient.getCorrelationBenchmark();
      setBenchmark(data);
    } catch (err: any) {
      setError(`Benchmark load failed: ${err.message}`);
    } finally {
      setIsActionLoading(false);
    }
  };

  const triggerReset = async () => {
    setIsActionLoading(true);
    setError(null);
    try {
      await apiClient.resetAll();
      setSelectedIncident(null);
      setSelectedIncidentDetails(null);
      setRca(null);
      setRemediation(null);
      setRecovery(null);
      setAudits([]);
      setIncidents([]);
      setAlerts([]);
      await refreshAll();
    } catch (err: any) {
      setError(`Reset failed: ${err.message}`);
    } finally {
      setIsActionLoading(false);
    }
  };

  const togglePolling = () => {
    setIsPolling((prev) => !prev);
  };

  return (
    <OpsPilotContext.Provider
      value={{
        health,
        topology,
        services,
        alerts,
        incidents,
        selectedIncident,
        selectedIncidentDetails,
        rca,
        remediation,
        recovery,
        audits,
        benchmark,
        isLoading,
        isActionLoading,
        isPolling,
        error,
        lastUpdated,
        refreshAll,
        selectIncident,
        triggerSync,
        triggerCorrelation,
        triggerRca,
        triggerRemediation,
        triggerRecoveryVerification,
        loadBenchmark,
        triggerReset,
        togglePolling,
        clearError,
      }}
    >
      {children}
    </OpsPilotContext.Provider>
  );
};

export const useOpsPilot = () => {
  const context = useContext(OpsPilotContext);
  if (!context) {
    throw new Error("useOpsPilot must be used within an OpsPilotProvider");
  }
  return context;
};
