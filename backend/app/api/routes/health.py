from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database.session import get_db
from app.ingestion.adapter import shopflow_adapter
from app.config import settings

router = APIRouter(tags=["Health"])

@router.get("/health")
def health_check():
    """
    Returns OpsPilot's own system health independently of ShopFlow's status.
    Exposes ShopFlow connectivity status separately.
    """
    shopflow_connected = shopflow_adapter.check_connectivity()
    
    return {
        "status": "healthy",
        "service": "opspilot-backend",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "shopflow": "connected" if shopflow_connected else "disconnected",
        "shopflow_target_url": settings.shopflow_base_url
    }

@router.post("/api/reset")
def reset_opspilot_database(db: Session = Depends(get_db)):
    """
    Resets the OpsPilot database to a clean slate (clears alerts, incidents, audits).
    """
    from app.database.repository import TelemetryRepository
    TelemetryRepository.clear_all(db)
    return {"status": "success", "message": "OpsPilot database reset to clean state"}

