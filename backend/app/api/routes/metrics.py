from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from app.database.session import get_db
from app.database.repository import TelemetryRepository

router = APIRouter(prefix="/api", tags=["Metrics"])

@router.get("/metrics")
def get_metrics(
    limit: int = Query(100, ge=1, le=1000),
    service: Optional[str] = None,
    metric_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Returns stored metric time series data."""
    return TelemetryRepository.get_metrics(
        db=db,
        limit=limit,
        service=service,
        metric_name=metric_name
    )
