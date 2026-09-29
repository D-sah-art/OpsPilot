from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from .models import ServiceModel, DependencyModel, AlertModel, MetricModel, LogModel, EventModel, IncidentModel, RemediationAuditModel
from app.models import Alert, Metric, LogEvent, SystemEvent, Service, Dependency

class TelemetryRepository:

    # ---------------- SERVICES ----------------
    @staticmethod
    def upsert_service(db: Session, service: Service) -> ServiceModel:
        existing = db.query(ServiceModel).filter(ServiceModel.service_id == service.service_id).first()
        if existing:
            existing.name = service.name
            existing.type = service.type
            existing.status = service.status
            existing.metadata_json = service.metadata
            db.commit()
            db.refresh(existing)
            return existing
        else:
            model = ServiceModel(
                service_id=service.service_id,
                name=service.name,
                type=service.type,
                status=service.status,
                metadata_json=service.metadata
            )
            db.add(model)
            db.commit()
            db.refresh(model)
            return model

    @staticmethod
    def get_services(db: Session) -> List[Dict[str, Any]]:
        rows = db.query(ServiceModel).all()
        return [
            {
                "service_id": r.service_id,
                "name": r.name,
                "type": r.type,
                "status": r.status,
                "metadata": r.metadata_json or {},
                "updated_at": r.updated_at.isoformat() if r.updated_at else None
            }
            for r in rows
        ]

    # ---------------- DEPENDENCIES ----------------
    @staticmethod
    def upsert_dependency(db: Session, dep: Dependency) -> DependencyModel:
        existing = db.query(DependencyModel).filter(
            DependencyModel.source == dep.source,
            DependencyModel.target == dep.target
        ).first()
        if existing:
            existing.relationship = dep.relationship
            existing.metadata_json = dep.metadata
            db.commit()
            db.refresh(existing)
            return existing
        else:
            model = DependencyModel(
                source=dep.source,
                target=dep.target,
                relationship=dep.relationship,
                metadata_json=dep.metadata
            )
            db.add(model)
            db.commit()
            db.refresh(model)
            return model

    @staticmethod
    def get_dependencies(db: Session) -> List[Dict[str, Any]]:
        rows = db.query(DependencyModel).all()
        return [
            {
                "source": r.source,
                "target": r.target,
                "relationship": r.relationship,
                "metadata": r.metadata_json or {}
            }
            for r in rows
        ]

    # ---------------- ALERTS ----------------
    @staticmethod
    def save_alerts(db: Session, alerts: List[Alert]) -> int:
        if not alerts:
            return 0
        new_count = 0
        for alert in alerts:
            # Check duplicate by alert_id
            existing = db.query(AlertModel).filter(AlertModel.alert_id == alert.id).first()
            if not existing:
                model = AlertModel(
                    alert_id=alert.id,
                    timestamp=alert.timestamp,
                    service=alert.service,
                    severity=alert.severity,
                    alert_type=alert.alert_type,
                    metric=alert.metric,
                    metric_value=alert.metric_value,
                    threshold=alert.threshold,
                    message=alert.message,
                    source=alert.source,
                    dependency=alert.dependency,
                    tags_json=alert.tags,
                    raw_payload_json=alert.raw_payload
                )
                db.add(model)
                new_count += 1
        if new_count > 0:
            db.commit()
        return new_count

    @staticmethod
    def get_alerts(
        db: Session,
        limit: int = 100,
        service: Optional[str] = None,
        severity: Optional[str] = None,
        alert_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = db.query(AlertModel)
        if service:
            query = query.filter(AlertModel.service == service)
        if severity:
            query = query.filter(AlertModel.severity == severity.upper())
        if alert_type:
            query = query.filter(AlertModel.alert_type == alert_type)
        
        rows = query.order_by(desc(AlertModel.timestamp)).limit(limit).all()
        return [
            {
                "id": r.alert_id,
                "timestamp": r.timestamp,
                "service": r.service,
                "severity": r.severity,
                "alert_type": r.alert_type,
                "metric": r.metric,
                "metric_value": r.metric_value,
                "threshold": r.threshold,
                "message": r.message,
                "source": r.source,
                "dependency": r.dependency,
                "tags": r.tags_json or {},
                "raw_payload": r.raw_payload_json or {}
            }
            for r in rows
        ]

    # ---------------- METRICS ----------------
    @staticmethod
    def save_metrics(db: Session, metrics: List[Metric]) -> int:
        if not metrics:
            return 0
        new_count = 0
        for m in metrics:
            model = MetricModel(
                timestamp=m.timestamp,
                service=m.service,
                metric_name=m.metric_name,
                value=m.value,
                unit=m.unit,
                tags_json=m.tags,
                raw_payload_json=m.raw_payload
            )
            db.add(model)
            new_count += 1
        if new_count > 0:
            db.commit()
        return new_count

    @staticmethod
    def get_metrics(
        db: Session,
        limit: int = 100,
        service: Optional[str] = None,
        metric_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = db.query(MetricModel)
        if service:
            query = query.filter(MetricModel.service == service)
        if metric_name:
            query = query.filter(MetricModel.metric_name == metric_name)
        
        rows = query.order_by(desc(MetricModel.timestamp)).limit(limit).all()
        return [
            {
                "timestamp": r.timestamp,
                "service": r.service,
                "metric_name": r.metric_name,
                "value": r.value,
                "unit": r.unit,
                "tags": r.tags_json or {},
                "raw_payload": r.raw_payload_json or {}
            }
            for r in rows
        ]

    # ---------------- LOGS ----------------
    @staticmethod
    def save_logs(db: Session, logs: List[LogEvent]) -> int:
        if not logs:
            return 0
        new_count = 0
        for log in logs:
            # Check duplicate by log_id
            existing = db.query(LogModel).filter(LogModel.log_id == log.id).first()
            if not existing:
                model = LogModel(
                    log_id=log.id,
                    timestamp=log.timestamp,
                    service=log.service,
                    level=log.level,
                    event=log.event,
                    message=log.message,
                    request_id=log.request_id,
                    dependency=log.dependency,
                    latency_ms=log.latency_ms,
                    status_code=log.status_code,
                    metadata_json=log.metadata,
                    raw_payload_json=log.raw_payload
                )
                db.add(model)
                new_count += 1
        if new_count > 0:
            db.commit()
        return new_count

    @staticmethod
    def get_logs(
        db: Session,
        limit: int = 100,
        service: Optional[str] = None,
        level: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = db.query(LogModel)
        if service:
            query = query.filter(LogModel.service == service)
        if level:
            query = query.filter(LogModel.level == level.upper())
        if search:
            query = query.filter(LogModel.message.contains(search) | LogModel.event.contains(search))
        
        rows = query.order_by(desc(LogModel.timestamp)).limit(limit).all()
        return [
            {
                "id": r.log_id,
                "timestamp": r.timestamp,
                "service": r.service,
                "level": r.level,
                "event": r.event,
                "message": r.message,
                "request_id": r.request_id,
                "dependency": r.dependency,
                "latency_ms": r.latency_ms,
                "status_code": r.status_code,
                "metadata": r.metadata_json or {},
                "raw_payload": r.raw_payload_json or {}
            }
            for r in rows
        ]

    # ---------------- EVENTS ----------------
    @staticmethod
    def save_events(db: Session, events: List[SystemEvent]) -> int:
        if not events:
            return 0
        new_count = 0
        for ev in events:
            existing = db.query(EventModel).filter(EventModel.event_id == ev.id).first()
            if not existing:
                model = EventModel(
                    event_id=ev.id,
                    timestamp=ev.timestamp,
                    service=ev.service,
                    event_type=ev.event_type,
                    message=ev.message,
                    metadata_json=ev.metadata,
                    raw_payload_json=ev.raw_payload
                )
                db.add(model)
                new_count += 1
        if new_count > 0:
            db.commit()
        return new_count

    @staticmethod
    def get_events(
        db: Session,
        limit: int = 100,
        service: Optional[str] = None,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = db.query(EventModel)
        if service:
            query = query.filter(EventModel.service == service)
        if event_type:
            query = query.filter(EventModel.event_type == event_type)
        
        rows = query.order_by(desc(EventModel.timestamp)).limit(limit).all()
        return [
            {
                "id": r.event_id,
                "timestamp": r.timestamp,
                "service": r.service,
                "event_type": r.event_type,
                "message": r.message,
                "metadata": r.metadata_json or {},
                "raw_payload": r.raw_payload_json or {}
            }
            for r in rows
        ]

    # ---------------- INCIDENTS ----------------
    @staticmethod
    def save_incidents(db: Session, incidents: List[Any]) -> int:
        if not incidents:
            return 0
        new_count = 0
        for inc in incidents:
            if isinstance(inc, dict):
                inc_id = inc.get("incident_id")
                title = inc.get("title", "Incident")
                severity = inc.get("severity", "CRITICAL")
                status = inc.get("status", "OPEN")
                started_at = inc.get("created_at") or inc.get("started_at")
                updated_at = inc.get("updated_at")
                resolved_at = inc.get("resolved_at")
                alert_count = inc.get("alert_count", 0)
                alert_ids = inc.get("alert_ids", [])
                affected_services = inc.get("affected_services", [])
                correlation_score = inc.get("correlation_score", 1.0)
                correlation_method = inc.get("correlation_method", "dependency_aware")
                evidence = inc.get("correlation_evidence", {})
            else:
                inc_id = inc.incident_id
                title = inc.title
                severity = inc.severity
                status = inc.status
                started_at = inc.created_at
                updated_at = inc.updated_at
                resolved_at = inc.resolved_at
                alert_count = inc.alert_count
                alert_ids = inc.alert_ids
                affected_services = inc.affected_services
                correlation_score = inc.correlation_score
                correlation_method = inc.correlation_method
                evidence = inc.correlation_evidence

            if hasattr(evidence, "model_dump"):
                evidence = evidence.model_dump()

            existing = db.query(IncidentModel).filter(IncidentModel.incident_id == inc_id).first()
            if existing:
                existing.title = title
                existing.severity = severity
                existing.status = status
                existing.started_at = started_at
                existing.updated_at = updated_at
                existing.resolved_at = resolved_at
                existing.alert_count = alert_count
                existing.alert_ids_json = alert_ids
                existing.affected_services_json = affected_services
                existing.correlation_score = correlation_score
                existing.correlation_method = correlation_method
                existing.evidence_json = evidence
            else:
                model = IncidentModel(
                    incident_id=inc_id,
                    title=title,
                    severity=severity,
                    status=status,
                    started_at=started_at,
                    updated_at=updated_at,
                    resolved_at=resolved_at,
                    alert_count=alert_count,
                    alert_ids_json=alert_ids,
                    affected_services_json=affected_services,
                    correlation_score=correlation_score,
                    correlation_method=correlation_method,
                    evidence_json=evidence
                )
                db.add(model)
                new_count += 1
        db.commit()
        return new_count

    @staticmethod
    def get_incidents(
        db: Session,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        query = db.query(IncidentModel)
        if status:
            query = query.filter(IncidentModel.status == status.upper())
        if severity:
            query = query.filter(IncidentModel.severity == severity.upper())
        
        rows = query.order_by(desc(IncidentModel.created_at)).limit(limit).all()
        return [
            {
                "incident_id": r.incident_id,
                "title": r.title,
                "severity": r.severity,
                "status": r.status,
                "created_at": r.started_at,
                "updated_at": r.updated_at or r.started_at,
                "resolved_at": r.resolved_at,
                "alert_count": r.alert_count,
                "alert_ids": r.alert_ids_json or [],
                "affected_services": r.affected_services_json or [],
                "correlation_score": r.correlation_score,
                "correlation_method": r.correlation_method,
                "correlation_evidence": r.evidence_json or {},
                "root_cause_service": r.root_cause_service,
                "summary": r.summary,
                "diagnosis": r.diagnosis_json or {}
            }
            for r in rows
        ]

    @staticmethod
    def get_incident_by_id(db: Session, incident_id: str) -> Optional[Dict[str, Any]]:
        r = db.query(IncidentModel).filter(IncidentModel.incident_id == incident_id).first()
        if not r:
            return None
        return {
            "incident_id": r.incident_id,
            "title": r.title,
            "severity": r.severity,
            "status": r.status,
            "created_at": r.started_at,
            "updated_at": r.updated_at or r.started_at,
            "resolved_at": r.resolved_at,
            "alert_count": r.alert_count,
            "alert_ids": r.alert_ids_json or [],
            "affected_services": r.affected_services_json or [],
            "correlation_score": r.correlation_score,
            "correlation_method": r.correlation_method,
            "correlation_evidence": r.evidence_json or {},
            "root_cause_service": r.root_cause_service,
            "summary": r.summary,
            "diagnosis": r.diagnosis_json or {}
        }

    @staticmethod
    def save_incident_diagnosis(db: Session, incident_id: str, diagnosis: Dict[str, Any]) -> bool:
        r = db.query(IncidentModel).filter(IncidentModel.incident_id == incident_id).first()
        if not r:
            return False
        r.diagnosis_json = diagnosis
        if "root_cause_service" in diagnosis and diagnosis["root_cause_service"]:
            r.root_cause_service = diagnosis["root_cause_service"]
        if "summary" in diagnosis and diagnosis["summary"]:
            r.summary = diagnosis["summary"]
        db.commit()
        db.refresh(r)
        return True

    @staticmethod
    def get_incident_diagnosis(db: Session, incident_id: str) -> Optional[Dict[str, Any]]:
        r = db.query(IncidentModel).filter(IncidentModel.incident_id == incident_id).first()
        if not r or not r.diagnosis_json:
            return None
        return r.diagnosis_json

    @staticmethod
    def update_incident_status(
        db: Session,
        incident_id: str,
        status: str,
        resolved_at: Optional[str] = None
    ) -> bool:
        r = db.query(IncidentModel).filter(IncidentModel.incident_id == incident_id).first()
        if not r:
            return False
        r.status = status
        if resolved_at:
            r.resolved_at = resolved_at
        db.commit()
        db.refresh(r)
        return True

    @staticmethod
    def delete_incidents(db: Session):
        db.query(IncidentModel).delete()
        db.commit()

    # ---------------- REMEDIATION & AUDIT TRAIL ----------------
    @staticmethod
    def save_audit_record(db: Session, audit_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Appends an immutable remediation audit record to SQLite database.
        """
        model = RemediationAuditModel(
            audit_id=audit_data.get("audit_id"),
            incident_id=audit_data.get("incident_id"),
            timestamp=audit_data.get("timestamp"),
            root_cause_service=audit_data.get("root_cause_service"),
            confidence=audit_data.get("confidence", 0.0),
            action=audit_data.get("action"),
            target_service=audit_data.get("target_service"),
            decision=audit_data.get("decision"),
            reason=audit_data.get("reason", ""),
            execution_mode=audit_data.get("execution_mode", "SIMULATION"),
            execution_status=audit_data.get("execution_status", "PENDING"),
            recovery_status=audit_data.get("recovery_status", "UNKNOWN"),
            actor=audit_data.get("actor", "opspilot-remediation-engine"),
            allowlist_policy_json=audit_data.get("allowlist_policy", {}),
            details_json=audit_data.get("details", {})
        )
        db.add(model)
        db.commit()
        db.refresh(model)
        return {
            "audit_id": model.audit_id,
            "incident_id": model.incident_id,
            "timestamp": model.timestamp,
            "root_cause_service": model.root_cause_service,
            "confidence": model.confidence,
            "action": model.action,
            "target_service": model.target_service,
            "decision": model.decision,
            "reason": model.reason,
            "execution_mode": model.execution_mode,
            "execution_status": model.execution_status,
            "recovery_status": model.recovery_status,
            "actor": model.actor,
            "allowlist_policy": model.allowlist_policy_json or {},
            "details": model.details_json or {},
            "created_at": model.created_at.isoformat() if model.created_at else None
        }

    @staticmethod
    def get_audits_for_incident(
        db: Session,
        incident_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        rows = db.query(RemediationAuditModel)\
            .filter(RemediationAuditModel.incident_id == incident_id)\
            .order_by(desc(RemediationAuditModel.created_at))\
            .limit(limit)\
            .all()
        return [
            {
                "audit_id": r.audit_id,
                "incident_id": r.incident_id,
                "timestamp": r.timestamp,
                "root_cause_service": r.root_cause_service,
                "confidence": r.confidence,
                "action": r.action,
                "target_service": r.target_service,
                "decision": r.decision,
                "reason": r.reason,
                "execution_mode": r.execution_mode,
                "execution_status": r.execution_status,
                "recovery_status": r.recovery_status,
                "actor": r.actor,
                "allowlist_policy": r.allowlist_policy_json or {},
                "details": r.details_json or {},
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in rows
        ]

    @staticmethod
    def get_latest_audit_for_incident(
        db: Session,
        incident_id: str
    ) -> Optional[Dict[str, Any]]:
        r = db.query(RemediationAuditModel)\
            .filter(RemediationAuditModel.incident_id == incident_id)\
            .order_by(desc(RemediationAuditModel.created_at))\
            .first()
        if not r:
            return None
        return {
            "audit_id": r.audit_id,
            "incident_id": r.incident_id,
            "timestamp": r.timestamp,
            "root_cause_service": r.root_cause_service,
            "confidence": r.confidence,
            "action": r.action,
            "target_service": r.target_service,
            "decision": r.decision,
            "reason": r.reason,
            "execution_mode": r.execution_mode,
            "execution_status": r.execution_status,
            "recovery_status": r.recovery_status,
            "actor": r.actor,
            "allowlist_policy": r.allowlist_policy_json or {},
            "details": r.details_json or {},
            "created_at": r.created_at.isoformat() if r.created_at else None
        }

    @staticmethod
    def get_all_audits(
        db: Session,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        rows = db.query(RemediationAuditModel)\
            .order_by(desc(RemediationAuditModel.created_at))\
            .limit(limit)\
            .all()
        return [
            {
                "audit_id": r.audit_id,
                "incident_id": r.incident_id,
                "timestamp": r.timestamp,
                "root_cause_service": r.root_cause_service,
                "confidence": r.confidence,
                "action": r.action,
                "target_service": r.target_service,
                "decision": r.decision,
                "reason": r.reason,
                "execution_mode": r.execution_mode,
                "execution_status": r.execution_status,
                "recovery_status": r.recovery_status,
                "actor": r.actor,
                "allowlist_policy": r.allowlist_policy_json or {},
                "details": r.details_json or {},
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in rows
        ]

    @staticmethod
    def clear_all(db: Session):
        db.query(RemediationAuditModel).delete()
        db.query(IncidentModel).delete()
        db.query(AlertModel).delete()
        db.query(MetricModel).delete()
        db.query(LogModel).delete()
        db.query(EventModel).delete()
        db.query(DependencyModel).delete()
        db.query(ServiceModel).delete()
        db.commit()
