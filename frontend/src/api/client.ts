import type {
  Alert,
  TopologyData,
  Incident,
  RootCauseAnalysis,
  RemediationResult,
  RecoveryEvidence,
  RemediationAudit,
  CorrelationBenchmarkResult,
  HealthStatus,
  ServiceEntity,
} from "./types";

const BASE_URL = "";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const data = await res.json();
      if (data && data.detail) {
        errorDetail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(`API Error [${res.status}]: ${errorDetail}`);
  }
  return res.json() as Promise<T>;
}

export const apiClient = {
  // System Health
  async getHealth(): Promise<HealthStatus> {
    const res = await fetch(`${BASE_URL}/health`);
    return handleResponse<HealthStatus>(res);
  },

  // Synchronization
  async syncShopFlow(): Promise<{ status: string; services?: number; alerts?: number }> {
    const res = await fetch(`${BASE_URL}/api/sync/shopflow`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    return handleResponse(res);
  },

  // Topology & Services
  async getTopology(): Promise<TopologyData> {
    const res = await fetch(`${BASE_URL}/api/topology`);
    return handleResponse<TopologyData>(res);
  },

  async getServices(): Promise<ServiceEntity[]> {
    const res = await fetch(`${BASE_URL}/api/services`);
    return handleResponse<ServiceEntity[]>(res);
  },

  // Alerts
  async getAlerts(limit: number = 100): Promise<Alert[]> {
    const res = await fetch(`${BASE_URL}/api/alerts?limit=${limit}`);
    return handleResponse<Alert[]>(res);
  },

  // Incidents & Correlation
  async getIncidents(): Promise<Incident[]> {
    const res = await fetch(`${BASE_URL}/api/incidents`);
    return handleResponse<Incident[]>(res);
  },

  async getIncident(incidentId: string): Promise<Incident> {
    const res = await fetch(`${BASE_URL}/api/incidents/${incidentId}`);
    return handleResponse<Incident>(res);
  },

  async runCorrelation(
    strategy: "dependency_aware" | "time_only" = "dependency_aware",
    persist: boolean = true,
    timeWindowSeconds: number = 600.0,
    threshold: number = 0.45
  ): Promise<{ status: string; strategy: string; incidents_count: number; incidents: Incident[] }> {
    const res = await fetch(`${BASE_URL}/api/correlation/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        strategy,
        persist,
        time_window_seconds: timeWindowSeconds,
        threshold,
      }),
    });
    return handleResponse(res);
  },

  async getCorrelationBenchmark(): Promise<{
    total_alerts: number;
    benchmark: Record<string, CorrelationBenchmarkResult>;
  }> {
    const res = await fetch(`${BASE_URL}/api/correlation/benchmark`);
    return handleResponse(res);
  },

  // Root Cause Diagnosis (AI + Fallback)
  async diagnoseRootCause(
    incidentId: string,
    forceRefresh: boolean = false,
    forceFallback: boolean = false
  ): Promise<RootCauseAnalysis> {
    const res = await fetch(`${BASE_URL}/api/incidents/${incidentId}/root-cause`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        force_refresh: forceRefresh,
        force_fallback: forceFallback,
      }),
    });
    return handleResponse<RootCauseAnalysis>(res);
  },

  async getRootCause(incidentId: string): Promise<RootCauseAnalysis> {
    const res = await fetch(`${BASE_URL}/api/incidents/${incidentId}/root-cause`);
    return handleResponse<RootCauseAnalysis>(res);
  },

  // Remediation & Safety Gate
  async remediateIncident(
    incidentId: string,
    params: {
      action?: string;
      target_service?: string;
      mode?: "SIMULATION" | "REAL";
      parameters?: Record<string, any>;
      force?: boolean;
      requested_by?: string;
    } = {}
  ): Promise<RemediationResult> {
    const res = await fetch(`${BASE_URL}/api/incidents/${incidentId}/remediate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: params.action,
        target_service: params.target_service,
        mode: params.mode || "SIMULATION",
        parameters: params.parameters || {},
        force: params.force || false,
        requested_by: params.requested_by || "operator",
      }),
    });
    return handleResponse<RemediationResult>(res);
  },

  async getLatestRemediation(incidentId: string): Promise<RemediationResult> {
    const res = await fetch(`${BASE_URL}/api/incidents/${incidentId}/remediation`);
    return handleResponse<RemediationResult>(res);
  },

  // Recovery Verification
  async verifyRecovery(incidentId: string): Promise<RecoveryEvidence> {
    const res = await fetch(`${BASE_URL}/api/incidents/${incidentId}/remediate/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    return handleResponse<RecoveryEvidence>(res);
  },

  // Audit Trail
  async getIncidentAuditTrail(incidentId: string): Promise<RemediationAudit[]> {
    const res = await fetch(`${BASE_URL}/api/incidents/${incidentId}/audit`);
    return handleResponse<RemediationAudit[]>(res);
  },

  // Reset to Clean Demo State
  async resetAll(): Promise<{ status: string }> {
    const res = await fetch(`${BASE_URL}/api/reset`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    try {
      await fetch(`http://127.0.0.1:8000/api/chaos/reset`, { method: "POST" });
    } catch {
      // ignore if shopflow not running
    }
    return handleResponse(res);
  },
  // Hindsight Memory System API
  async getMemoryStatus(): Promise<{ enabled: boolean; base_url: string; bank_id: string; sdk_available: boolean }> {
    const res = await fetch(`${BASE_URL}/api/memory/status`);
    return handleResponse(res);
  },

  async clearMemoryBank(): Promise<{ status: string; message: string }> {
    const res = await fetch(`${BASE_URL}/api/memory/clear`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    return handleResponse(res);
  },
};

