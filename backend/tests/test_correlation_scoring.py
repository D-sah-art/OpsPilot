import pytest
from app.models.alert import Alert
from app.topology.graph import DependencyGraph
from app.correlation.scoring import (
    calculate_pairwise_score,
    compute_temporal_score,
    compute_dependency_score,
    compute_graph_distance_score,
    compute_causal_order_score,
    compute_alert_type_score,
    compute_severity_score,
    compute_tag_and_metric_score,
    WEIGHT_DEPENDENCY,
    WEIGHT_GRAPH_DISTANCE,
    WEIGHT_CAUSAL_ORDER,
    WEIGHT_TEMPORAL,
    WEIGHT_SERVICE,
    WEIGHT_ALERT_TYPE,
    WEIGHT_SEVERITY,
    WEIGHT_TAG_AND_METRIC,
)

@pytest.fixture
def test_topology_graph():
    graph = DependencyGraph()
    nodes = [
        {"id": "shopflow-frontend", "name": "Frontend"},
        {"id": "api-gateway", "name": "Gateway"},
        {"id": "checkout-api", "name": "Checkout API"},
        {"id": "order-api", "name": "Order API"},
        {"id": "product-api", "name": "Product API"},
        {"id": "postgresql", "name": "PostgreSQL"},
        {"id": "redis", "name": "Redis"},
        {"id": "unrelated-service", "name": "Isolated Service"}
    ]
    edges = [
        {"source": "shopflow-frontend", "target": "api-gateway"},
        {"source": "api-gateway", "target": "checkout-api"},
        {"source": "api-gateway", "target": "product-api"},
        {"source": "checkout-api", "target": "order-api"},
        {"source": "order-api", "target": "postgresql"},
        {"source": "product-api", "target": "redis"},
    ]
    graph.load_from_topology(nodes, edges)
    return graph

def test_weights_sum_to_one():
    total_weights = (
        WEIGHT_DEPENDENCY
        + WEIGHT_GRAPH_DISTANCE
        + WEIGHT_CAUSAL_ORDER
        + WEIGHT_TEMPORAL
        + WEIGHT_SERVICE
        + WEIGHT_ALERT_TYPE
        + WEIGHT_SEVERITY
        + WEIGHT_TAG_AND_METRIC
    )
    assert abs(total_weights - 1.0) < 1e-6

def test_temporal_scoring():
    # Immediate (<= 15s)
    score, _ = compute_temporal_score(5.0)
    assert score == 1.0

    # Rapid (15s - 60s)
    score, _ = compute_temporal_score(30.0)
    assert 0.7 <= score <= 1.0

    # Gradual (60s - 180s)
    score, _ = compute_temporal_score(120.0)
    assert 0.3 <= score <= 0.7

    # Outside window (> 600s)
    score, _ = compute_temporal_score(700.0)
    assert score == 0.0

def test_graph_distance_scoring():
    assert compute_graph_distance_score(0)[0] == 1.0
    assert compute_graph_distance_score(1)[0] == 0.9
    assert compute_graph_distance_score(2)[0] == 0.7
    assert compute_graph_distance_score(3)[0] == 0.5
    assert compute_graph_distance_score(None)[0] == 0.0

def test_dependency_scoring(test_topology_graph):
    # Same service
    score, _ = compute_dependency_score("postgresql", "postgresql", test_topology_graph)
    assert score == 1.0

    # Direct dependency: order-api -> postgresql
    score, _ = compute_dependency_score("order-api", "postgresql", test_topology_graph)
    assert score == 1.0

    # Transitive dependency: checkout-api -> order-api -> postgresql
    score, _ = compute_dependency_score("checkout-api", "postgresql", test_topology_graph)
    assert score == 0.8

    # Unrelated / disconnected service
    score, _ = compute_dependency_score("unrelated-service", "postgresql", test_topology_graph)
    assert score == 0.0

def test_causal_order_scoring(test_topology_graph):
    # PostgreSQL (upstream) failing at T=0, Order API failing at T=5
    # Natural causal propagation: upstream fails before downstream caller
    alert_pg = Alert(
        id="alt_pg", timestamp="2026-09-05T00:00:00Z", service="postgresql",
        severity="CRITICAL", alert_type="DB_LOCK", metric="latency", metric_value=500,
        threshold=100, message="DB locked"
    )
    alert_order = Alert(
        id="alt_order", timestamp="2026-09-05T00:00:05Z", service="order-api",
        severity="CRITICAL", alert_type="DATABASE_TIMEOUT", metric="timeout_count",
        metric_value=10, threshold=1, message="Timeout connecting to DB"
    )

    score, reason = compute_causal_order_score(alert_pg, alert_order, test_topology_graph, 0.0, 5.0)
    assert score == 1.0
    assert "upstream dependency postgresql" in reason

def test_pairwise_score_deterministic_and_bounded(test_topology_graph):
    alert_pg = Alert(
        id="alt_pg", timestamp="2026-09-05T00:00:00Z", service="postgresql",
        severity="CRITICAL", alert_type="DB_QUERY_SLOW", metric="db_latency_ms",
        metric_value=450.0, threshold=100.0, message="Slow queries on orders table"
    )
    alert_order = Alert(
        id="alt_order", timestamp="2026-09-05T00:00:02Z", service="order-api",
        severity="CRITICAL", alert_type="DATABASE_TIMEOUT", metric="query_timeout_rate",
        metric_value=0.5, threshold=0.05, message="Database timeout"
    )

    score_1 = calculate_pairwise_score(alert_pg, alert_order, test_topology_graph)
    score_2 = calculate_pairwise_score(alert_pg, alert_order, test_topology_graph)

    # Determinism
    assert score_1.total_score == score_2.total_score
    assert score_1.reasons == score_2.reasons

    # High correlation between direct cascade neighbors
    assert score_1.total_score >= 0.70
    assert score_1.dependency_score == 1.0
    assert score_1.graph_distance_score == 0.9

def test_disconnected_services_score_low(test_topology_graph):
    alert_pg = Alert(
        id="alt_pg", timestamp="2026-09-05T00:00:00Z", service="postgresql",
        severity="CRITICAL", alert_type="DB_LOCK", metric="latency", metric_value=500,
        threshold=100, message="DB locked"
    )
    alert_unrelated = Alert(
        id="alt_iso", timestamp="2026-09-05T00:00:02Z", service="unrelated-service",
        severity="WARNING", alert_type="MEM_WARNING", metric="mem_pct", metric_value=75,
        threshold=70, message="High memory"
    )

    ps = calculate_pairwise_score(alert_pg, alert_unrelated, test_topology_graph)
    # Score should be low because topology distance is disconnected (0.0) and dependency is 0.0
    assert ps.dependency_score == 0.0
    assert ps.graph_distance_score == 0.0
    assert ps.total_score < 0.45
