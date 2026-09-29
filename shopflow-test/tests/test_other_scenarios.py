import time
from chaos.engine import chaos_engine
from telemetry.engine import telemetry_engine

def test_redis_failure_scenario(client):
    res = client.post("/api/chaos/scenario/redis_failure")
    assert res.status_code == 200
    time.sleep(1.0)
    
    # Check alerts and metrics
    alerts_res = client.get("/telemetry/alerts")
    assert alerts_res.status_code == 200
    
    # Reset
    reset_res = client.post("/api/chaos/reset")
    assert reset_res.status_code == 200

def test_high_memory_scenario(client):
    res = client.post("/api/chaos/scenario/high_memory")
    assert res.status_code == 200
    
    metrics_res = client.get("/telemetry/metrics")
    assert metrics_res.status_code == 200
    
    client.post("/api/chaos/reset")

def test_traffic_spike_scenario(client):
    res = client.post("/api/chaos/scenario/traffic_spike")
    assert res.status_code == 200
    
    status_res = client.get("/api/chaos/status")
    assert status_res.status_code == 200
    assert status_res.json()["active_scenario"] == "traffic_spike"
    
    client.post("/api/chaos/reset")

def test_checkout_failure_scenario(client):
    res = client.post("/api/chaos/scenario/checkout_failure")
    assert res.status_code == 200
    
    # Attempt checkout -> should fail with payment rejection
    checkout_payload = {
        "user_id": "usr_alex_01",
        "user_email": "alex@shopflow.dev",
        "items": [{"product_id": "prod_01", "price": 299.99, "quantity": 1}],
        "shipping_address": {"street": "742 Evergreen Terrace"}
    }
    c_res = client.post("/api/checkout", json=checkout_payload)
    assert c_res.status_code == 500
    
    client.post("/api/chaos/reset")
