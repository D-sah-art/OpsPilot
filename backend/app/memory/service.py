import logging
from typing import Dict, Any, Optional, List

from .hindsight_client import hindsight_client
from .models import HindsightRecallResult, HindsightMemoryItem

logger = logging.getLogger("opspilot.memory.service")

class MemoryService:
    """
    Application Memory Manager bridging OpsPilot AIOps workflows with Hindsight Vectorize.
    """

    def recall_similar_incidents(self, incident_data: Dict[str, Any], top_k: int = 3) -> HindsightRecallResult:
        """
        Builds a structured recall query from current incident telemetry and queries Hindsight.
        """
        incident_id = incident_data.get("id", "unknown")
        affected_services = incident_data.get("affected_services", [])
        title = incident_data.get("title", f"Incident in {', '.join(affected_services)}")
        
        # Build concise query from alerts and services
        alert_summaries = []
        for alert in incident_data.get("alerts", []):
            if isinstance(alert, dict):
                alert_summaries.append(f"{alert.get('service')}: {alert.get('alert_name')} ({alert.get('message')})")
        
        query = (
            f"Incident: {title}. "
            f"Affected Microservices: {', '.join(affected_services)}. "
            f"Alert Patterns: {'; '.join(alert_summaries[:5])}."
        )

        try:
            return hindsight_client.recall_memories(
                query=query,
                affected_services=affected_services,
                top_k=top_k
            )
        except Exception as e:
            logger.error(f"[HINDSIGHT] Unexpected recall exception: {e}")
            return HindsightRecallResult(
                enabled=hindsight_client.enabled,
                status="ERROR",
                bank_id=hindsight_client.bank_id,
                memories_recalled=0,
                memories=[],
                formatted_context="",
            )

    def retain_incident_resolution(
        self,
        incident_data: Dict[str, Any],
        root_cause_data: Dict[str, Any],
        remediation_data: Dict[str, Any],
        recovery_data: Dict[str, Any],
    ) -> bool:
        """
        Constructs a structured, sanitized operational memory of a resolved incident and retains it in Hindsight.
        """
        try:
            incident_id = incident_data.get("id", "unknown")
            affected_services = incident_data.get("affected_services", [])
            title = incident_data.get("title", f"Cascade in {', '.join(affected_services)}")

            root_svc = root_cause_data.get("root_cause_service", "unknown")
            rca_summary = root_cause_data.get("root_cause_summary", "No summary")
            action = remediation_data.get("action", remediation_data.get("remediation_action", "none"))
            is_recovered = recovery_data.get("is_recovered", False)
            recovery_details = recovery_data.get("details", {})

            # Build rich, clear operational memory summary
            content_parts = [
                f"Incident '{title}' affected microservices: {', '.join(affected_services)}.",
                f"Root Cause Analysis identified '{root_svc}' as failure origin ({rca_summary}).",
                f"Executed Safety-Gated Remediation Action: '{action}'.",
                f"Observable Recovery Verification Status: {'SUCCESSFUL (200 OK)' if is_recovered else 'UNVERIFIED'}.",
                f"System Signals: Health {recovery_details.get('health_status', 'OK')}, Active Alerts: {recovery_details.get('active_alerts_count', 0)}."
            ]

            content = " ".join(content_parts)

            success = hindsight_client.retain_incident(
                incident_id=incident_id,
                title=title,
                content=content,
                affected_services=affected_services,
                root_cause_service=root_svc,
                remediation_action=action,
                recovery_verified=is_recovered,
                tags=["opspilot", "incident_resolution", f"service:{root_svc}"],
                extra_metadata={
                    "rca_confidence": str(root_cause_data.get("confidence_score", 1.0)),
                    "safety_decision": remediation_data.get("status", "APPROVED")
                }
            )

            if success:
                logger.info(f"[HINDSIGHT] Successfully retained operational resolution for incident {incident_id}")
            return success

        except Exception as e:
            logger.error(f"[HINDSIGHT] Error retaining incident resolution: {e}")
            return False

    def clear_bank(self) -> bool:
        return hindsight_client.clear_bank()

memory_service = MemoryService()
recall_similar_incidents = memory_service.recall_similar_incidents
retain_incident_resolution = memory_service.retain_incident_resolution
