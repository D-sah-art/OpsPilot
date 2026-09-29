from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid

def default_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()

class PairwiseScore(BaseModel):
    alert_a_id: str
    alert_b_id: str
    service_a: str
    service_b: str
    total_score: float
    dependency_score: float
    graph_distance_score: float
    causal_order_score: float
    temporal_score: float
    service_score: float
    alert_type_score: float
    severity_score: float
    tag_and_metric_score: float
    reasons: List[str] = Field(default_factory=list)

class CorrelationEvidence(BaseModel):
    temporal_span_seconds: float = 0.0
    earliest_alert: Dict[str, Any] = Field(default_factory=dict)
    latest_alert: Dict[str, Any] = Field(default_factory=dict)
    dependency_paths: List[List[str]] = Field(default_factory=list)
    causal_chain: List[Dict[str, Any]] = Field(default_factory=list)
    primary_affected_services: List[str] = Field(default_factory=list)
    alert_type_breakdown: Dict[str, int] = Field(default_factory=dict)
    severity_breakdown: Dict[str, int] = Field(default_factory=dict)
    top_pairwise_correlations: List[Dict[str, Any]] = Field(default_factory=list)

class Incident(BaseModel):
    incident_id: str = Field(default_factory=lambda: f"inc_{uuid.uuid4().hex[:10]}")
    title: str
    severity: str = "CRITICAL"
    status: str = "OPEN"
    created_at: str = Field(default_factory=default_timestamp)
    updated_at: str = Field(default_factory=default_timestamp)
    resolved_at: Optional[str] = None
    alert_count: int = 0
    alert_ids: List[str] = Field(default_factory=list)
    affected_services: List[str] = Field(default_factory=list)
    correlation_score: float = 1.0
    correlation_method: str = "dependency_aware"
    correlation_evidence: CorrelationEvidence = Field(default_factory=CorrelationEvidence)

class CorrelationBenchmarkResult(BaseModel):
    strategy: str
    total_alerts: int
    incidents_count: int
    alerts_grouped: int
    isolated_incidents: int
    average_incident_size: float
    average_cohesion_score: float
    unrelated_alerts_separated: int
    execution_time_ms: float
    summary: str
    incidents: List[Incident] = Field(default_factory=list)

class CorrelationRequest(BaseModel):
    strategy: str = "dependency_aware"  # "dependency_aware" or "time_only"
    persist: bool = True
    time_window_seconds: float = 600.0
    threshold: float = 0.45
