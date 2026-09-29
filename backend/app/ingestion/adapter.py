import time
import httpx
import logging
from typing import Dict, List, Any, Optional
from app.config import settings

logger = logging.getLogger("opspilot.shopflow_adapter")

class ShopFlowAdapter:
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        client: Optional[Any] = None
    ):
        self.base_url = (base_url or settings.shopflow_base_url).rstrip('/')
        self.timeout = timeout or settings.shopflow_timeout_seconds
        self._custom_client = client

    def _execute_request(self, method: str, path: str, **kwargs) -> Any:
        if self._custom_client is not None:
            return self._custom_client.request(method, path, **kwargs)
        with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
            return client.request(method, path, **kwargs)

    def check_connectivity(self) -> bool:
        try:
            res = self._execute_request("GET", "/health")
            return res.status_code == 200
        except Exception as e:
            logger.debug(f"ShopFlow health probe failed: {e}")
            return False

    def get_health(self) -> Dict[str, Any]:
        try:
            res = self._execute_request("GET", "/health")
            res.raise_for_status()
            return res.json()
        except Exception as e:
            logger.debug(f"ShopFlow get_health failed: {e}")
            return {"status": "unreachable"}

    def probe_checkout(self) -> Dict[str, Any]:
        """
        Executes an active end-to-end synthetic checkout transaction health probe.
        Produces genuine observable evidence from ShopFlow /api/checkout.
        """
        payload = {
            "user_id": "usr_probe_synthetic",
            "user_email": "probe@opspilot.internal",
            "items": [
                {
                    "product_id": "prod_01",
                    "product_title": "Synthetic Probe Product",
                    "price": 29.99,
                    "quantity": 1
                }
            ],
            "shipping_address": {
                "street": "1 Probe Way",
                "city": "OpsPilot",
                "state": "CA",
                "zip": "94105",
                "country": "USA"
            },
            "payment_method": "Synthetic Probe (Automated)"
        }
        start_t = time.perf_counter()
        try:
            res = self._execute_request("POST", "/api/checkout", json=payload)
            elapsed_ms = (time.perf_counter() - start_t) * 1000.0
            if res.status_code == 200:
                data = res.json()
                return {
                    "success": bool(data.get("success", False)),
                    "status_code": res.status_code,
                    "latency_ms": round(elapsed_ms, 2),
                    "order_id": data.get("order_id"),
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "status_code": res.status_code,
                    "latency_ms": round(elapsed_ms, 2),
                    "order_id": None,
                    "error": f"HTTP {res.status_code}: {res.text[:100]}"
                }
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_t) * 1000.0
            return {
                "success": False,
                "status_code": 0,
                "latency_ms": round(elapsed_ms, 2),
                "order_id": None,
                "error": str(e)
            }

    def fetch_topology(self) -> Dict[str, Any]:
        try:
            res = self._execute_request("GET", "/api/topology")
            res.raise_for_status()
            return res.json()
        except Exception as e:
            logger.warning(f"Failed to fetch topology from {self.base_url}/api/topology: {e}")
            return {"nodes": [], "edges": []}

    def fetch_health_summary(self) -> Dict[str, Any]:
        try:
            res = self._execute_request("GET", "/api/health-summary")
            res.raise_for_status()
            return res.json()
        except Exception as e:
            logger.warning(f"Failed to fetch health summary from {self.base_url}/api/health-summary: {e}")
            return {"status": "Unknown", "healthy_services": 0, "total_services": 0}

    def fetch_metrics(self) -> Dict[str, Any]:
        try:
            res = self._execute_request("GET", "/telemetry/metrics")
            res.raise_for_status()
            return res.json()
        except Exception as e:
            logger.warning(f"Failed to fetch metrics from {self.base_url}/telemetry/metrics: {e}")
            return {"services": {}}

    def fetch_logs(self, limit: int = 100, service: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            params = {"limit": limit}
            if service:
                params["service"] = service
            res = self._execute_request("GET", "/telemetry/logs", params=params)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            logger.warning(f"Failed to fetch logs from {self.base_url}/telemetry/logs: {e}")
            return []

    def fetch_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            res = self._execute_request("GET", "/telemetry/alerts", params={"limit": limit})
            res.raise_for_status()
            return res.json()
        except Exception as e:
            logger.warning(f"Failed to fetch alerts from {self.base_url}/telemetry/alerts: {e}")
            return []

    def fetch_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            res = self._execute_request("GET", "/telemetry/events", params={"limit": limit})
            res.raise_for_status()
            return res.json()
        except Exception as e:
            logger.warning(f"Failed to fetch events from {self.base_url}/telemetry/events: {e}")
            return []

    def fetch_services(self) -> Dict[str, Any]:
        try:
            res = self._execute_request("GET", "/telemetry/services")
            res.raise_for_status()
            return res.json()
        except Exception as e:
            logger.warning(f"Failed to fetch services from {self.base_url}/telemetry/services: {e}")
            return {"services": {}}

    def reset_chaos(self) -> bool:
        """Calls ShopFlow's chaos reset endpoint to terminate active chaos scenarios and restore healthy state."""
        try:
            res = self._execute_request("POST", "/api/chaos/reset")
            return res.status_code == 200
        except Exception as e:
            logger.warning(f"Failed to reset chaos on {self.base_url}/api/chaos/reset: {e}")
            return False

# Default adapter instance
shopflow_adapter = ShopFlowAdapter()
