from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from app.database.session import get_db
from app.correlation.service import correlation_service
from app.correlation.models import CorrelationRequest
from app.database.repository import TelemetryRepository
from app.models.alert import Alert

router = APIRouter(prefix="/api/correlation", tags=["Correlation"])

@router.post("", summary="Run telemetry correlation")
@router.post("/run", summary="Run telemetry correlation")
def run_correlation(
    request: Optional[CorrelationRequest] = None,
    strategy: Optional[str] = Query(None),
    persist: bool = Query(True),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    req = request or CorrelationRequest()
    chosen_strategy = strategy or req.strategy

    incidents = correlation_service.correlate_from_db(
        db=db,
        strategy_name=chosen_strategy,
        time_window_seconds=req.time_window_seconds,
        threshold=req.threshold,
        persist=persist
    )

    return {
        "status": "success",
        "strategy": chosen_strategy,
        "incidents_count": len(incidents),
        "incidents": [inc.model_dump() for inc in incidents]
    }

@router.get("/benchmark", summary="Benchmark Time-Only vs Dependency-Aware Correlation")
def get_correlation_benchmark(db: Session = Depends(get_db)) -> Dict[str, Any]:
    raw_alerts = TelemetryRepository.get_alerts(db, limit=1000)
    alerts = [
        Alert(
            id=a["id"],
            timestamp=a["timestamp"],
            service=a["service"],
            severity=a["severity"],
            alert_type=a["alert_type"],
            metric=a["metric"],
            metric_value=a["metric_value"],
            threshold=a["threshold"],
            message=a["message"],
            source=a.get("source", "shopflow-telemetry-agent"),
            dependency=a.get("dependency"),
            tags=a.get("tags", {}),
            raw_payload=a.get("raw_payload", {})
        )
        for a in raw_alerts
    ]

    benchmark_results = correlation_service.run_benchmark(alerts)

    return {
        "total_alerts": len(alerts),
        "benchmark": {
            k: v.model_dump() for k, v in benchmark_results.items()
        }
    }
