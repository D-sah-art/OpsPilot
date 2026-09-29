import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.topology.discovery_models import DiscoveredNode, DiscoveredEdge, DiscoveredTopologyResult
from app.topology.telemetry_source import ApplicationTelemetrySource
from app.topology.grafana_source import GrafanaTelemetrySource
from app.topology.discovery import TopologyDiscoveryEngine
from app.topology.graph import dependency_graph
from app.main import app

def test_telemetry_source_extracts_nodes_and_edges_from_logs():
    source = ApplicationTelemetrySource()
    logs = [
        {"service": "checkout-api", "dependency": "order-api", "event": "HTTP_CALL", "message": "Calling order service", "status_code": 200},
        {"service": "order-api", "dependency": "postgresql", "event": "SQL_QUERY", "message": "Querying orders table"},
        {"service": "api-gateway", "message": "POST /api/checkout HTTP/1.1 200 OK"}
    ]
    nodes, edges = source.observe(logs=logs)
    
    node_ids = {n.id for n in nodes}
    assert "checkout-api" in node_ids
    assert "order-api" in node_ids
    assert "postgresql" in node_ids
    assert "api-gateway" in node_ids
    assert "shopflow-frontend" in node_ids  # Inferred ingress tier

    edge_tuples = {(e.source, e.target) for e in edges}
    assert ("checkout-api", "order-api") in edge_tuples
    assert ("order-api", "postgresql") in edge_tuples
    assert ("api-gateway", "checkout-api") in edge_tuples
    assert ("shopflow-frontend", "api-gateway") in edge_tuples

def test_telemetry_source_extracts_edges_from_alerts_and_health():
    source = ApplicationTelemetrySource()
    alerts = [
        {"service": "order-api", "dependency": "postgresql", "severity": "CRITICAL", "alert_type": "DB_CONNECTION_TIMEOUT", "message": "Connection timed out"}
    ]
    health_data = {
        "service": "checkout-api",
        "dependencies": {
            "order-api": "healthy",
            "product-api": "healthy"
        }
    }
    nodes, edges = source.observe(alerts=alerts, health_data=health_data)
    edge_tuples = {(e.source, e.target) for e in edges}
    
    assert ("order-api", "postgresql") in edge_tuples
    assert ("checkout-api", "order-api") in edge_tuples
    assert ("checkout-api", "product-api") in edge_tuples

def test_evidence_accumulation_and_confidence_growth():
    engine = TopologyDiscoveryEngine()
    engine.reset()
    
    # First observation
    batch_1 = [{"service": "checkout-api", "dependency": "order-api", "message": "Call 1"}]
    res1 = engine.discover_from_sync(logs=batch_1)
    
    edge_key = ("checkout-api", "order-api")
    assert edge_key in engine.discovered_edges
    edge = engine.discovered_edges[edge_key]
    assert edge.evidence_count == 1
    initial_conf = edge.confidence
    assert 0.5 <= initial_conf <= 0.7
    
    # Subsequent observations increase evidence count and confidence
    for i in range(2, 8):
        batch = [{"service": "checkout-api", "dependency": "order-api", "message": f"Call {i}"}]
        engine.discover_from_sync(logs=batch)
        
    updated_edge = engine.discovered_edges[edge_key]
    assert updated_edge.evidence_count == 7
    assert updated_edge.confidence > initial_conf
    assert updated_edge.confidence <= 0.99
    assert "application_logs" in updated_edge.evidence_sources

def test_grafana_source_offline_graceful_handling():
    # Points to non-existent port 39999
    grafana = GrafanaTelemetrySource(grafana_url="http://127.0.0.1:39999", enabled=True, timeout_seconds=0.5)
    connected = grafana.check_connection()
    assert connected is False
    assert grafana.last_check_status == "offline"
    
    # Observe should not throw any exceptions
    nodes, edges = grafana.observe()
    assert len(nodes) == 0
    assert len(edges) == 0

def test_grafana_source_mock_metrics_and_loki():
    grafana = GrafanaTelemetrySource(base_url="http://mock-grafana:3000", enabled=True)
    grafana.check_availability = MagicMock(return_value=True)
    grafana.is_connected = True
    grafana.fetch_datasources = MagicMock(return_value=[{"id": 1, "name": "Prometheus", "type": "prometheus"}])
    
    mock_prom_response = MagicMock()
    mock_prom_response.status_code = 200
    mock_prom_response.json.return_value = {
        "data": {
            "result": [
                {"metric": {"client": "checkout-api", "server": "order-api"}},
                {"metric": {"client": "order-api", "server": "postgresql"}}
            ]
        }
    }
    
    grafana._execute_request = MagicMock(return_value=mock_prom_response)
    
    nodes, edges = grafana.observe()
    edge_tuples = {(e.source, e.target) for e in edges}
    assert ("checkout-api", "order-api") in edge_tuples
    assert ("order-api", "postgresql") in edge_tuples

def test_fallback_activation_when_telemetry_cold():
    engine = TopologyDiscoveryEngine()
    engine.reset()
    
    fallback = {
        "nodes": [
            {"id": "service-a", "name": "Service A", "type": "service", "tier": "core"},
            {"id": "service-b", "name": "Service B", "type": "database", "tier": "data"}
        ],
        "edges": [
            {"source": "service-a", "target": "service-b", "protocol": "TCP/SQL"}
        ]
    }
    
    # Sync with NO telemetry logs/alerts/metrics
    res = engine.discover_from_sync(fallback_topology=fallback, logs=[], alerts=[], metrics={}, health_data={})
    assert res.source == "fallback"
    assert "Fallback" in res.discovery_source
    assert res.total_nodes == 2
    assert res.total_edges == 1
    
    # Now send telemetry observing service-a calling service-b
    res2 = engine.discover_from_sync(logs=[{"service": "service-a", "dependency": "service-b"}])
    assert res2.source == "discovered"
    assert "Observed Runtime Telemetry" in res2.discovery_source
    
    edge_in_result = next(e for e in res2.edges if e["source"] == "service-a" and e["target"] == "service-b")
    assert edge_in_result["observed"] is True
    assert edge_in_result["evidence_count"] >= 1

def test_api_routes_get_and_post_topology(client):
    # Test GET /api/topology
    get_res = client.get("/api/topology")
    assert get_res.status_code == 200
    data = get_res.json()
    assert "nodes" in data
    assert "edges" in data
    assert "total_nodes" in data
    assert "total_edges" in data
    assert "source" in data
    assert "discovery_source" in data
    assert "grafana_connected" in data
    assert "grafana_status" in data
    assert data["source"] in ("discovered", "fallback")
    
    # Test POST /api/topology/discover
    post_res = client.post("/api/topology/discover")
    assert post_res.status_code == 200
    discover_data = post_res.json()
    assert "source" in discover_data
    assert "total_nodes" in discover_data
    assert "total_edges" in discover_data
    assert "evidence_summary" in discover_data

def test_discovered_topology_preserves_rca_graph_algorithms():
    engine = TopologyDiscoveryEngine()
    engine.reset()
    
    # Discovery produces multi-tier graph
    engine.discover_from_sync(
        logs=[
            {"service": "api-gateway", "dependency": "checkout-api"},
            {"service": "checkout-api", "dependency": "order-api"},
            {"service": "order-api", "dependency": "postgresql"},
            {"service": "product-api", "dependency": "postgresql"}
        ]
    )
    
    # Verify dependency_graph traversal functions
    deps_of_checkout = dependency_graph.get_dependencies("checkout-api")
    assert "order-api" in deps_of_checkout
    
    dependents_of_pg = dependency_graph.get_dependents("postgresql")
    assert "order-api" in dependents_of_pg
    assert "product-api" in dependents_of_pg
    
    # Shortest path from api-gateway to postgresql should traverse checkout-api and order-api
    path = dependency_graph.get_shortest_path("api-gateway", "postgresql")
    assert path == ["api-gateway", "checkout-api", "order-api", "postgresql"]

def test_dynamic_discovery_novel_unconfigured_service():
    engine = TopologyDiscoveryEngine()
    engine.reset()
    
    # Observe an unexpected service not in any baseline
    logs = [
        {"service": "payment-v2", "dependency": "postgresql", "message": "Novel payment service query"}
    ]
    res = engine.discover_from_sync(logs=logs)
    assert res.source == "discovered"
    node_ids = [n["id"] for n in res.nodes]
    assert "payment-v2" in node_ids
    assert "postgresql" in node_ids
    
    edge_pairs = [(e["source"], e["target"]) for e in res.edges]
    assert ("payment-v2", "postgresql") in edge_pairs

def test_grafana_datasource_bad_status_graceful_handling():
    grafana = GrafanaTelemetrySource(base_url="http://mock-grafana:3000", enabled=True)
    grafana.check_availability = MagicMock(return_value=True)
    grafana.is_connected = True
    grafana.fetch_datasources = MagicMock(return_value=[{"id": 99, "name": "Broken Prometheus", "type": "prometheus"}])
    
    # Simulate 500 error from datasource proxy
    mock_err_response = MagicMock()
    mock_err_response.status_code = 500
    mock_err_response.text = "Internal Server Error"
    grafana._execute_request = MagicMock(return_value=mock_err_response)
    
    nodes, edges = grafana.observe()
    assert len(nodes) == 0
    assert len(edges) == 0

def test_topology_result_to_dict_and_serialization():
    result = DiscoveredTopologyResult(
        source="discovered",
        discovered_at="2026-09-06T00:00:00Z",
        discovery_source="Observed Runtime Telemetry",
        grafana_connected=False,
        grafana_status="offline",
        total_nodes=2,
        total_edges=1,
        nodes=[{"id": "a"}, {"id": "b"}],
        edges=[{"source": "a", "target": "b"}],
        evidence_summary={"observations": 5}
    )
    d = result.to_dict()
    assert d["source"] == "discovered"
    assert d["grafana_connected"] is False
    assert d["total_nodes"] == 2
    assert d["total_edges"] == 1
    assert "evidence" in d
    assert "evidence_summary" in d

def test_topology_discovery_engine_reset():
    engine = TopologyDiscoveryEngine()
    engine.discover_from_sync(logs=[{"service": "svc-x", "dependency": "svc-y"}])
    assert len(engine.discovered_nodes) > 0
    assert len(engine.discovered_edges) > 0
    assert engine.is_active_discovery is True
    
    engine.reset()
    assert len(engine.discovered_nodes) == 0
    assert len(engine.discovered_edges) == 0
    assert engine.is_active_discovery is False

def test_multi_source_evidence_aggregation():
    engine = TopologyDiscoveryEngine()
    engine.reset()
    
    # Observe same edge through logs, alerts, and health checks
    logs = [{"service": "checkout-api", "dependency": "order-api"}]
    alerts = [{"service": "checkout-api", "dependency": "order-api", "severity": "WARNING", "alert_type": "HIGH_LATENCY"}]
    health = {"service": "checkout-api", "dependencies": {"order-api": "healthy"}}
    
    res = engine.discover_from_sync(logs=logs, alerts=alerts, health_data=health)
    edge = next(e for e in res.edges if e["source"] == "checkout-api" and e["target"] == "order-api")
    
    assert edge["observed"] is True
    assert edge["evidence_count"] >= 3
    sources = set(edge["evidence_sources"])
    assert "application_logs" in sources
    assert "application_alerts" in sources
    assert "service_health" in sources

def test_topology_graph_undirected_distance_calculation():
    engine = TopologyDiscoveryEngine()
    engine.reset()
    
    engine.discover_from_sync(
        logs=[
            {"service": "frontend", "dependency": "gateway"},
            {"service": "gateway", "dependency": "api-service"},
            {"service": "api-service", "dependency": "database"}
        ]
    )
    
    # Verify distance across 3 hops
    dist = dependency_graph.dependency_distance("frontend", "database")
    assert dist == 3
    # Reverse direction
    dist_rev = dependency_graph.dependency_distance("database", "frontend")
    assert dist_rev == 3

