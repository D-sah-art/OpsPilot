from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

def default_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()

class ConfidenceBreakdown(BaseModel):
    topological_clarity: float = Field(default=0.0, ge=0.0, le=1.0, description="Clarity of directed dependency path to root service")
    causal_consistency: float = Field(default=0.0, ge=0.0, le=1.0, description="Earliest alert temporal and causal alignment")
    evidence_completeness: float = Field(default=0.0, ge=0.0, le=1.0, description="Presence of pairwise scores, metrics, and logs")
    symptom_breadth: float = Field(default=0.0, ge=0.0, le=1.0, description="Symptom propagation coverage across dependent tiers")
    correlation_cohesion: float = Field(default=0.0, ge=0.0, le=1.0, description="Cohesion score from Phase 3 correlation")
    weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "topological_clarity": 0.30,
            "causal_consistency": 0.25,
            "evidence_completeness": 0.20,
            "symptom_breadth": 0.15,
            "correlation_cohesion": 0.10
        }
    )
    formula: str = "0.30*topological + 0.25*causal + 0.20*evidence + 0.15*symptoms + 0.10*cohesion"

class RootCauseAnalysis(BaseModel):
    incident_id: str
    root_cause_service: str
    root_cause_summary: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_breakdown: ConfidenceBreakdown
    causal_narrative: str
    propagation_path: List[str] = Field(default_factory=list)
    evidence_summary: List[str] = Field(default_factory=list)
    recommended_action: str
    analysis_mode: str = "deterministic_fallback"  # "llm" or "deterministic_fallback"
    model_used: Optional[str] = None
    diagnosed_at: str = Field(default_factory=default_timestamp)
    # Hindsight Memory System Observability Fields
    memory_enabled: bool = False
    connection_status: str = "CONNECTED_TO_HINDSIGHT"
    memory_source: str = "Vectorize Hindsight Engine"
    memories_recalled: int = 0
    memory_status: str = "IDLE"
    recalled_memories: List[Dict[str, Any]] = Field(default_factory=list)


class RootCauseRequest(BaseModel):
    force_refresh: bool = False
    force_fallback: bool = False
