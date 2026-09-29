from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.database.session import get_db
from app.ingestion.service import ingestion_service

router = APIRouter(prefix="/api", tags=["Synchronization"])

@router.post("/sync/shopflow")
def sync_shopflow(db: Session = Depends(get_db)):
    """
    Triggers an on-demand synchronization pass with the external ShopFlow environment.
    Ingests topology, services, alerts, logs, metrics, and events into SQLite and updates the dependency graph.
    """
    return ingestion_service.sync_shopflow(db=db)
