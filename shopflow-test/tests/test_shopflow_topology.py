def test_get_topology_structure(client):
    res = client.get("/api/topology")
    assert res.status_code == 200
    topo = res.json()
    assert "nodes" in topo
    assert "edges" in topo
    assert "version" in topo

    node_ids = [n["id"] for n in topo["nodes"]]
    expected_services = [
        "shopflow-frontend",
        "api-gateway",
        "product-api",
        "order-api",
        "checkout-api",
        "auth-service",
        "postgresql",
        "redis"
    ]
    for s in expected_services:
        assert s in node_ids, f"Expected node '{s}' in topology"

    # Verify edge connectivity
    edge_pairs = [(e["source"], e["target"]) for e in topo["edges"]]
    assert ("shopflow-frontend", "api-gateway") in edge_pairs
    assert ("api-gateway", "product-api") in edge_pairs
    assert ("api-gateway", "order-api") in edge_pairs
    assert ("api-gateway", "checkout-api") in edge_pairs
    assert ("checkout-api", "order-api") in edge_pairs
    assert ("checkout-api", "postgresql") in edge_pairs
    assert ("order-api", "postgresql") in edge_pairs
    assert ("product-api", "redis") in edge_pairs
