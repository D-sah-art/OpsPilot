from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import uuid

def current_iso_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()

class LogEntry(BaseModel):
    id: str = Field(default_factory=lambda: f"log_{uuid.uuid4().hex[:10]}")
    timestamp: str = Field(default_factory=current_iso_timestamp)
    service: str
    level: str = "INFO"  # INFO, WARN, ERROR, DEBUG
    event: str           # REQUEST_RECEIVED, REQUEST_COMPLETED, DATABASE_TIMEOUT, etc.
    message: str
    request_id: Optional[str] = None
    dependency: Optional[str] = None
    latency_ms: Optional[float] = None
    status_code: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Alert(BaseModel):
    id: str = Field(default_factory=lambda: f"alt_{uuid.uuid4().hex[:10]}")
    timestamp: str = Field(default_factory=current_iso_timestamp)
    service: str
    severity: str        # CRITICAL, WARNING, INFO
    alert_type: str      # HIGH_CPU, HIGH_MEMORY, HIGH_LATENCY, DB_CONNECTION_EXHAUSTION, etc.
    metric: str
    metric_value: float
    threshold: float
    message: str
    source: str = "shopflow-telemetry-agent"
    dependency: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)

class SystemEvent(BaseModel):
    id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:10]}")
    timestamp: str = Field(default_factory=current_iso_timestamp)
    service: str
    event_type: str      # SCENARIO_STARTED, SCENARIO_STAGE, SERVICE_DEGRADED, SERVICE_RECOVERED, RESET
    description: str
    severity: str = "INFO"
    payload: Dict[str, Any] = Field(default_factory=dict)

class ServiceMetrics(BaseModel):
    service: str
    timestamp: str = Field(default_factory=current_iso_timestamp)
    cpu_pct: float = 12.5
    memory_pct: float = 28.0
    request_rate_rps: float = 45.0
    latency_p50_ms: float = 18.0
    latency_p90_ms: float = 45.0
    latency_p99_ms: float = 95.0
    error_rate_pct: float = 0.0
    active_requests: int = 4
    http_status_counts: Dict[str, int] = Field(default_factory=lambda: {"200": 450, "400": 2, "500": 0})
    db_connections_active: int = 4
    db_connections_idle: int = 16
    db_connections_max: int = 20
    db_latency_ms: float = 4.5
    db_error_count: int = 0
    redis_latency_ms: float = 1.2
    redis_hits: int = 340
    redis_misses: int = 12
    availability_pct: float = 100.0
    status: str = "Operational"  # Operational, Degraded, Major Outage, Recovering
