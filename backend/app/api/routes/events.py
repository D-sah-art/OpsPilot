from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from app.database.session import get_db
from app.database.repository import TelemetryRepository

router = APIRouter(prefix="/api", tags=["Events"])

@router.get("/events")
def get_events(
    limit: int = Query(100, ge=1, le=1000),
    service: Optional[str] = None,
    event_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Returns stored system events."""
    return TelemetryRepository.get_events(
        db=db,
        limit=limit,
        service=service,
        event_type=event_type
    )
