from typing import List, Dict, Any
from .models import ChaosScenario, ChaosStage

SCENARIO_DATABASE_CASCADE = ChaosScenario(
    id="database_cascade",
    name="Database Cascade Outage",
    description="PostgreSQL slow queries and connection pool exhaustion cascading upstream to Order API, Checkout API, and API Gateway.",
    severity="CRITICAL",
    primary_fault_service="postgresql",
    duration_seconds=60,
    stages=[
        ChaosStage(
            stage=1,
            name="DB Query Degradation",
            offset_seconds=0,
            service="postgresql",
            state="Degraded",
            customer_impact="none",
            description="Initial database query lock contention causing latency spike.",
            metrics_override={
                "db_latency_ms": 450.0,
                "latency_p50_ms": 120.0,
                "latency_p90_ms": 450.0,
                "latency_p99_ms": 890.0,
                "db_connections_active": 15,
                "db_connections_idle": 5,
                "cpu_pct": 68.5,
                "status": "Degraded"
            }
        ),
        ChaosStage(
            stage=2,
            name="Connection Pool Exhaustion",
            offset_seconds=2,
            service="postgresql",
            state="Major Outage",
            customer_impact="low",
            description="PostgreSQL connection pool completely saturated. Connection queue growing.",
            metrics_override={
                "db_latency_ms": 2400.0,
                "latency_p50_ms": 850.0,
                "latency_p90_ms": 2400.0,
                "latency_p99_ms": 4800.0,
                "db_connections_active": 20,
                "db_connections_idle": 0,
                "db_error_count": 18,
                "cpu_pct": 89.2,
                "error_rate_pct": 25.0,
                "status": "Major Outage"
            }
        ),
        ChaosStage(
            stage=3,
            name="Order API Slowdown & Timeout",
            offset_seconds=4,
            service="order-api",
            state="Degraded",
            customer_impact="medium",
            description="Order API experiencing DB query timeouts and connection pool wait queue overflow.",
            metrics_override={
                "latency_p50_ms": 1450.0,
                "latency_p90_ms": 3200.0,
                "latency_p99_ms": 5800.0,
                "error_rate_pct": 48.0,
                "availability_pct": 62.0,
                "active_requests": 28,
                "status": "Degraded"
            }
        ),
        ChaosStage(
            stage=4,
            name="Checkout Orchestrator Failure",
            offset_seconds=6,
            service="checkout-api",
            state="Major Outage",
            customer_impact="high",
            description="Checkout API failing transactions due to downstream Order API and DB connection failures.",
            metrics_override={
                "latency_p50_ms": 2100.0,
                "latency_p90_ms": 4500.0,
                "latency_p99_ms": 7200.0,
                "error_rate_pct": 88.0,
                "availability_pct": 18.0,
                "active_requests": 42,
                "memory_pct": 84.0,
                "status": "Major Outage"
            }
        ),
        ChaosStage(
            stage=5,
            name="API Gateway 502/504 Spike",
            offset_seconds=8,
            service="api-gateway",
            state="Degraded",
            customer_impact="high",
            description="Gateway experiencing upstream timeout errors (504 Gateway Timeout) on order and checkout routes.",
            metrics_override={
                "latency_p50_ms": 950.0,
                "latency_p90_ms": 2800.0,
                "latency_p99_ms": 5500.0,
                "error_rate_pct": 64.0,
                "availability_pct": 52.0,
                "cpu_pct": 74.0,
                "status": "Degraded"
            }
        ),
        ChaosStage(
            stage=6,
            name="Customer Checkout Degradation",
            offset_seconds=10,
            service="shopflow-frontend",
            state="Degraded",
            customer_impact="critical",
            description="Customer checkout unavailable. Graceful degradation messages active.",
            metrics_override={}
        )
    ]
)

SCENARIO_REDIS_FAILURE = ChaosScenario(
    id="redis_failure",
    name="Redis Cache Outage",
    description="Redis server becomes unresponsive, triggering cache miss storm and high latency on product catalog queries.",
    severity="HIGH",
    primary_fault_service="redis",
    duration_seconds=45,
    stages=[
        ChaosStage(
            stage=1,
            name="Redis Connection Drop",
            offset_seconds=0,
            service="redis",
            state="Major Outage",
            customer_impact="low",
            description="Redis connection dropped. PING command timeouts.",
            metrics_override={
                "redis_latency_ms": 1500.0,
                "redis_hits": 0,
                "redis_misses": 450,
                "error_rate_pct": 95.0,
                "availability_pct": 0.0,
                "status": "Major Outage"
            }
        ),
        ChaosStage(
            stage=2,
            name="Product API Cache Miss Storm",
            offset_seconds=2,
            service="product-api",
            state="Degraded",
            customer_impact="low",
            description="Product API falling back directly to DB for every catalog query, increasing response latency.",
            metrics_override={
                "latency_p50_ms": 280.0,
                "latency_p90_ms": 520.0,
                "cpu_pct": 65.0,
                "status": "Degraded"
            }
        )
    ]
)

SCENARIO_HIGH_MEMORY = ChaosScenario(
    id="high_memory",
    name="Checkout API Memory Leak",
    description="Checkout service accumulates uncollected memory buffers leading to GC pauses and sluggish processing.",
    severity="MEDIUM",
    primary_fault_service="checkout-api",
    duration_seconds=40,
    stages=[
        ChaosStage(
            stage=1,
            name="Memory Saturation",
            offset_seconds=0,
            service="checkout-api",
            state="Degraded",
            customer_impact="low",
            description="Process resident set size exceeding 94% threshold.",
            metrics_override={
                "memory_pct": 94.8,
                "latency_p50_ms": 380.0,
                "latency_p90_ms": 820.0,
                "status": "Degraded"
            }
        )
    ]
)

SCENARIO_HIGH_LATENCY = ChaosScenario(
    id="high_latency",
    name="Inter-Service Network Latency",
    description="Network packet delay injected across internal service mesh, causing response slowdown.",
    severity="MEDIUM",
    primary_fault_service="api-gateway",
    duration_seconds=40,
    stages=[
        ChaosStage(
            stage=1,
            name="Network Delay Injection",
            offset_seconds=0,
            service="api-gateway",
            state="Degraded",
            customer_impact="medium",
            description="Gateway round-trip time elevated to 1800ms.",
            metrics_override={
                "latency_p50_ms": 850.0,
                "latency_p90_ms": 1800.0,
                "latency_p99_ms": 3200.0,
                "status": "Degraded"
            }
        )
    ]
)

SCENARIO_TRAFFIC_SPIKE = ChaosScenario(
    id="traffic_spike",
    name="Flash Sale Traffic Surge",
    description="10x surge in incoming visitor requests causing queue build-up and throttling.",
    severity="MEDIUM",
    primary_fault_service="api-gateway",
    duration_seconds=45,
    stages=[
        ChaosStage(
            stage=1,
            name="Surge Ingress",
            offset_seconds=0,
            service="api-gateway",
            state="Degraded",
            customer_impact="low",
            description="Incoming RPS climbed from 65 RPS to 720 RPS.",
            metrics_override={
                "request_rate_rps": 720.0,
                "cpu_pct": 91.5,
                "active_requests": 95,
                "latency_p90_ms": 480.0,
                "status": "Degraded"
            }
        )
    ]
)

SCENARIO_CHECKOUT_FAILURE = ChaosScenario(
    id="checkout_failure",
    name="Payment Simulator Error",
    description="Simulated payment processor rejection causing isolated checkout transaction failures.",
    severity="HIGH",
    primary_fault_service="checkout-api",
    duration_seconds=35,
    stages=[
        ChaosStage(
            stage=1,
            name="Payment Rejection Storm",
            offset_seconds=0,
            service="checkout-api",
            state="Major Outage",
            customer_impact="high",
            description="Payment simulator rejecting card tokens with simulated upstream gateway 500.",
            metrics_override={
                "error_rate_pct": 100.0,
                "availability_pct": 0.0,
                "status": "Major Outage"
            }
        )
    ]
)

SCENARIO_UNKNOWN_ISSUE = ChaosScenario(
    id="unknown_issue",
    name="Multi-Service Anomaly",
    description="Anomalous metric jitter across multiple services without clear fatal crash.",
    severity="LOW",
    primary_fault_service="product-api",
    duration_seconds=30,
    stages=[
        ChaosStage(
            stage=1,
            name="Intermittent Latency Jitter",
            offset_seconds=0,
            service="product-api",
            state="Degraded",
            customer_impact="low",
            description="Random 150-350ms spikes observed across catalog search endpoints.",
            metrics_override={
                "latency_p50_ms": 180.0,
                "latency_p90_ms": 350.0,
                "status": "Degraded"
            }
        )
    ]
)

ALL_SCENARIOS: Dict[str, ChaosScenario] = {
    "database_cascade": SCENARIO_DATABASE_CASCADE,
    "redis_failure": SCENARIO_REDIS_FAILURE,
    "high_memory": SCENARIO_HIGH_MEMORY,
    "high_latency": SCENARIO_HIGH_LATENCY,
    "traffic_spike": SCENARIO_TRAFFIC_SPIKE,
    "checkout_failure": SCENARIO_CHECKOUT_FAILURE,
    "unknown_issue": SCENARIO_UNKNOWN_ISSUE,
}
