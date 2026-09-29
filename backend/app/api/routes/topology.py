from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.database.session import get_db
from app.topology.discovery import topology_discovery_engine
from app.topology.graph import dependency_graph

router = APIRouter(prefix="/api", tags=["Topology"])

@router.get("/topology")
def get_topology():
    """Returns the current dynamically discovered (or fallback) NetworkX dependency graph model."""
    return topology_discovery_engine.get_current_topology_dict()

@router.post("/topology/discover")
def trigger_discovery():
    """Triggers an explicit inspection pass for dynamic topology discovery."""
    return topology_discovery_engine.get_current_topology_dict()
