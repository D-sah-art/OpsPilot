import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.database.repository import TelemetryRepository
from .models import RootCauseAnalysis
from .analyzer import RootCauseAnalyzer

logger = logging.getLogger("opspilot.root_cause.service")

class RootCauseService:
    def __init__(self, analyzer: Optional[RootCauseAnalyzer] = None):
        self.analyzer = analyzer or RootCauseAnalyzer()

    def diagnose_incident(
        self,
        db: Session,
        incident_id: str,
        force_refresh: bool = False,
        force_fallback: bool = False
    ) -> RootCauseAnalysis:
        """
        Diagnoses an incident and caches the result into SQLite persistence.
        If cached result exists and force_refresh is False, returns the cached diagnosis.
        """
        incident = TelemetryRepository.get_incident_by_id(db, incident_id=incident_id)
        if not incident:
            raise ValueError(f"Incident '{incident_id}' not found")

        # Check existing cache
        if not force_refresh:
            cached_diagnosis = incident.get("diagnosis")
            if cached_diagnosis and cached_diagnosis.get("root_cause_service"):
                logger.info(f"Returning cached diagnosis for incident '{incident_id}'")
                return RootCauseAnalysis(**cached_diagnosis)

        # Retrieve linked alerts for context
        alert_ids = set(incident.get("alert_ids", []))
        all_alerts = TelemetryRepository.get_alerts(db, limit=1000)
        linked_alerts = [a for a in all_alerts if a["id"] in alert_ids]

        # Perform analysis
        analysis = self.analyzer.analyze(
            incident_id=incident_id,
            incident_data=incident,
            alerts=linked_alerts,
            force_fallback=force_fallback
        )

        # Persist diagnosis cache into DB
        TelemetryRepository.save_incident_diagnosis(
            db=db,
            incident_id=incident_id,
            diagnosis=analysis.model_dump()
        )

        return analysis

    def get_diagnosis(self, db: Session, incident_id: str) -> Optional[RootCauseAnalysis]:
        """Retrieves existing cached diagnosis if available."""
        cached = TelemetryRepository.get_incident_diagnosis(db, incident_id=incident_id)
        if cached and cached.get("root_cause_service"):
            return RootCauseAnalysis(**cached)
        return None

# Singleton instance
root_cause_service = RootCauseService()
