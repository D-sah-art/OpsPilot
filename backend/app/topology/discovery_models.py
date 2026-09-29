from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

def current_iso_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()

class DiscoveredNode(BaseModel):
    id: str
    name: str
    type: str = "service"
    tier: str = "core"
    criticality: str = "medium"
    status: str = "Operational"
    first_seen: str = Field(default_factory=current_iso_timestamp)
    last_seen: str = Field(default_factory=current_iso_timestamp)
    observation_count: int = 1
    sources: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "tier": self.tier,
            "criticality": self.criticality,
            "status": self.status,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "observation_count": self.observation_count,
            "sources": self.sources,
        }
        d.update(self.metadata)
        return d

class DiscoveredEdge(BaseModel):
    source: str
    target: str
    protocol: str = "HTTP"
    type: str = "sync"
    criticality: str = "medium"
    observed: bool = True
    evidence_count: int = 1
    first_observed: str = Field(default_factory=current_iso_timestamp)
    last_observed: str = Field(default_factory=current_iso_timestamp)
    confidence: float = 0.50
    evidence_sources: List[str] = Field(default_factory=list)
    sample_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "source": self.source,
            "target": self.target,
            "protocol": self.protocol,
            "type": self.type,
            "criticality": self.criticality,
            "observed": self.observed,
            "evidence_count": self.evidence_count,
            "first_observed": self.first_observed,
            "last_observed": self.last_observed,
            "confidence": round(self.confidence, 4),
            "evidence_sources": self.evidence_sources,
            "sample_evidence": self.sample_evidence[-3:],
        }
        d.update(self.metadata)
        return d

class DiscoveredTopologyResult(BaseModel):
    source: str = "discovered"  # "discovered" or "fallback"
    discovered_at: str = Field(default_factory=current_iso_timestamp)
    discovery_source: str = "Observed Runtime Telemetry"
    grafana_connected: bool = False
    grafana_status: str = "offline"
    total_nodes: int = 0
    total_edges: int = 0
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_summary: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = self.model_dump()
        data["evidence"] = self.evidence_summary
        return data

