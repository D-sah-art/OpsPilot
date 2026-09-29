import os
import time
import yaml
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

# Services
from services.auth-service.main import app as auth_app
from services.product-api.main import app as product_app
from services.order-api.main import app as order_app
from services.checkout-api.main import app as checkout_app

# Telemetry & Chaos
from telemetry.engine import telemetry_engine
from telemetry.logger import get_logger
from telemetry.models import LogEntry
from chaos.engine import chaos_engine
from chaos.scenarios import ALL_SCENARIOS

logger = get_logger("api-gateway")

app = FastAPI(
    title="ShopFlow API Gateway",
    version="1.0.0",
    description="Edge API Gateway and Telemetry Hub for ShopFlow E-Commerce Platform"
)

# Enable CORS for local dev and frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load topology config
CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
TOPOLOGY_FILE = CONFIG_DIR / "topology.yaml"

def load_topology_data() -> Dict[str, Any]:
    if TOPOLOGY_FILE.exists():
        with open(TOPOLOGY_FILE, "r") as f:
            return yaml.safe_load(f)
    return {"nodes": [], "edges": []}

# Request telemetry middleware
@app.middleware("http")
async def telemetry_middleware(request: Request, call_next):
    start_time = time.time()
    path = request.url.path
    
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000

    # Don't flood logs with high-frequency telemetry polling
    if not path.startswith("/telemetry") and not path.startswith("/assets"):
        status_code = response.status_code
        level = "ERROR" if status_code >= 500 else ("WARN" if status_code >= 400 else "INFO")
        event = "GATEWAY_REQUEST_COMPLETED"
        
        telemetry_engine.record_log(LogEntry(
            service="api-gateway",
            level=level,
            event=event,
            message=f"{request.method} {path} -> {status_code} ({round(duration_ms, 1)}ms)",
            latency_ms=round(duration_ms, 1),
            status_code=status_code,
            metadata={"method": request.method, "path": path}
        ))
        
    return response

# ==========================================
# 1. Health & Readiness Contracts
# ==========================================

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "api-gateway",
        "timestamp": time.time(),
        "environment": "production-simulation"
    }

@app.get("/ready")
def ready():
    return {"status": "ready", "service": "api-gateway"}

@app.get("/live")
def live():
    return {"status": "alive", "service": "api-gateway"}

@app.get("/api/health-summary")
def health_summary():
    return telemetry_engine.get_health_summary()

@app.get("/status")
def status_endpoint():
    return telemetry_engine.get_services()

# ==========================================
# 2. Topology Contract
# ==========================================

@app.get("/api/topology")
def get_topology():
    topo = load_topology_data()
    services_status = telemetry_engine.get_services().get("services", {})
    
    # Enrich nodes with live status from telemetry engine
    enriched_nodes = []
    for node in topo.get("nodes", []):
        node_copy = dict(node)
        s_id = node.get("id")
        if s_id in services_status:
            node_copy["live_status"] = services_status[s_id].get("status", "Operational")
            node_copy["latency_ms"] = services_status[s_id].get("latency_ms", 0.0)
            node_copy["error_rate_pct"] = services_status[s_id].get("error_rate_pct", 0.0)
            node_copy["availability_pct"] = services_status[s_id].get("availability_pct", 100.0)
        else:
            node_copy["live_status"] = "Operational"
            node_copy["availability_pct"] = 100.0
        enriched_nodes.append(node_copy)

    return {
        "version": topo.get("version", "1.0"),
        "updated_at": topo.get("updated_at"),
        "nodes": enriched_nodes,
        "edges": topo.get("edges", [])
    }

# ==========================================
# 3. Mount Subservice Routers under /api
# ==========================================

# Product API routes
@app.get("/api/categories")
def api_get_categories():
    from services.product-api.main import get_categories
    return get_categories()

@app.get("/api/products")
def api_list_products(category: Optional[str] = None, q: Optional[str] = None):
    from services.product-api.main import list_products
    return list_products(category=category, q=q)

@app.get("/api/products/{product_id}")
def api_get_product(product_id: str):
    from services.product-api.main import get_product
    return get_product(product_id=product_id)

# Auth Service routes
from services.auth-service.main import LoginRequest
@app.post("/api/auth/login")
def api_login(request: LoginRequest):
    from services.auth-service.main import login
    return login(request=request)

@app.get("/api/auth/users")
def api_get_users():
    from services.auth-service.main import get_demo_users
    return get_demo_users()

@app.get("/api/auth/verify")
def api_verify_token(authorization: Optional[str] = Header(None)):
    from services.auth-service.main import verify_token
    return verify_token(authorization=authorization)

# Cart & Checkout routes
from services.checkout-api.main import CartRequest, CheckoutRequest
@app.post("/api/cart")
def api_update_cart(request: CartRequest):
    from services.checkout-api.main import update_cart
    return update_cart(request=request)

@app.get("/api/cart/{session_id}")
def api_get_cart(session_id: str):
    from services.checkout-api.main import get_cart
    return get_cart(session_id=session_id)

@app.post("/api/checkout")
def api_checkout(request: CheckoutRequest):
    from services.checkout-api.main import process_checkout
    return process_checkout(request=request)

# Order routes
from services.order-api.main import CreateOrderRequest
@app.get("/api/orders")
def api_list_orders(user_id: Optional[str] = None):
    from services.order-api.main import list_orders
    return list_orders(user_id=user_id)

@app.get("/api/orders/{order_id}")
def api_get_order(order_id: str):
    from services.order-api.main import get_order
    return get_order(order_id=order_id)

@app.post("/api/orders")
def api_create_order(request: CreateOrderRequest):
    from services.order-api.main import create_order
    return create_order(request=request)

# ==========================================
# 4. Telemetry Endpoints
# ==========================================

@app.get("/telemetry/metrics")
def get_telemetry_metrics():
    return telemetry_engine.get_metrics()

@app.get("/telemetry/logs")
def get_telemetry_logs(
    limit: int = Query(100, ge=1, le=1000),
    service: Optional[str] = None,
    level: Optional[str] = None,
    search: Optional[str] = None
):
    return telemetry_engine.get_logs(limit=limit, service=service, level=level, search=search)

@app.get("/telemetry/alerts")
def get_telemetry_alerts(
    limit: int = Query(100, ge=1, le=1000),
    severity: Optional[str] = None,
    service: Optional[str] = None,
    alert_type: Optional[str] = None
):
    return telemetry_engine.get_alerts(limit=limit, severity=severity, service=service, alert_type=alert_type)

@app.get("/telemetry/events")
def get_telemetry_events(
    limit: int = Query(100, ge=1, le=1000),
    event_type: Optional[str] = None,
    service: Optional[str] = None
):
    return telemetry_engine.get_events(limit=limit, event_type=event_type, service=service)

@app.get("/telemetry/services")
def get_telemetry_services():
    return telemetry_engine.get_services()

# ==========================================
# 5. Chaos Lab Endpoints
# ==========================================

@app.get("/api/chaos/scenarios")
def list_chaos_scenarios():
    return chaos_engine.list_scenarios()

@app.get("/api/chaos/status")
def get_chaos_status():
    return chaos_engine.get_status()

@app.post("/api/chaos/scenario/{scenario_id}")
def trigger_chaos_scenario(scenario_id: str):
    try:
        res = chaos_engine.trigger_scenario(scenario_id)
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/chaos/reset")
def reset_chaos():
    return chaos_engine.reset()

# ==========================================
# 6. Static Frontend Mount (if built)
# ==========================================
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = FRONTEND_DIST / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIST / "index.html"))
