from app.topology.graph import DependencyGraph

def test_dependency_graph_traversal():
    graph = DependencyGraph()

    nodes = [
        {"id": "shopflow-frontend", "name": "Frontend", "type": "frontend"},
        {"id": "api-gateway", "name": "API Gateway", "type": "gateway"},
        {"id": "product-api", "name": "Product API", "type": "service"},
        {"id": "order-api", "name": "Order API", "type": "service"},
        {"id": "checkout-api", "name": "Checkout API", "type": "service"},
        {"id": "postgresql", "name": "PostgreSQL DB", "type": "database"},
        {"id": "redis", "name": "Redis Cache", "type": "cache"},
    ]

    edges = [
        {"source": "shopflow-frontend", "target": "api-gateway", "protocol": "HTTPS"},
        {"source": "api-gateway", "target": "product-api", "protocol": "HTTP"},
        {"source": "api-gateway", "target": "checkout-api", "protocol": "HTTP"},
        {"source": "api-gateway", "target": "order-api", "protocol": "HTTP"},
        {"source": "checkout-api", "target": "order-api", "protocol": "HTTP"},
        {"source": "checkout-api", "target": "product-api", "protocol": "HTTP"},
        {"source": "checkout-api", "target": "postgresql", "protocol": "TCP"},
        {"source": "order-api", "target": "postgresql", "protocol": "TCP"},
        {"source": "product-api", "target": "redis", "protocol": "TCP"},
        {"source": "product-api", "target": "postgresql", "protocol": "TCP"},
    ]

    graph.load_from_topology(nodes, edges)

    assert graph.graph.number_of_nodes() == 7
    assert graph.graph.number_of_edges() == 10

    # 1. Upstream services called by checkout-api
    upstream_of_checkout = graph.get_upstream_services("checkout-api")
    assert "order-api" in upstream_of_checkout
    assert "postgresql" in upstream_of_checkout
    assert "product-api" in upstream_of_checkout

    # 2. Downstream callers affected if postgresql fails
    downstream_of_pg = graph.get_downstream_services("postgresql")
    assert "order-api" in downstream_of_pg
    assert "checkout-api" in downstream_of_pg
    assert "api-gateway" in downstream_of_pg
    assert "shopflow-frontend" in downstream_of_pg

    # 3. Dependency distance
    dist_pg_to_checkout = graph.dependency_distance("checkout-api", "postgresql")
    assert dist_pg_to_checkout == 1  # direct edge from checkout-api to postgresql exists

    dist_frontend_to_pg = graph.dependency_distance("shopflow-frontend", "postgresql")
    assert dist_frontend_to_pg == 3  # frontend -> gateway -> order-api/checkout-api -> postgresql

    # 4. Path lookup
    path = graph.get_path("api-gateway", "postgresql")
    assert path is not None
    assert path[0] == "api-gateway"
    assert path[-1] == "postgresql"

    # 5. Dependency relatedness
    assert graph.is_dependency_related("order-api", "postgresql") is True
    assert graph.is_dependency_related("shopflow-frontend", "redis") is True
