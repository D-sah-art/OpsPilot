from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from app.database.session import get_db
from app.database.repository import TelemetryRepository

router = APIRouter(prefix="/api", tags=["Alerts"])

@router.get("/alerts")
def get_alerts(
    limit: int = Query(100, ge=1, le=1000),
    service: Optional[str] = None,
    severity: Optional[str] = None,
    alert_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Returns stored alerts from SQLite with filtering."""
    return TelemetryRepository.get_alerts(
        db=db,
        limit=limit,
        service=service,
        severity=severity,
        alert_type=alert_type
    )
