import os
import json
import uuid
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import asyncpg
from telemetry.logger import get_logger
from chaos.engine import chaos_engine

logger = get_logger("db-pool")

INITIAL_PRODUCTS = [
    {
        "id": "prod_01",
        "title": "ProFlow Noise-Canceling Headphones",
        "description": "Premium wireless acoustic headphones with adaptive ANC, 40-hour battery life, and spatial audio.",
        "category": "Electronics",
        "price": 299.99,
        "rating": 4.9,
        "review_count": 342,
        "stock": 45,
        "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&auto=format&fit=crop&q=80",
        "badge": "Best Seller",
        "specs": {"Battery": "40 hrs", "Connectivity": "Bluetooth 5.3", "Weight": "250g", "ANC": "Adaptive"}
    },
    {
        "id": "prod_02",
        "title": "AeroMechanical RGB Keyboard",
        "description": "Hot-swappable tactile mechanical keyboard with PBT keycaps, per-key RGB, and wireless dual-mode.",
        "category": "Electronics",
        "price": 149.50,
        "rating": 4.8,
        "review_count": 189,
        "stock": 28,
        "image_url": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600&auto=format&fit=crop&q=80",
        "badge": "Popular",
        "specs": {"Switches": "Tactile Brown", "Layout": "75%", "RGB": "16.8M colors", "Connection": "2.4GHz / USB-C"}
    },
    {
        "id": "prod_03",
        "title": "UltraPrecision Ergonomic Mouse",
        "description": "High-accuracy wireless mouse with magnetic scroll wheel, ergonomic palm support, and fast charging.",
        "category": "Electronics",
        "price": 89.00,
        "rating": 4.7,
        "review_count": 512,
        "stock": 60,
        "image_url": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=600&auto=format&fit=crop&q=80",
        "badge": "Staff Pick",
        "specs": {"DPI": "16000 DPI", "Battery": "70 days", "Buttons": "7 programmable"}
    },
    {
        "id": "prod_04",
        "title": "Studio UltraWide 4K Monitor 34\"",
        "description": "Curved IPS 144Hz HDR600 display with 99% DCI-P3 color accuracy and 90W USB-C power delivery.",
        "category": "Electronics",
        "price": 649.99,
        "rating": 4.9,
        "review_count": 98,
        "stock": 15,
        "image_url": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=600&auto=format&fit=crop&q=80",
        "badge": "Featured",
        "specs": {"Resolution": "3440 x 1440", "Refresh Rate": "144Hz", "Panel": "Fast IPS", "Ports": "USB-C, HDMI 2.1, DP 1.4"}
    },
    {
        "id": "prod_05",
        "title": "Merino Wool Minimalist Hoodie",
        "description": "Engineered thermal regulation merino wool blend pullover designed for comfort and durability.",
        "category": "Apparel",
        "price": 115.00,
        "rating": 4.6,
        "review_count": 215,
        "stock": 80,
        "image_url": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=600&auto=format&fit=crop&q=80",
        "badge": "Eco-Friendly",
        "specs": {"Material": "80% Merino Wool, 20% Recycled Poly", "Fit": "Athletic", "Care": "Machine wash cold"}
    },
    {
        "id": "prod_06",
        "title": "All-Weather Tech Waterproof Parka",
        "description": "3-layer breathable waterproof membrane jacket with stormproof seams and thermal interior lining.",
        "category": "Apparel",
        "price": 240.00,
        "rating": 4.8,
        "review_count": 164,
        "stock": 32,
        "image_url": "https://images.unsplash.com/photo-1548883354-7622d03aca27?w=600&auto=format&fit=crop&q=80",
        "badge": "New Arrival",
        "specs": {"Waterproof Rating": "20,000mm", "Breathability": "15,000g", "Pockets": "6 sealed"}
    },
    {
        "id": "prod_07",
        "title": "Artisan Pour-Over Coffee Station",
        "description": "Borosilicate glass dripper with solid walnut stand, precision gooseneck kettle, and digital scale.",
        "category": "Home & Living",
        "price": 125.00,
        "rating": 4.9,
        "review_count": 420,
        "stock": 50,
        "image_url": "https://images.unsplash.com/photo-1517668808822-9ebb02f2a0e6?w=600&auto=format&fit=crop&q=80",
        "badge": "Bestseller",
        "specs": {"Capacity": "800ml", "Material": "Walnut & Glass", "Kettle": "1.0L Temperature Control"}
    },
    {
        "id": "prod_08",
        "title": "Ergonomic Mesh Lumbar Desk Chair",
        "description": "Dynamic lumbar support, 4D adjustable armrests, breathable mesh back, and aluminum wheelbase.",
        "category": "Home & Living",
        "price": 380.00,
        "rating": 4.7,
        "review_count": 310,
        "stock": 22,
        "image_url": "https://images.unsplash.com/photo-1580481077194-e4359cf9c6dc?w=600&auto=format&fit=crop&q=80",
        "badge": "Top Rated",
        "specs": {"Weight Capacity": "300 lbs", "Adjustability": "4D Armrests, Lumbar, Height", "Warranty": "5 Years"}
    },
    {
        "id": "prod_09",
        "title": "Full-Grain Leather Everyday Briefcase",
        "description": "Handcrafted vegetable-tanned leather briefcase with padded laptop sleeve and brass hardware.",
        "category": "Accessories",
        "price": 195.00,
        "rating": 4.9,
        "review_count": 140,
        "stock": 25,
        "image_url": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&auto=format&fit=crop&q=80",
        "badge": "Handmade",
        "specs": {"Fits Laptop": "Up to 16-inch", "Leather": "Full-grain Italian", "Hardware": "Solid Brass"}
    },
    {
        "id": "prod_10",
        "title": "Titanium Modular Everyday Pen",
        "description": "Precision CNC-machined Grade 5 titanium body with Schmidt EasyFlow 9000 refill cartridge.",
        "category": "Accessories",
        "price": 65.00,
        "rating": 4.8,
        "review_count": 275,
        "stock": 110,
        "image_url": "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?w=600&auto=format&fit=crop&q=80",
        "badge": "Trending",
        "specs": {"Material": "Grade 5 Titanium", "Refill": "Schmidt 9000", "Length": "135mm"}
    },
    {
        "id": "prod_11",
        "title": "Smart Ambient Light Bar 2-Pack",
        "description": "Syncs with monitor audio and screen colors, 16 million colors, voice control, and preset scenes.",
        "category": "Electronics",
        "price": 79.99,
        "rating": 4.5,
        "review_count": 380,
        "stock": 70,
        "image_url": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=600&auto=format&fit=crop&q=80",
        "badge": "Smart Tech",
        "specs": {"Connectivity": "WiFi 2.4GHz + BT", "Lumens": "500lm each", "Voice Support": "Alexa & Google"}
    },
    {
        "id": "prod_12",
        "title": "Matte Ceramic Desk Organizer Tray",
        "description": "Minimalist dual-compartment heavy stoneware tray for organizing cables, watches, and stationery.",
        "category": "Home & Living",
        "price": 35.00,
        "rating": 4.6,
        "review_count": 95,
        "stock": 120,
        "image_url": "https://images.unsplash.com/photo-1544816155-12df9643f363?w=600&auto=format&fit=crop&q=80",
        "badge": "Essential",
        "specs": {"Finish": "Matte Glazed", "Dimensions": "22 x 12 x 2.5 cm", "Weight": "450g"}
    }
]

INITIAL_USERS = [
    {
        "id": "usr_alex_01",
        "email": "alex@shopflow.dev",
        "password_hash": "$2b$12$e9Qq0.v3pQW8lG5pA/3X5eQoGj.n.sD5Xh4Kk6Yn.oJ8l.xM.3C2e",
        "full_name": "Alex Rivera",
        "role": "customer"
    },
    {
        "id": "usr_sarah_02",
        "email": "sarah@shopflow.dev",
        "password_hash": "$2b$12$e9Qq0.v3pQW8lG5pA/3X5eQoGj.n.sD5Xh4Kk6Yn.oJ8l.xM.3C2e",
        "full_name": "Sarah Chen",
        "role": "customer"
    },
    {
        "id": "usr_admin_03",
        "email": "ops@shopflow.dev",
        "password_hash": "$2b$12$e9Qq0.v3pQW8lG5pA/3X5eQoGj.n.sD5Xh4Kk6Yn.oJ8l.xM.3C2e",
        "full_name": "DevOps Lead",
        "role": "admin"
    }
]

INITIAL_ORDERS = [
    {
        "id": "ord_1001",
        "user_id": "usr_alex_01",
        "user_email": "alex@shopflow.dev",
        "status": "DELIVERED",
        "subtotal": 299.99,
        "tax": 24.00,
        "shipping": 0.00,
        "total": 323.99,
        "shipping_address": {"street": "742 Evergreen Terrace", "city": "Springfield", "state": "OR", "zip": "97477", "country": "USA"},
        "payment_method": "Credit Card (**** 4242)",
        "created_at": "2026-09-02T14:20:00Z",
        "items": [
            {
                "id": "itm_01",
                "product_id": "prod_01",
                "product_title": "ProFlow Noise-Canceling Headphones",
                "price": 299.99,
                "quantity": 1
            }
        ]
    },
    {
        "id": "ord_1002",
        "user_id": "usr_alex_01",
        "user_email": "alex@shopflow.dev",
        "status": "SHIPPED",
        "subtotal": 149.50,
        "tax": 11.96,
        "shipping": 0.00,
        "total": 161.46,
        "shipping_address": {"street": "742 Evergreen Terrace", "city": "Springfield", "state": "OR", "zip": "97477", "country": "USA"},
        "payment_method": "Credit Card (**** 4242)",
        "created_at": "2026-09-04T10:15:00Z",
        "items": [
            {
                "id": "itm_02",
                "product_id": "prod_02",
                "product_title": "AeroMechanical RGB Keyboard",
                "price": 149.50,
                "quantity": 1
            }
        ]
    }
]

class DatabaseManager:
    def __init__(self):
        self.products: Dict[str, Dict[str, Any]] = {p["id"]: dict(p) for p in INITIAL_PRODUCTS}
        self.users: Dict[str, Dict[str, Any]] = {u["email"]: dict(u) for u in INITIAL_USERS}
        self.orders: Dict[str, Dict[str, Any]] = {o["id"]: dict(o) for o in INITIAL_ORDERS}
        self.cart_sessions: Dict[str, List[Dict[str, Any]]] = {}

    def get_products(self, category: Optional[str] = None, query: Optional[str] = None) -> List[Dict[str, Any]]:
        results = list(self.products.values())
        if category and category.lower() != "all":
            results = [p for p in results if p["category"].lower() == category.lower()]
        if query:
            q = query.lower()
            results = [
                p for p in results
                if q in p["title"].lower() or q in p["description"].lower() or q in p["category"].lower()
            ]
        return results

    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        return self.products.get(product_id)

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return self.users.get(email.lower())

    def get_orders(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        orders_list = list(self.orders.values())
        if user_id:
            orders_list = [o for o in orders_list if o["user_id"] == user_id]
        return sorted(orders_list, key=lambda x: x["created_at"], reverse=True)

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        return self.orders.get(order_id)

    def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        order_id = f"ord_{uuid.uuid4().hex[:6]}"
        now = datetime.now(timezone.utc).isoformat()
        
        items = []
        for itm in order_data.get("items", []):
            item_id = f"itm_{uuid.uuid4().hex[:6]}"
            items.append({
                "id": item_id,
                "product_id": itm["product_id"],
                "product_title": itm.get("product_title", "Product"),
                "price": float(itm["price"]),
                "quantity": int(itm["quantity"])
            })
            # Deduct stock if available
            p_id = itm["product_id"]
            if p_id in self.products:
                self.products[p_id]["stock"] = max(0, self.products[p_id]["stock"] - int(itm["quantity"]))

        new_order = {
            "id": order_id,
            "user_id": order_data.get("user_id", "usr_alex_01"),
            "user_email": order_data.get("user_email", "alex@shopflow.dev"),
            "status": "CONFIRMED",
            "subtotal": float(order_data.get("subtotal", 0.0)),
            "tax": float(order_data.get("tax", 0.0)),
            "shipping": float(order_data.get("shipping", 0.0)),
            "total": float(order_data.get("total", 0.0)),
            "shipping_address": order_data.get("shipping_address", {}),
            "payment_method": order_data.get("payment_method", "Credit Card (Simulated)"),
            "created_at": now,
            "items": items
        }
        self.orders[order_id] = new_order
        return new_order

    def get_cart(self, session_id: str) -> List[Dict[str, Any]]:
        return self.cart_sessions.get(session_id, [])

    def save_cart(self, session_id: str, items: List[Dict[str, Any]]):
        self.cart_sessions[session_id] = items

db = DatabaseManager()
