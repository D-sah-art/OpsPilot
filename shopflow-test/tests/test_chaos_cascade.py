import time
from datetime import datetime
from chaos.engine import chaos_engine
from telemetry.engine import telemetry_engine

def test_database_cascade_causal_sequence_and_alerts(client):
    # 1. Trigger database_cascade
    trigger_res = client.post("/api/chaos/scenario/database_cascade")
    assert trigger_res.status_code == 200
    status_data = trigger_res.json()
    assert status_data["active_scenario"] == "database_cascade"
    assert status_data["state"] == "RUNNING"

    # Wait for the fast simulation runner to finish emitting all 6 stages
    max_wait = 15.0
    start_t = time.time()
    while time.time() - start_t < max_wait:
        st = client.get("/api/chaos/status").json()
        if st.get("state") == "COMPLETED" or st.get("alert_count", 0) >= 28:
            break
        time.sleep(0.5)

    # 2. Fetch all emitted alerts
    alerts_res = client.get("/telemetry/alerts?limit=100")
    assert alerts_res.status_code == 200
    alerts = alerts_res.json()

    # Verify ~28–30 useful alerts produced
    alert_count = len(alerts)
    assert 28 <= alert_count <= 32, f"Expected between 28 and 32 alerts, got {alert_count}"

    # Verify alerts are chronologically ordered (oldest to newest in causal order)
    # The API returns them newest first (reversed), so let's reverse to check causal sequence
    causal_alerts = list(reversed(alerts))
    timestamps = [datetime.fromisoformat(a["timestamp"]) for a in causal_alerts]
    for i in range(len(timestamps) - 1):
        assert timestamps[i] <= timestamps[i+1], f"Alert timestamp out of causal order at index {i}"

    # 3. Verify PostgreSQL degrades first (initial 4+ alerts are from postgresql)
    first_four_services = [a["service"] for a in causal_alerts[:4]]
    assert all(s == "postgresql" for s in first_four_services), f"Expected first 4 alerts to be postgresql, got {first_four_services}"

    # 4. Verify DB latency & slow query alerts appear first
    early_alert_types = [a["alert_type"] for a in causal_alerts[:4]]
    assert "DB_QUERY_SLOW" in early_alert_types
    assert "DB_LOCK_CONTENTION" in early_alert_types

    # 5. Verify Connection Pool Exhaustion follows
    pool_alert = next((a for a in causal_alerts if a["alert_type"] == "DB_CONNECTION_EXHAUSTION"), None)
    assert pool_alert is not None
    assert pool_alert["service"] == "postgresql"

    # 6. Verify Order API degrades next
    order_api_alert = next((a for a in causal_alerts if a["service"] == "order-api"), None)
    assert order_api_alert is not None
    assert order_api_alert["dependency"] == "postgresql"

    # 7. Verify Checkout API degrades next
    checkout_api_alert = next((a for a in causal_alerts if a["service"] == "checkout-api"), None)
    assert checkout_api_alert is not None
    assert checkout_api_alert["dependency"] == "order-api"

    # 8. Verify Gateway symptoms appear next
    gateway_alert = next((a for a in causal_alerts if a["service"] == "api-gateway"), None)
    assert gateway_alert is not None

    # 9. Verify variety of alert types (not 30 identical copies)
    unique_alert_types = set(a["alert_type"] for a in alerts)
    assert len(unique_alert_types) >= 8, f"Expected at least 8 distinct alert types, got {len(unique_alert_types)}: {unique_alert_types}"

    # 10. Verify Customer Checkout degradation
    checkout_payload = {
        "user_id": "usr_alex_01",
        "user_email": "alex@shopflow.dev",
        "items": [{"product_id": "prod_01", "price": 299.99, "quantity": 1}],
        "shipping_address": {"street": "742 Evergreen Terrace"}
    }
    checkout_res = client.post("/api/checkout", json=checkout_payload)
    assert checkout_res.status_code in [500, 503, 504]
    err_detail = checkout_res.json().get("detail", "")
    assert "temporarily unavailable" in err_detail or "exhausted" in err_detail or "timeout" in err_detail

    # 11. Verify Product Browsing remains available during checkout degradation
    products_res = client.get("/api/products")
    assert products_res.status_code == 200

    # 12. Verify Reset restores healthy state
    reset_res = client.post("/api/chaos/reset")
    assert reset_res.status_code == 200
    reset_data = reset_res.json()
    assert reset_data["state"] == "IDLE"
    assert reset_data["alert_count"] == 0

    # Verify health summary returns to Operational
    health_summary_res = client.get("/api/health-summary")
    assert health_summary_res.status_code == 200
    assert health_summary_res.json()["status"] == "Operational"

    # Verify checkout works again after reset
    checkout_recovered_res = client.post("/api/checkout", json=checkout_payload)
    assert checkout_recovered_res.status_code == 200
    assert checkout_recovered_res.json()["success"] is True
