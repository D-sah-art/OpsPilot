import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.session import init_db
from app.api.routes import (
    health_router,
    services_router,
    topology_router,
    alerts_router,
    metrics_router,
    logs_router,
    events_router,
    sync_router,
    correlation_router,
    incidents_router,
    memory_router,
    hindsight_api_router,
)



logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "logger": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'
)
logger = logging.getLogger("opspilot.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database tables
    logger.info("Initializing OpsPilot SQLite database...")
    init_db()
    try:
        import yaml, os
        from app.topology.discovery import topology_discovery_engine
        possible_paths = [
            os.path.join(os.getcwd(), "config", "topology.yaml"),
            os.path.join(os.getcwd(), "..", "shopflow-test", "config", "topology.yaml"),
            os.path.join(os.getcwd(), "shopflow-test", "config", "topology.yaml"),
        ]
        for p in possible_paths:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    topo = yaml.safe_load(f)
                    topology_discovery_engine.register_fallback_topology(topo.get("nodes", []), topo.get("edges", []))
                    logger.info(f"Loaded fallback topology baseline from {p}")
                break
    except Exception as e:
        logger.debug(f"Notice during startup topology load: {e}")
    logger.info("OpsPilot backend service ready.")
    yield
    # Shutdown
    logger.info("OpsPilot backend service shutting down.")

app = FastAPI(
    title="OpsPilot — Autonomous AIOps Platform",
    version="1.0.0",
    description="Intelligent dependency-aware incident correlation, root-cause diagnosis, and automated remediation platform.",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(health_router)
app.include_router(services_router)
app.include_router(topology_router)
app.include_router(alerts_router)
app.include_router(metrics_router)
app.include_router(logs_router)
app.include_router(events_router)
app.include_router(sync_router)
app.include_router(correlation_router)
app.include_router(incidents_router)
app.include_router(memory_router)
app.include_router(hindsight_api_router)


@app.get("/")
def root():
    return {
        "app": "OpsPilot",
        "version": "1.0.0",
        "status": "operational",
        "docs_url": "/docs",
        "health_url": "/health"
    }
