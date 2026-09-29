import logging
import httpx
from typing import Dict, List, Any, Optional, Tuple
from app.config import settings
from .discovery_models import DiscoveredNode, DiscoveredEdge, current_iso_timestamp
from .telemetry_source import BaseTelemetrySource

logger = logging.getLogger("opspilot.topology.grafana_source")

class GrafanaTelemetrySource(BaseTelemetrySource):
    """
    Read-only Grafana observability source.
    Inspects Grafana HTTP API (/api/health, /api/datasources, /api/ds/query)
    to query service graph metrics or distributed tracing dependencies.
    Fails completely gracefully if Grafana is offline or unconfigured.
    """
    def __init__(
        self,
        base_url: Optional[str] = None,
        grafana_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        enabled: Optional[bool] = None,
        client: Optional[Any] = None
    ):
        target_url = base_url or grafana_url or settings.grafana_url
        self.base_url = target_url.rstrip("/")
        self.api_key = api_key or settings.grafana_api_key
        self.timeout = timeout_seconds or settings.grafana_timeout_seconds
        self.enabled = enabled if enabled is not None else settings.grafana_enabled
        self._custom_client = client
        self.is_connected = False
        self.last_check_status = "uninitialized"

    def check_connection(self) -> bool:
        return self.check_availability()

    @property
    def name(self) -> str:
        return "grafana"

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _execute_request(self, method: str, path: str, **kwargs) -> Any:
        if self._custom_client is not None:
            return self._custom_client.request(method, path, **kwargs)
        headers = {**self._get_headers(), **kwargs.pop("headers", {})}
        with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
            return client.request(method, path, headers=headers, **kwargs)

    def check_availability(self) -> bool:
        if not self.enabled:
            self.is_connected = False
            self.last_check_status = "disabled"
            return False
        try:
            res = self._execute_request("GET", "/api/health")
            self.is_connected = (res.status_code == 200)
            self.last_check_status = "online" if self.is_connected else f"http_{res.status_code}"
            return self.is_connected
        except Exception as e:
            logger.debug(f"Grafana probe to {self.base_url}/api/health failed (offline): {e}")
            self.is_connected = False
            self.last_check_status = "offline"
            return False

    def fetch_datasources(self) -> List[Dict[str, Any]]:
        if not self.check_availability():
            return []
        try:
            res = self._execute_request("GET", "/api/datasources")
            if res.status_code == 200:
                return res.json()
            return []
        except Exception as e:
            logger.debug(f"Failed to fetch Grafana datasources: {e}")
            return []

    def observe(
        self,
        logs: Optional[List[Dict[str, Any]]] = None,
        alerts: Optional[List[Dict[str, Any]]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        health_data: Optional[Dict[str, Any]] = None,
        events: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[List[DiscoveredNode], List[DiscoveredEdge]]:
        """
        Queries Grafana datasources for service dependency graph telemetry.
        If Grafana is offline or returns empty/unsupported datasources,
        returns empty lists cleanly without raising exceptions.
        """
        if not self.check_availability():
            return [], []

        discovered_nodes: Dict[str, DiscoveredNode] = {}
        discovered_edges: Dict[Tuple[str, str], DiscoveredEdge] = {}

        try:
            # Query datasources for Prometheus / Tempo / ServiceGraph metrics
            datasources = self.fetch_datasources()
            for ds in datasources:
                ds_type = ds.get("type", "").lower()
                ds_id = ds.get("id")
                if "prometheus" in ds_type or "tempo" in ds_type or "loki" in ds_type:
                    logger.info(f"Inspecting Grafana datasource: {ds.get('name')} (type: {ds_type})")
                    # In a connected Grafana instance, query traces_service_graph_request_total
                    # Example proxy query: /api/datasources/proxy/{id}/api/v1/query?query=traces_service_graph_request_total
                    try:
                        query_path = f"/api/datasources/proxy/{ds_id}/api/v1/query"
                        query_params = {"query": "traces_service_graph_request_total"}
                        res = self._execute_request("GET", query_path, params=query_params)
                        if res.status_code == 200:
                            data = res.json()
                            results = data.get("data", {}).get("result", [])
                            for item in results:
                                metric = item.get("metric", {})
                                client_svc = metric.get("client") or metric.get("client_service") or metric.get("service")
                                server_svc = metric.get("server") or metric.get("server_service") or metric.get("target")
                                if client_svc and server_svc and client_svc != server_svc:
                                    now = current_iso_timestamp()
                                    if client_svc not in discovered_nodes:
                                        discovered_nodes[client_svc] = DiscoveredNode(
                                            id=client_svc,
                                            name=client_svc,
                                            sources=["grafana"]
                                        )
                                    if server_svc not in discovered_nodes:
                                        discovered_nodes[server_svc] = DiscoveredNode(
                                            id=server_svc,
                                            name=server_svc,
                                            sources=["grafana"]
                                        )
                                    key = (client_svc, server_svc)
                                    discovered_edges[key] = DiscoveredEdge(
                                        source=client_svc,
                                        target=server_svc,
                                        protocol="HTTP",
                                        type="sync",
                                        observed=True,
                                        evidence_count=1,
                                        first_observed=now,
                                        last_observed=now,
                                        confidence=0.85,
                                        evidence_sources=["grafana_service_graph"],
                                        sample_evidence=[{"metric": metric, "value": item.get("value")}]
                                    )
                    except Exception as q_err:
                        logger.debug(f"Grafana datasource proxy query returned: {q_err}")

        except Exception as e:
            logger.debug(f"Grafana observation pass encountered notice: {e}")

        return list(discovered_nodes.values()), list(discovered_edges.values())

grafana_telemetry_source = GrafanaTelemetrySource()
