import pytest
from app.models.alert import Alert
from app.topology.graph import DependencyGraph
from app.correlation.strategies.time_only import TimeOnlyStrategy
from app.correlation.strategies.dependency_aware import DependencyAwareStrategy

@pytest.fixture
def topology():
    graph = DependencyGraph()
    nodes = [
        {"id": "api-gateway", "name": "API Gateway"},
        {"id": "checkout-api", "name": "Checkout API"},
        {"id": "order-api", "name": "Order API"},
        {"id": "postgresql", "name": "PostgreSQL"},
        {"id": "auth-service", "name": "Auth Service"},
        {"id": "isolated-worker", "name": "Isolated Worker"}
    ]
    edges = [
        {"source": "api-gateway", "target": "checkout-api"},
        {"source": "api-gateway", "target": "auth-service"},
        {"source": "checkout-api", "target": "order-api"},
        {"source": "order-api", "target": "postgresql"},
    ]
    graph.load_from_topology(nodes, edges)
    return graph

def test_time_only_strategy_groups_by_window(topology):
    strategy = TimeOnlyStrategy()
    
    # 3 alerts within 10 seconds
    alerts = [
        Alert(id="a1", timestamp="2026-09-05T00:00:00Z", service="postgresql", severity="CRITICAL", alert_type="SLOW_QUERY", metric="latency", metric_value=400, threshold=100, message="slow"),
        Alert(id="a2", timestamp="2026-09-05T00:00:03Z", service="order-api", severity="CRITICAL", alert_type="TIMEOUT", metric="latency", metric_value=3000, threshold=100, message="timeout"),
        Alert(id="a3", timestamp="2026-09-05T00:00:06Z", service="isolated-worker", severity="WARNING", alert_type="HIGH_CPU", metric="cpu", metric_value=85, threshold=70, message="cpu"),
        # 1 alert 5 minutes later
        Alert(id="a4", timestamp="2026-09-05T00:05:00Z", service="postgresql", severity="INFO", alert_type="SLOW_QUERY", metric="latency", metric_value=120, threshold=100, message="minor slow")
    ]

    incidents = strategy.correlate(alerts, topology, time_window_seconds=45.0)

    # Time-only groups a1, a2, a3 together because of time proximity (falsely merging isolated-worker)
    # and splits a4 into a second incident because of time gap
    assert len(incidents) == 2
    assert incidents[0].alert_count == 3
    assert "isolated-worker" in incidents[0].affected_services  # False merge!
    assert incidents[1].alert_count == 1
    assert incidents[1].alert_ids == ["a4"]

def test_dependency_aware_separates_unrelated_services(topology):
    strategy = DependencyAwareStrategy()

    # 3 cascade alerts + 1 simultaneous unrelated alert on isolated worker
    alerts = [
        Alert(id="a1", timestamp="2026-09-05T00:00:00Z", service="postgresql", severity="CRITICAL", alert_type="DB_QUERY_SLOW", metric="latency", metric_value=500, threshold=100, message="slow"),
        Alert(id="a2", timestamp="2026-09-05T00:00:02Z", service="order-api", severity="CRITICAL", alert_type="DATABASE_TIMEOUT", metric="timeout", metric_value=5, threshold=1, message="timeout"),
        Alert(id="a3", timestamp="2026-09-05T00:00:04Z", service="checkout-api", severity="CRITICAL", alert_type="CHECKOUT_FAILED", metric="errors", metric_value=10, threshold=1, message="fail"),
        Alert(id="a_unrelated", timestamp="2026-09-05T00:00:02Z", service="isolated-worker", severity="WARNING", alert_type="HIGH_CPU", metric="cpu", metric_value=85, threshold=70, message="cpu")
    ]

    incidents = strategy.correlate(alerts, topology, time_window_seconds=600.0, threshold=0.45)

    # Dependency-aware correctly identifies 2 distinct incidents:
    # 1. The cascade incident (postgresql, order-api, checkout-api)
    # 2. The isolated incident (isolated-worker)
    assert len(incidents) == 2

    cascade_inc = next(inc for inc in incidents if "postgresql" in inc.affected_services)
    assert cascade_inc.alert_count == 3
    assert set(cascade_inc.affected_services) == {"postgresql", "order-api", "checkout-api"}
    assert "isolated-worker" not in cascade_inc.affected_services

    isolated_inc = next(inc for inc in incidents if "isolated-worker" in inc.affected_services)
    assert isolated_inc.alert_count == 1
    assert isolated_inc.affected_services == ["isolated-worker"]

def test_dependency_aware_correlation_determinism(topology):
    strategy = DependencyAwareStrategy()

    alerts = [
        Alert(id="alt_1", timestamp="2026-09-05T00:00:00Z", service="postgresql", severity="CRITICAL", alert_type="DB_LOCK", metric="latency", metric_value=500, threshold=100, message="lock"),
        Alert(id="alt_2", timestamp="2026-09-05T00:00:03Z", service="order-api", severity="CRITICAL", alert_type="TIMEOUT", metric="latency", metric_value=3000, threshold=100, message="timeout"),
        Alert(id="alt_3", timestamp="2026-09-05T00:00:06Z", service="checkout-api", severity="CRITICAL", alert_type="CHECKOUT_FAIL", metric="err", metric_value=10, threshold=1, message="err"),
        Alert(id="alt_4", timestamp="2026-09-05T00:00:08Z", service="api-gateway", severity="CRITICAL", alert_type="504_GATEWAY", metric="5xx", metric_value=10, threshold=1, message="504"),
    ]

    results = []
    for _ in range(5):
        incidents = strategy.correlate(alerts, topology)
        results.append(incidents)

    # Assert all 5 runs produced identical results
    first_run = results[0]
    for other_run in results[1:]:
        assert len(first_run) == len(other_run)
        for inc1, inc2 in zip(first_run, other_run):
            assert inc1.incident_id == inc2.incident_id
            assert inc1.alert_ids == inc2.alert_ids
            assert inc1.affected_services == inc2.affected_services
            assert inc1.correlation_score == inc2.correlation_score
