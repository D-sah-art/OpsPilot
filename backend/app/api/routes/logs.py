from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from app.database.session import get_db
from app.database.repository import TelemetryRepository

router = APIRouter(prefix="/api", tags=["Logs"])

@router.get("/logs")
def get_logs(
    limit: int = Query(100, ge=1, le=1000),
    service: Optional[str] = None,
    level: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Returns stored structured JSON logs."""
    return TelemetryRepository.get_logs(
        db=db,
        limit=limit,
        service=service,
        level=level,
        search=search
    )
