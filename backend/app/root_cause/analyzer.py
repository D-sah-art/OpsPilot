import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.topology.graph import DependencyGraph, dependency_graph
from .models import RootCauseAnalysis, ConfidenceBreakdown
from .fallback import DeterministicFallbackAnalyzer
from .llm_client import LLMClient

logger = logging.getLogger("opspilot.root_cause.analyzer")

class RootCauseAnalyzer:
    """
    Orchestrates AI-assisted root-cause diagnosis with deterministic fallback.
    Ensures outputs are grounded in Phase 3 evidence, confidence is evidence-derived,
    and dangerous commands are strictly rejected.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        fallback_analyzer: Optional[DeterministicFallbackAnalyzer] = None,
        graph: Optional[DependencyGraph] = None
    ):
        self.graph = graph or dependency_graph
        self.llm_client = llm_client or LLMClient()
        self.fallback_analyzer = fallback_analyzer or DeterministicFallbackAnalyzer(graph=self.graph)

    def analyze(
        self,
        incident_id: str,
        incident_data: Dict[str, Any],
        alerts: Optional[List[Dict[str, Any]]] = None,
        force_fallback: bool = False
    ) -> RootCauseAnalysis:
        """
        Executes root cause diagnosis:
        1. Recalls relevant historical incident memories from Hindsight.
        2. Tries LLM with recalled memory context if configured and not force_fallback.
        3. Seamlessly falls back to deterministic analyzer upon any failure or rejection.
        4. Attaches Hindsight memory metadata to the diagnosis result.
        """
        from app.memory.service import memory_service
        recall_result = memory_service.recall_similar_incidents(incident_data)
        
        recalled_memories_data = [m.model_dump() for m in recall_result.memories]

        if not force_fallback and self.llm_client.is_configured():
            try:
                llm_response = self.llm_client.diagnose_incident(
                    incident_data,
                    hindsight_context=recall_result.formatted_context
                )
                if llm_response:
                    evidence = incident_data.get("correlation_evidence") or {}
                    if hasattr(evidence, "model_dump"):
                        evidence = evidence.model_dump()

                    root_svc = llm_response["root_cause_service"]
                    affected_services = incident_data.get("affected_services") or []
                    causal_chain = evidence.get("causal_chain") or []
                    earliest_alert = evidence.get("earliest_alert") or {}
                    dependency_paths = evidence.get("dependency_paths") or []
                    top_pairwise = evidence.get("top_pairwise_correlations") or []
                    correlation_score = float(incident_data.get("correlation_score", 1.0))

                    # Calculate evidence-derived confidence breakdown for explainability
                    confidence_breakdown, fallback_conf = self.fallback_analyzer._calculate_confidence(
                        root_service=root_svc,
                        affected_services=affected_services,
                        causal_chain=causal_chain,
                        earliest_alert=earliest_alert,
                        dependency_paths=dependency_paths,
                        top_pairwise=top_pairwise,
                        correlation_score=correlation_score
                    )

                    # Use LLM confidence score if valid in [0.0, 1.0], else fallback confidence
                    raw_conf = llm_response.get("confidence_score")
                    if isinstance(raw_conf, (int, float)) and 0.0 <= raw_conf <= 1.0:
                        conf_score = round(float(raw_conf), 3)
                    else:
                        conf_score = fallback_conf

                    logger.info(f"Successfully diagnosed incident '{incident_id}' using LLM ({self.llm_client.model}) with {recall_result.memories_recalled} recalled Hindsight memories")
                    return RootCauseAnalysis(
                        incident_id=incident_id,
                        root_cause_service=root_svc,
                        root_cause_summary=llm_response["root_cause_summary"],
                        confidence_score=conf_score,
                        confidence_breakdown=confidence_breakdown,
                        causal_narrative=llm_response["causal_narrative"],
                        propagation_path=llm_response.get("propagation_path", []),
                        evidence_summary=llm_response.get("evidence_summary", []),
                        recommended_action=llm_response["recommended_action"],
                        analysis_mode="llm",
                        model_used=self.llm_client.model,
                        diagnosed_at=datetime.now(timezone.utc).isoformat(),
                        memory_enabled=recall_result.enabled,
                        memories_recalled=recall_result.memories_recalled,
                        memory_status=recall_result.status,
                        recalled_memories=recalled_memories_data,
                    )
            except Exception as e:
                logger.warning(f"LLM diagnosis attempt failed, engaging deterministic fallback: {e}")

        # Deterministic Fallback
        logger.info(f"Diagnosing incident '{incident_id}' using deterministic fallback analyzer")
        fallback_res = self.fallback_analyzer.analyze(
            incident_id=incident_id,
            incident_data=incident_data,
            alerts=alerts
        )
        fallback_res.memory_enabled = recall_result.enabled
        fallback_res.memories_recalled = recall_result.memories_recalled
        fallback_res.memory_status = recall_result.status
        fallback_res.recalled_memories = recalled_memories_data
        return fallback_res

