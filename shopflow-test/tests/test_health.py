def test_health_endpoints(client):
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

    res_ready = client.get("/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "ready"

    res_live = client.get("/live")
    assert res_live.status_code == 200
    assert res_live.json()["status"] == "alive"

def test_health_summary(client):
    res = client.get("/api/health-summary")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "healthy_services" in data
    assert "total_services" in data
    assert data["status"] == "Operational"

def test_status_endpoint(client):
    res = client.get("/status")
    assert res.status_code == 200
    data = res.json()
    assert "services" in data
    assert "postgresql" in data["services"]
    assert "redis" in data["services"]
    assert "api-gateway" in data["services"]
