export interface Alert {
  id: string;
  timestamp: string;
  service: string;
  severity: "CRITICAL" | "WARNING" | "INFO" | string;
  alert_type: string;
  metric: string;
  metric_value: number;
  threshold: number;
  message: string;
  source?: string;
  dependency?: string | null;
  tags?: Record<string, any>;
  raw_payload?: Record<string, any>;
}

export interface TopologyNode {
  id: string;
  name?: string;
  type?: string;
  tier?: string;
  criticality?: string;
  status?: string;
}

export interface TopologyEdge {
  source: string;
  target: string;
  protocol?: string;
  type?: string;
  criticality?: string;
  observed?: boolean;
  evidence_count?: number;
  confidence?: number;
  evidence_sources?: string[];
  last_observed?: string;
}

export interface EdgeEvidenceItem {
  count: number;
  confidence: number;
  sources: string[];
  last_observed?: string;
}

export interface TopologyEvidenceSummary {
  total_observations?: number;
  sources?: string[];
  average_edge_confidence?: number;
  edges_evidence?: Record<string, EdgeEvidenceItem>;
  status?: string;
  reason?: string;
}

export interface TopologyData {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  total_nodes: number;
  total_edges: number;
  source?: "discovered" | "fallback" | string;
  discovered_at?: string;
  discovery_source?: string;
  grafana_connected?: boolean;
  grafana_status?: string;
  evidence?: TopologyEvidenceSummary;
  evidence_summary?: TopologyEvidenceSummary;
}

export interface PairwiseScore {
  alert_a_id: string;
  alert_b_id: string;
  service_a: string;
  service_b: string;
  total_score: number;
  dependency_score: number;
  graph_distance_score: number;
  causal_order_score: number;
  temporal_score: number;
  service_score: number;
  alert_type_score: number;
  severity_score: number;
  tag_and_metric_score: number;
  reasons: string[];
}

export interface CorrelationEvidence {
  temporal_span_seconds: number;
  earliest_alert: Record<string, any>;
  latest_alert: Record<string, any>;
  dependency_paths: string[][];
  causal_chain: Array<Record<string, any>>;
  primary_affected_services: string[];
  alert_type_breakdown: Record<string, number>;
  severity_breakdown: Record<string, number>;
  top_pairwise_correlations: Array<Record<string, any>>;
}

export interface Incident {
  incident_id: string;
  title: string;
  severity: string;
  status: string;
  created_at: string;
  updated_at: string;
  resolved_at?: string | null;
  alert_count: number;
  alert_ids: string[];
  affected_services: string[];
  correlation_score: number;
  correlation_method: string;
  correlation_evidence: CorrelationEvidence;
  alerts?: Alert[];
}

export interface ConfidenceBreakdown {
  topological_clarity: number;
  causal_consistency: number;
  evidence_completeness: number;
  symptom_breadth: number;
  correlation_cohesion: number;
  weights: Record<string, number>;
  formula: string;
}

export interface HindsightMemoryItem {
  id: string;
  incident_id: string;
  title: string;
  content: string;
  affected_services: string[];
  root_cause_service?: string | null;
  remediation_action?: string | null;
  recovery_verified: boolean;
  tags: string[];
  timestamp: string;
}

export interface MemoryStatusType {
  enabled: boolean;
  connection_status: "CONNECTED_TO_HINDSIGHT" | "HINDSIGHT_UNAVAILABLE" | "LOCAL_FALLBACK" | "DISABLED" | string;
  base_url: string;
  bank_id: string;
  sdk_available: boolean;
  details?: Record<string, any>;
}

export interface RootCauseAnalysis {
  incident_id: string;
  root_cause_service: string;
  root_cause_summary: string;
  confidence_score: number;
  confidence_breakdown: ConfidenceBreakdown;
  causal_narrative: string;
  propagation_path: string[];
  evidence_summary: string[];
  recommended_action: string;
  analysis_mode: "llm" | "deterministic_fallback" | string;
  model_used?: string | null;
  diagnosed_at: string;
  memory_enabled?: boolean;
  connection_status?: string;
  memory_source?: string;
  memories_recalled?: number;
  memory_status?: string;
  recalled_memories?: HindsightMemoryItem[];
}



export interface SafetyConditionCheck {
  condition_number: number;
  name: string;
  passed: boolean;
  detail: string;
}

export interface SafetyGateResult {
  decision: "APPROVED" | "REJECTED" | "HUMAN_REVIEW" | string;
  allowed: boolean;
  action: string;
  target_service: string;
  execution_mode: "SIMULATION" | "REAL" | string;
  reason: string;
  conditions: SafetyConditionCheck[];
  allowlist_policy: Record<string, any>;
}

export interface RecoveryEvidence {
  status: "RECOVERED" | "NOT_RECOVERED" | "UNKNOWN" | "PENDING" | string;
  healthy: boolean;
  active_alerts_count: number;
  error_rate?: number | null;
  latency_ms?: number | null;
  checkout_successful?: boolean | null;
  probe_latency_ms?: number | null;
  signals_evaluated: string[];
  reasons: string[];
}

export interface RemediationResult {
  audit_id: string;
  incident_id: string;
  root_cause_service?: string | null;
  confidence: number;
  action: string;
  target_service: string;
  decision: "APPROVED" | "REJECTED" | "HUMAN_REVIEW" | string;
  execution_mode: "SIMULATION" | "REAL" | string;
  execution_status: "PENDING" | "SIMULATED_SUCCESS" | "EXECUTED_SUCCESS" | "FAILED" | "SKIPPED" | string;
  reason: string;
  recovery_status: "RECOVERED" | "NOT_RECOVERED" | "UNKNOWN" | "PENDING" | string;
  recovery_evidence?: RecoveryEvidence | null;
  safety_gate_result?: SafetyGateResult | null;
  timestamp: string;
}

export interface RemediationAudit {
  id?: number;
  audit_id: string;
  incident_id: string;
  timestamp: string;
  root_cause_service?: string | null;
  confidence: number;
  action: string;
  target_service: string;
  decision: string;
  execution_mode: string;
  execution_status: string;
  recovery_status: string;
  reason?: string;
  conditions_passed?: number;
  total_conditions?: number;
  recovery_healthy?: boolean;
  checkout_successful?: boolean | null;
  raw_payload?: Record<string, any>;
}

export interface CorrelationBenchmarkResult {
  strategy: string;
  total_alerts: number;
  incidents_count: number;
  alerts_grouped: number;
  isolated_incidents: number;
  average_incident_size: number;
  average_cohesion_score: number;
  unrelated_alerts_separated: number;
  execution_time_ms: number;
  summary: string;
  incidents: Incident[];
}

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  timestamp: string;
  shopflow: "connected" | "disconnected" | string;
  shopflow_target_url: string;
}

export interface ServiceEntity {
  id: string;
  name: string;
  type: string;
  tier: string;
  criticality: string;
  status: string;
  port?: number;
  health_endpoint?: string;
}
