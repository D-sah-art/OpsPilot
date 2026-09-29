import time
import json
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from services.common.db import db
from services.common.redis_client import redis_client
from telemetry.logger import get_logger
from chaos.engine import chaos_engine

logger = get_logger("product-api")

app = FastAPI(title="ShopFlow Product API", version="1.0.0")

class ProductModel(BaseModel):
    id: str
    title: str
    description: str
    category: str
    price: float
    rating: float
    review_count: int
    stock: int
    image_url: str
    badge: Optional[str] = None
    specs: Dict[str, Any] = {}

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "product-api",
        "dependencies": {
            "redis": "healthy",
            "postgresql": "healthy"
        }
    }

@app.get("/categories", response_model=List[str])
def get_categories():
    categories = sorted(list(set(p["category"] for p in db.products.values())))
    return categories

@app.get("/products", response_model=List[ProductModel])
def list_products(category: Optional[str] = None, q: Optional[str] = None):
    start = time.time()
    cache_key = f"products:cat_{category or 'all'}:q_{q or 'none'}"

    chaos_status = chaos_engine.get_status()
    is_redis_down = (
        chaos_status.get("active_scenario") == "redis_failure" and
        chaos_status.get("state") == "RUNNING"
    )

    # Check cache if redis is not simulated down
    cached_data = None
    if not is_redis_down:
        cached_data = redis_client.get(cache_key)

    if cached_data:
        try:
            products = json.loads(cached_data)
            latency = (time.time() - start) * 1000
            logger.debug("CACHE_HIT", f"Served {len(products)} products from Redis cache", dependency="redis", latency_ms=latency)
            return products
        except Exception:
            pass

    # Cache miss or redis down -> Query Database
    logger.info("CACHE_MISS", f"Cache miss for {cache_key}, querying PostgreSQL", dependency="postgresql")
    
    # Check if database cascade is active to inject realistic latency
    if chaos_status.get("active_scenario") == "database_cascade" and chaos_status.get("state") == "RUNNING":
        time.sleep(0.05)  # Slight spillover latency

    products = db.get_products(category=category, query=q)
    
    # Store in Redis if Redis is active
    if not is_redis_down:
        try:
            redis_client.set(cache_key, json.dumps(products), ex=120)
        except Exception:
            pass

    latency = (time.time() - start) * 1000
    logger.info("REQUEST_COMPLETED", f"Fetched {len(products)} products from DB", latency_ms=latency, status_code=200)
    return products

@app.get("/products/{product_id}", response_model=ProductModel)
def get_product(product_id: str):
    start = time.time()
    product = db.get_product(product_id)
    latency = (time.time() - start) * 1000
    if not product:
        logger.warn("PRODUCT_NOT_FOUND", f"Product ID {product_id} not found", latency_ms=latency, status_code=404)
        raise HTTPException(status_code=404, detail="Product not found")
    
    logger.info("REQUEST_COMPLETED", f"Retrieved product {product_id}", latency_ms=latency, status_code=200)
    return product
