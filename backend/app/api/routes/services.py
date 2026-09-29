from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.database.session import get_db
from app.database.repository import TelemetryRepository
from app.topology.graph import dependency_graph

router = APIRouter(prefix="/api", tags=["Services"])

@router.get("/services")
def list_services(db: Session = Depends(get_db)):
    """Returns all monitored services registered in OpsPilot."""
    services = TelemetryRepository.get_services(db)
    if not services:
        # Fallback to in-memory graph nodes if not yet synced to DB
        return dependency_graph.get_nodes()
    return services
