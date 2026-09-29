import time
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

from services.common.db import db
from telemetry.logger import get_logger
from chaos.engine import chaos_engine

logger = get_logger("checkout-api")

app = FastAPI(title="ShopFlow Checkout API", version="1.0.0")

class CartItem(BaseModel):
    product_id: str
    product_title: Optional[str] = None
    price: float
    quantity: int = 1
    image_url: Optional[str] = None

class CartRequest(BaseModel):
    session_id: str
    items: List[CartItem]

class CheckoutRequest(BaseModel):
    user_id: Optional[str] = "usr_alex_01"
    user_email: Optional[str] = "alex@shopflow.dev"
    items: List[CartItem]
    shipping_address: Dict[str, Any]
    payment_method: Optional[str] = "Credit Card (Simulated)"
    coupon_code: Optional[str] = None

class CheckoutResponse(BaseModel):
    success: bool
    order_id: Optional[str] = None
    message: str
    order: Optional[Dict[str, Any]] = None

@app.get("/health")
def health():
    chaos_status = chaos_engine.get_status()
    if (
        chaos_status.get("active_scenario") in ["database_cascade", "checkout_failure"] and
        chaos_status.get("current_stage", 0) >= 4 and
        chaos_status.get("state") in ["RUNNING", "COMPLETED"]
    ):
        return {
            "status": "degraded",
            "service": "checkout-api",
            "dependencies": {
                "order-api": "degraded",
                "product-api": "healthy",
                "postgresql": "failing"
            }
        }
    return {
        "status": "healthy",
        "service": "checkout-api",
        "dependencies": {
            "order-api": "healthy",
            "product-api": "healthy",
            "postgresql": "healthy"
        }
    }

@app.post("/cart")
def update_cart(request: CartRequest):
    db.save_cart(request.session_id, [item.model_dump() for item in request.items])
    return {"status": "ok", "items_count": len(request.items)}

@app.get("/cart/{session_id}")
def get_cart(session_id: str):
    items = db.get_cart(session_id)
    return {"session_id": session_id, "items": items}

@app.post("/checkout", response_model=CheckoutResponse)
def process_checkout(request: CheckoutRequest):
    start = time.time()
    logger.info("CHECKOUT_INITIATED", f"Initiating checkout for {request.user_email}", metadata={"items_count": len(request.items)})

    if not request.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    chaos_status = chaos_engine.get_status()

    # 1. Simulate High Memory latency
    if chaos_status.get("active_scenario") == "high_memory" and chaos_status.get("state") == "RUNNING":
        time.sleep(0.35)

    # 2. Simulate Isolated Checkout Failure
    if chaos_status.get("active_scenario") == "checkout_failure" and chaos_status.get("state") in ["RUNNING", "COMPLETED"]:
        latency = (time.time() - start) * 1000
        logger.error("PAYMENT_GATEWAY_ERROR", "Payment simulator rejected transaction: simulated upstream gateway error", status_code=500, latency_ms=latency)
        raise HTTPException(status_code=500, detail="Payment authorization rejected by gateway.")

    # 3. Simulate Database Cascade Downstream Failure (Stage 4+)
    if (
        chaos_status.get("active_scenario") == "database_cascade" and
        chaos_status.get("current_stage", 0) >= 3 and
        chaos_status.get("state") in ["RUNNING", "COMPLETED"]
    ):
        time.sleep(0.4)
        latency = (time.time() - start) * 1000
        logger.error(
            "DEPENDENCY_TIMEOUT",
            "Checkout API call to downstream order-api timed out after 3000ms",
            dependency="order-api",
            latency_ms=latency,
            status_code=503
        )
        logger.error(
            "CHECKOUT_FAILED",
            "Checkout workflow aborting due to order persistence failure in order-api",
            dependency="order-api",
            status_code=503
        )
        raise HTTPException(
            status_code=503,
            detail="Checkout temporarily unavailable. Your cart is safe. Please try again in a moment."
        )

    # Calculate Totals
    subtotal = sum(item.price * item.quantity for item in request.items)
    if request.coupon_code and request.coupon_code.upper() == "HACKATHON20":
        subtotal = round(subtotal * 0.8, 2)
    tax = round(subtotal * 0.08, 2)
    shipping = 0.00 if subtotal > 50.0 else 9.99
    total = round(subtotal + tax + shipping, 2)

    # Verify inventory from DB
    for item in request.items:
        prod = db.get_product(item.product_id)
        if prod and prod["stock"] < item.quantity:
            logger.warn("INSUFFICIENT_STOCK", f"Insufficient stock for {prod['title']}", latency_ms=(time.time() - start) * 1000)
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {prod['title']}")

    # Call Order API / DB to create the order
    order_payload = {
        "user_id": request.user_id or "usr_alex_01",
        "user_email": request.user_email or "alex@shopflow.dev",
        "subtotal": subtotal,
        "tax": tax,
        "shipping": shipping,
        "total": total,
        "shipping_address": request.shipping_address,
        "payment_method": request.payment_method or "Credit Card (Simulated)",
        "items": [
            {
                "product_id": item.product_id,
                "product_title": item.product_title or (db.get_product(item.product_id) or {}).get("title", "Product"),
                "price": item.price,
                "quantity": item.quantity
            }
            for item in request.items
        ]
    }

    created_order = db.create_order(order_payload)
    latency = (time.time() - start) * 1000
    logger.info("CHECKOUT_COMPLETED", f"Checkout succeeded. Order {created_order['id']} placed.", latency_ms=latency, status_code=200)

    return CheckoutResponse(
        success=True,
        order_id=created_order["id"],
        message="Order successfully placed!",
        order=created_order
    )
