def test_cart_management(client):
    cart_data = {
        "session_id": "sess_test_123",
        "items": [
            {
                "product_id": "prod_01",
                "product_title": "ProFlow Headphones",
                "price": 299.99,
                "quantity": 2
            }
        ]
    }
    update_res = client.post("/api/cart", json=cart_data)
    assert update_res.status_code == 200
    assert update_res.json()["items_count"] == 1

    get_res = client.get("/api/cart/sess_test_123")
    assert get_res.status_code == 200
    assert len(get_res.json()["items"]) == 1

def test_full_checkout_flow(client):
    checkout_payload = {
        "user_id": "usr_alex_01",
        "user_email": "alex@shopflow.dev",
        "items": [
            {
                "product_id": "prod_02",
                "product_title": "AeroMechanical RGB Keyboard",
                "price": 149.50,
                "quantity": 1
            },
            {
                "product_id": "prod_03",
                "product_title": "UltraPrecision Ergonomic Mouse",
                "price": 89.00,
                "quantity": 1
            }
        ],
        "shipping_address": {
            "street": "100 Tech Boulevard",
            "city": "San Francisco",
            "state": "CA",
            "zip": "94105",
            "country": "USA"
        },
        "payment_method": "Credit Card (Simulated)",
        "coupon_code": "HACKATHON20"
    }

    res = client.post("/api/checkout", json=checkout_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "order_id" in data
    order_id = data["order_id"]

    # Verify order is queryable
    order_res = client.get(f"/api/orders/{order_id}")
    assert order_res.status_code == 200
    order_data = order_res.json()
    assert order_data["id"] == order_id
    assert order_data["user_email"] == "alex@shopflow.dev"
    assert len(order_data["items"]) == 2

def test_checkout_empty_cart(client):
    checkout_payload = {
        "user_id": "usr_alex_01",
        "user_email": "alex@shopflow.dev",
        "items": [],
        "shipping_address": {}
    }
    res = client.post("/api/checkout", json=checkout_payload)
    assert res.status_code == 400
