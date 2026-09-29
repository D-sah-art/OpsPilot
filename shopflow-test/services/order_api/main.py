import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from services.common.db import db
from telemetry.logger import get_logger
from chaos.engine import chaos_engine

logger = get_logger("order-api")

app = FastAPI(title="ShopFlow Order API", version="1.0.0")

class OrderItemModel(BaseModel):
    product_id: str
    product_title: Optional[str] = "Product"
    price: float
    quantity: int = 1

class CreateOrderRequest(BaseModel):
    user_id: str
    user_email: str
    subtotal: float
    tax: float
    shipping: float
    total: float
    shipping_address: Dict[str, Any]
    payment_method: Optional[str] = "Credit Card (Simulated)"
    items: List[OrderItemModel]

class OrderResponse(BaseModel):
    id: str
    user_id: str
    user_email: str
    status: str
    subtotal: float
    tax: float
    shipping: float
    total: float
    shipping_address: Dict[str, Any]
    payment_method: str
    created_at: str
    items: List[Dict[str, Any]]

@app.get("/health")
def health():
    chaos_status = chaos_engine.get_status()
    if (
        chaos_status.get("active_scenario") == "database_cascade" and
        chaos_status.get("current_stage", 0) >= 3 and
        chaos_status.get("state") in ["RUNNING", "COMPLETED"]
    ):
        return {
            "status": "degraded",
            "service": "order-api",
            "dependencies": {"postgresql": "failing"}
        }
    return {
        "status": "healthy",
        "service": "order-api",
        "dependencies": {"postgresql": "healthy"}
    }

@app.get("/orders", response_model=List[OrderResponse])
def list_orders(user_id: Optional[str] = None):
    start = time.time()
    chaos_status = chaos_engine.get_status()

    # If database cascade is in Stage 3+, simulate DB query failure
    if (
        chaos_status.get("active_scenario") == "database_cascade" and
        chaos_status.get("current_stage", 0) >= 3 and
        chaos_status.get("state") in ["RUNNING", "COMPLETED"]
    ):
        time.sleep(0.3)
        latency = (time.time() - start) * 1000
        logger.error("DATABASE_TIMEOUT", "PostgreSQL query timeout on orders table", dependency="postgresql", latency_ms=latency, status_code=500)
        raise HTTPException(status_code=500, detail="Database connection pool timeout while querying orders")

    orders = db.get_orders(user_id=user_id)
    latency = (time.time() - start) * 1000
    logger.info("REQUEST_COMPLETED", f"Retrieved {len(orders)} orders", latency_ms=latency, status_code=200)
    return orders

@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: str):
    start = time.time()
    order = db.get_order(order_id)
    latency = (time.time() - start) * 1000
    if not order:
        logger.warn("ORDER_NOT_FOUND", f"Order {order_id} not found", latency_ms=latency, status_code=404)
        raise HTTPException(status_code=404, detail="Order not found")
    
    logger.info("REQUEST_COMPLETED", f"Fetched order {order_id}", latency_ms=latency, status_code=200)
    return order

@app.post("/orders", response_model=OrderResponse)
def create_order(request: CreateOrderRequest):
    start = time.time()
    logger.info("ORDER_CREATION_START", f"Creating order for user {request.user_email}", metadata={"user_id": request.user_id})

    chaos_status = chaos_engine.get_status()
    # If database cascade is active, simulate DB insertion failure
    if (
        chaos_status.get("active_scenario") == "database_cascade" and
        chaos_status.get("current_stage", 0) >= 2 and
        chaos_status.get("state") in ["RUNNING", "COMPLETED"]
    ):
        time.sleep(0.4)
        latency = (time.time() - start) * 1000
        logger.error(
            "DATABASE_TIMEOUT",
            "Failed to acquire PostgreSQL connection lease for INSERT transaction. Connection pool exhausted.",
            dependency="postgresql",
            latency_ms=latency,
            status_code=503
        )
        raise HTTPException(status_code=503, detail="Database connection pool exhausted. Unable to write order transaction.")

    order = db.create_order(request.model_dump())
    latency = (time.time() - start) * 1000
    logger.info("ORDER_CREATED", f"Order {order['id']} created successfully total=${order['total']}", latency_ms=latency, status_code=201)
    return order
