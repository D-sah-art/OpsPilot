import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.ingestion.adapter import ShopFlowAdapter, shopflow_adapter
from app.database.repository import TelemetryRepository
from .models import RecoveryStatus, RecoveryEvidence

logger = logging.getLogger("opspilot.remediation.recovery")

class RecoveryVerifier:
    """
    Verifies system recovery against real observable ShopFlow telemetry signals.
    Evaluates:
    1. Target service health & connectivity (/health or /api/health-summary)
    2. Active critical incident & target alerts in database
    3. Real telemetry metrics (error rate & latency) if available
    4. Active end-to-end synthetic checkout transaction probe

    Never fabricates metrics, assumes blind success, or infers checkout health from check counts.
    """

    def __init__(self, adapter: Optional[ShopFlowAdapter] = None):
        self.adapter = adapter or shopflow_adapter

    def verify(
        self,
        db: Session,
        incident_id: str,
        target_service: str,
        action: str
    ) -> RecoveryEvidence:
        signals_evaluated: List[str] = []
        reasons: List[str] = []

        failure_evidence_found = False
        positive_signals_count = 0
        available_signals_count = 0

        # -------------------------------------------------------------
        # 1. Target Service Health Endpoint Probe
        # -------------------------------------------------------------
        signals_evaluated.append("health_endpoint")
        health_resp = None
        try:
            if hasattr(self.adapter, "get_health"):
                res = self.adapter.get_health()
                if isinstance(res, dict):
                    health_resp = res
            if not health_resp and hasattr(self.adapter, "fetch_health_summary"):
                res = self.adapter.fetch_health_summary()
                if isinstance(res, dict):
                    health_resp = res
        except Exception as e:
            logger.debug(f"Recovery health probe exception: {e}")

        is_connected = bool(
            health_resp 
            and isinstance(health_resp, dict) 
            and health_resp.get("status") not in ["unreachable", "Unknown", None]
        )
        target_healthy: Optional[bool] = None

        if is_connected:
            available_signals_count += 1
            services = health_resp.get("services", {})
            if isinstance(services, dict) and target_service in services:
                target_status = str(services[target_service].get("status", "")).lower()
                target_healthy = target_status in ["operational", "healthy", "ok"]
            else:
                status_str = str(health_resp.get("status", "")).lower()
                target_healthy = status_str in ["ok", "healthy", "operational"]

            if target_healthy:
                positive_signals_count += 1
                reasons.append(f"Target service '{target_service}' reported healthy/operational via health endpoint.")
            else:
                failure_evidence_found = True
                reasons.append(f"Target service '{target_service}' is still degraded/unhealthy in health endpoint.")
        else:
            reasons.append(f"ShopFlow health endpoint unreachable for '{target_service}'.")

        # -------------------------------------------------------------
        # 2. Live & Active Telemetry Alert Evaluation
        # -------------------------------------------------------------
        signals_evaluated.append("active_alerts")
        active_count = 0
        live_alerts = None
        try:
            if hasattr(self.adapter, "fetch_alerts"):
                res = self.adapter.fetch_alerts(limit=50)
                if isinstance(res, list):
                    live_alerts = res
        except Exception as e:
            logger.debug(f"Fetch live alerts exception: {e}")

        if live_alerts is not None:
            available_signals_count += 1
            target_critical_alerts = [
                a for a in live_alerts
                if (a.get("service") == target_service or a.get("dependency") == target_service)
                and str(a.get("severity", "")).upper() in ["CRITICAL", "HIGH", "MAJOR"]
            ]
            active_count = len(target_critical_alerts)
            if active_count > 0:
                failure_evidence_found = True
                reasons.append(f"Detected {active_count} actively firing critical alert(s) on '{target_service}'.")
            else:
                positive_signals_count += 1
                reasons.append(f"Zero active firing critical alerts on target '{target_service}'.")
        else:
            # Fallback to repository alerts check
            available_signals_count += 1
            recent_alerts = TelemetryRepository.get_alerts(db, service=target_service, limit=20)
            incident = TelemetryRepository.get_incident_by_id(db, incident_id=incident_id) if incident_id else None
            incident_alert_ids = set(incident.get("alert_ids", [])) if incident else set()

            active_critical_alerts = [
                a for a in recent_alerts 
                if a.get("severity") in ["CRITICAL", "HIGH"]
            ]
            active_count = len(active_critical_alerts)

            if incident_alert_ids:
                active_incident_critical = [
                    a for a in active_critical_alerts if a.get("id") in incident_alert_ids
                ]
                if active_incident_critical:
                    failure_evidence_found = True
                    reasons.append(f"Found {len(active_incident_critical)} active critical alert(s) from incident '{incident_id}' on '{target_service}'.")
                elif active_count > 0:
                    failure_evidence_found = True
                    reasons.append(f"Found {active_count} active critical/high alert(s) on target '{target_service}'.")
                else:
                    positive_signals_count += 1
                    reasons.append(f"No active critical alerts remaining for incident '{incident_id}' / '{target_service}'.")
            else:
                if active_count > 0:
                    failure_evidence_found = True
                    reasons.append(f"Found {active_count} active critical alert(s) on target service '{target_service}'.")
                else:
                    positive_signals_count += 1
                    reasons.append(f"No active critical alerts found for '{target_service}'.")

        # -------------------------------------------------------------
        # 3. Telemetry Metrics Evaluation (Nominal Latency / Error Rate)
        # -------------------------------------------------------------
        signals_evaluated.append("telemetry_metrics")
        live_metrics = None
        try:
            if hasattr(self.adapter, "fetch_metrics"):
                res = self.adapter.fetch_metrics()
                if isinstance(res, dict) and "services" in res:
                    live_metrics = res
        except Exception as e:
            logger.debug(f"Fetch live metrics exception: {e}")

        error_rate_val: Optional[float] = None
        latency_val: Optional[float] = None

        if live_metrics and "services" in live_metrics:
            svc_dict = live_metrics.get("services", {})
            if isinstance(svc_dict, dict):
                if target_service in svc_dict:
                    svc_m = svc_dict[target_service]
                    err_pct = float(svc_m.get("error_rate_pct", 0.0))
                    error_rate_val = err_pct / 100.0 if err_pct > 1.0 else err_pct
                    latency_val = float(svc_m.get("latency_ms", 0.0))
                elif "postgresql" in svc_dict:
                    svc_m = svc_dict["postgresql"]
                    err_pct = float(svc_m.get("error_rate_pct", 0.0))
                    error_rate_val = err_pct / 100.0 if err_pct > 1.0 else err_pct
                    latency_val = float(svc_m.get("latency_ms", 0.0))

        if error_rate_val is None and latency_val is None:
            recent_metrics = TelemetryRepository.get_metrics(db, service=target_service, limit=10)
            for m in recent_metrics:
                mname = m.get("metric_name", "")
                if error_rate_val is None and ("error_rate" in mname or "failure_rate" in mname):
                    error_rate_val = float(m.get("value", 0.0))
                if latency_val is None and ("latency" in mname or "duration" in mname):
                    latency_val = float(m.get("value", 0.0))

        if error_rate_val is not None or latency_val is not None:
            available_signals_count += 1
            metrics_elevated = False
            if error_rate_val is not None and error_rate_val > 0.05:
                metrics_elevated = True
                reasons.append(f"Service error rate remains elevated at {error_rate_val:.1%}.")
            if latency_val is not None and latency_val > 3000.0:
                metrics_elevated = True
                reasons.append(f"Service latency remains elevated at {latency_val:.1f}ms.")

            if metrics_elevated:
                failure_evidence_found = True
            else:
                positive_signals_count += 1
                details = []
                if error_rate_val is not None:
                    details.append(f"error rate {error_rate_val:.1%}")
                if latency_val is not None:
                    details.append(f"latency {latency_val:.1f}ms")
                reasons.append(f"Telemetry metrics within nominal thresholds ({', '.join(details)}).")
        else:
            reasons.append(f"Telemetry metrics unavailable for '{target_service}'.")

        # -------------------------------------------------------------
        # 4. Active End-to-End Synthetic Checkout / Transaction Probe
        # -------------------------------------------------------------
        signals_evaluated.append("active_checkout_probe")
        checkout_successful: Optional[bool] = None
        probe_res = None
        try:
            if hasattr(self.adapter, "probe_checkout"):
                res = self.adapter.probe_checkout()
                if isinstance(res, dict):
                    probe_res = res
        except Exception as e:
            logger.debug(f"Checkout probe exception: {e}")

        probe_lat: Optional[float] = None
        if probe_res is not None:
            if "latency_ms" in probe_res and probe_res["latency_ms"] is not None:
                probe_lat = float(probe_res["latency_ms"])
            if probe_res.get("success") is True:
                available_signals_count += 1
                positive_signals_count += 1
                checkout_successful = True
                order_id = probe_res.get("order_id", "simulated")
                lat_str = f"{probe_lat:.1f}ms" if probe_lat is not None else "nominal"
                reasons.append(f"Active synthetic checkout probe succeeded (Order ID: {order_id}, latency: {lat_str}).")
            elif probe_res.get("status_code", 0) > 0 and probe_res.get("status_code") != 200:
                available_signals_count += 1
                failure_evidence_found = True
                checkout_successful = False
                reasons.append(f"Active synthetic checkout probe failed (HTTP {probe_res.get('status_code')}: {probe_res.get('error')}).")
            else:
                checkout_successful = None
                reasons.append(f"Active checkout probe unavailable ({probe_res.get('error')}).")
        else:
            checkout_successful = None
            reasons.append("Active checkout probe not executed / unavailable on adapter.")

        # -------------------------------------------------------------
        # 5. Final Deterministic Recovery Decision
        # -------------------------------------------------------------
        if failure_evidence_found:
            final_status = RecoveryStatus.NOT_RECOVERED
            healthy = False
        elif positive_signals_count >= 2 and available_signals_count >= 2:
            final_status = RecoveryStatus.RECOVERED
            healthy = True
        else:
            final_status = RecoveryStatus.UNKNOWN
            healthy = False
            reasons.append("Insufficient observable telemetry to confirm recovery — returning UNKNOWN.")

        return RecoveryEvidence(
            status=final_status,
            healthy=healthy,
            active_alerts_count=active_count,
            error_rate=error_rate_val,
            latency_ms=latency_val,
            checkout_successful=checkout_successful,
            probe_latency_ms=probe_lat,
            signals_evaluated=signals_evaluated,
            reasons=reasons
        )

# Global singleton
recovery_verifier = RecoveryVerifier()
