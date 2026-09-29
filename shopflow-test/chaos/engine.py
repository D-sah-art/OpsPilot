import threading
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta

from .models import ChaosStatus, ChaosScenario
from .scenarios import ALL_SCENARIOS
from telemetry.engine import telemetry_engine
from telemetry.logger import get_logger
from telemetry.alerts import emit_alert
from telemetry.models import SystemEvent

logger = get_logger("chaos-engine")

class ChaosEngine:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ChaosEngine, cls).__new__(cls)
                cls._instance._init_engine()
            return cls._instance

    def _init_engine(self):
        self.status = ChaosStatus()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._mutex = threading.Lock()
        self.demo_mode = True

    def get_status(self) -> Dict[str, Any]:
        with self._mutex:
            if self.status.state == "RUNNING" and self.status.started_at:
                try:
                    start_dt = datetime.fromisoformat(self.status.started_at)
                    elapsed = int((datetime.now(timezone.utc) - start_dt).total_seconds())
                    self.status.elapsed_seconds = elapsed
                except Exception:
                    pass
            self.status.alert_count = len(telemetry_engine.alert_buffer)
            self.status.event_count = len(telemetry_engine.event_buffer)
            self.status.log_count = len(telemetry_engine.log_buffer)
            return self.status.model_dump()

    def list_scenarios(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "severity": s.severity,
                "primary_fault_service": s.primary_fault_service,
                "duration_seconds": s.duration_seconds,
                "stages_count": len(s.stages)
            }
            for s in ALL_SCENARIOS.values()
        ]

    def trigger_scenario(self, scenario_id: str) -> Dict[str, Any]:
        with self._mutex:
            if scenario_id not in ALL_SCENARIOS:
                raise ValueError(f"Unknown chaos scenario: {scenario_id}")

            # Stop any running scenario
            self._stop_event.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=1.0)

            self._stop_event.clear()
            scenario = ALL_SCENARIOS[scenario_id]

            now_iso = datetime.now(timezone.utc).isoformat()
            self.status = ChaosStatus(
                active_scenario=scenario.id,
                scenario_name=scenario.name,
                state="RUNNING",
                started_at=now_iso,
                elapsed_seconds=0,
                current_stage=1,
                total_stages=len(scenario.stages),
                affected_services=[scenario.primary_fault_service],
                recovery_status="DEGRADED",
                demo_mode=self.demo_mode
            )

            # Record Start Event & Log
            telemetry_engine.record_event(SystemEvent(
                service=scenario.primary_fault_service,
                event_type="CHAOS_SCENARIO_TRIGGERED",
                description=f"Chaos scenario '{scenario.name}' activated. Primary fault target: {scenario.primary_fault_service}",
                severity="WARNING",
                payload={"scenario_id": scenario.id, "severity": scenario.severity}
            ))

            logger.warn(
                "SCENARIO_STARTED",
                f"Chaos scenario {scenario_id} triggered. Primary fault: {scenario.primary_fault_service}",
                dependency=scenario.primary_fault_service,
                metadata={"scenario_id": scenario_id}
            )

            # Spawn runner thread
            if scenario_id == "database_cascade":
                self._thread = threading.Thread(target=self._run_database_cascade_scenario, daemon=True)
            else:
                self._thread = threading.Thread(target=self._run_generic_scenario, args=(scenario,), daemon=True)
            
            self._thread.start()
            return self.status.model_dump()

    def _run_generic_scenario(self, scenario: ChaosScenario):
        start_time = time.time()
        for idx, stage in enumerate(scenario.stages):
            if self._stop_event.is_set():
                return

            with self._mutex:
                self.status.current_stage = stage.stage
                if stage.service not in self.status.affected_services:
                    self.status.affected_services.append(stage.service)

            # Apply metrics override
            if stage.metrics_override:
                telemetry_engine.update_metrics(stage.service, **stage.metrics_override)

            # Emit stage event
            telemetry_engine.record_event(SystemEvent(
                service=stage.service,
                event_type="SCENARIO_STAGE_TRANSITION",
                description=f"Stage {stage.stage}/{len(scenario.stages)}: {stage.name} - {stage.description}",
                severity="WARNING" if stage.state == "Degraded" else "CRITICAL",
                payload={"stage": stage.stage, "state": stage.state}
            ))

            # Emit log
            logger.error(
                "SERVICE_DEGRADED",
                f"Service {stage.service} degraded: {stage.description}",
                dependency=stage.service,
                status_code=503 if stage.state == "Major Outage" else 500
            )

            # Emit alert
            emit_alert(
                service=stage.service,
                severity="CRITICAL" if stage.state == "Major Outage" else "WARNING",
                alert_type="SERVICE_DEGRADED",
                metric="availability_pct",
                metric_value=0.0 if stage.state == "Major Outage" else 65.0,
                threshold=99.0,
                message=f"Chaos injection: {stage.name} - {stage.description}",
                tags={"scenario": scenario.id, "stage": str(stage.stage)}
            )

            sleep_time = 2.0 if self.demo_mode else 5.0
            time.sleep(sleep_time)

    def _run_database_cascade_scenario(self):
        """
        Executes the exact 6-stage database_cascade causal progression.
        Emits precisely 29 distinct, causally ordered, realistic alerts.
        """
        base_time = datetime.now(timezone.utc)
        scenario = ALL_SCENARIOS["database_cascade"]

        def get_ts(offset_sec: float) -> str:
            return (base_time + timedelta(seconds=offset_sec)).isoformat()

        # STAGE 1: DB Query Degradation (T+0s)
        if self._stop_event.is_set(): return
        with self._mutex:
            self.status.current_stage = 1
            self.status.affected_services = ["postgresql"]

        telemetry_engine.update_metrics("postgresql", **scenario.stages[0].metrics_override)
        telemetry_engine.record_event(SystemEvent(
            service="postgresql",
            event_type="SCENARIO_STAGE_TRANSITION",
            description="Stage 1/6: DB Query Degradation - Query lock contention causing latency spike.",
            severity="WARNING",
            payload={"stage": 1, "service": "postgresql"}
        ))
        logger.warn("DATABASE_SLOW_QUERY", "Slow query execution detected on orders table (duration 450ms)", dependency="postgresql", latency_ms=450.0)
        logger.info("REQUEST_RECEIVED", "Incoming order transactions queued waiting for database lock", service="order-api")

        # Alerts 1 - 4
        emit_alert("postgresql", "WARNING", "DB_QUERY_SLOW", "query_duration_p95_ms", 450.0, 100.0, "Slow query execution detected on table 'orders' [SELECT FOR UPDATE lock contention]", timestamp=get_ts(0.1), tags={"table": "orders", "db": "shopflow"})
        emit_alert("postgresql", "WARNING", "DB_QUERY_SLOW", "query_duration_max_ms", 890.0, 250.0, "PostgreSQL query execution time exceeded SLA threshold (890ms on order_items scan)", timestamp=get_ts(0.3), tags={"table": "order_items", "db": "shopflow"})
        emit_alert("postgresql", "INFO", "HIGH_CPU", "db_cpu_pct", 68.5, 60.0, "PostgreSQL CPU utilization rising due to index scan lock wait overhead", timestamp=get_ts(0.5), tags={"host": "pg-primary-01"})
        emit_alert("postgresql", "WARNING", "DB_LOCK_CONTENTION", "waiting_locks_count", 14.0, 5.0, "Row-level lock contention detected on pg_catalog & orders table", timestamp=get_ts(0.8), tags={"lock_type": "RowExclusiveLock"})

        time.sleep(1.0 if self.demo_mode else 3.0)

        # STAGE 2: Connection Pool Exhaustion (T+2s)
        if self._stop_event.is_set(): return
        with self._mutex:
            self.status.current_stage = 2
            self.status.affected_services = ["postgresql"]

        telemetry_engine.update_metrics("postgresql", **scenario.stages[1].metrics_override)
        telemetry_engine.record_event(SystemEvent(
            service="postgresql",
            event_type="SCENARIO_STAGE_TRANSITION",
            description="Stage 2/6: Connection Pool Exhaustion - PostgreSQL connection pool 98% full.",
            severity="CRITICAL",
            payload={"stage": 2, "service": "postgresql"}
        ))
        logger.error("DATABASE_CONNECTION_PRESSURE", "PostgreSQL connection pool near saturation: 19/20 active connections", dependency="postgresql")
        logger.warn("CONNECTION_POOL_QUEUE", "Connection wait queue length reached 18 pending queries", dependency="postgresql")

        # Alerts 5 - 8
        emit_alert("postgresql", "WARNING", "DB_CONNECTION_EXHAUSTION", "connection_pool_active_pct", 85.0, 75.0, "PostgreSQL active connection pool utilization exceeded warning limit (17/20 active connections)", timestamp=get_ts(2.1), tags={"pool": "primary_readwrite"})
        emit_alert("postgresql", "CRITICAL", "DB_CONNECTION_EXHAUSTION", "connection_pool_active_pct", 98.0, 90.0, "PostgreSQL connection pool near saturation: 19/20 connections in use, 12 queries queued", timestamp=get_ts(2.4), tags={"pool": "primary_readwrite"})
        emit_alert("postgresql", "CRITICAL", "DB_CONNECTION_EXHAUSTION", "pool_wait_queue_depth", 18.0, 5.0, "PostgreSQL connection queue overflow: incoming client connection requests blocked", timestamp=get_ts(2.7), tags={"queue": "asyncpg_pool"})
        emit_alert("postgresql", "WARNING", "DB_TRANSACTION_AGE", "longest_xact_duration_sec", 14.5, 5.0, "Long-running open transaction detected in state 'idle in transaction'", timestamp=get_ts(3.0), tags={"pid": "8472"})

        time.sleep(1.0 if self.demo_mode else 3.0)

        # STAGE 3: Order API Slowdown & Timeout (T+4s)
        if self._stop_event.is_set(): return
        with self._mutex:
            self.status.current_stage = 3
            self.status.affected_services = ["postgresql", "order-api"]

        telemetry_engine.update_metrics("order-api", **scenario.stages[2].metrics_override)
        telemetry_engine.record_event(SystemEvent(
            service="order-api",
            event_type="SCENARIO_STAGE_TRANSITION",
            description="Stage 3/6: Order API Slowdown & Timeout - DB query timeouts and connection wait queue overflow.",
            severity="CRITICAL",
            payload={"stage": 3, "service": "order-api"}
        ))
        logger.error("DATABASE_TIMEOUT", "Order API database query timeout after 3000ms while executing INSERT INTO orders", dependency="postgresql", status_code=500, latency_ms=3000.0)
        logger.error("SERVICE_DEGRADED", "Order API entering degraded state: 48% of order creation requests failing", dependency="postgresql")

        # Alerts 9 - 13
        emit_alert("order-api", "WARNING", "DEPENDENCY_TIMEOUT", "pg_pool_acquire_latency_ms", 1850.0, 500.0, "Order API connection acquisition timeout when acquiring PostgreSQL connection lease", timestamp=get_ts(4.1), dependency="postgresql", tags={"endpoint": "/orders"})
        emit_alert("order-api", "WARNING", "HIGH_LATENCY", "order_create_latency_p95_ms", 2450.0, 400.0, "Order API POST /orders latency degraded due to postgresql query stall", timestamp=get_ts(4.3), dependency="postgresql", tags={"route": "POST /api/orders"})
        emit_alert("order-api", "CRITICAL", "HIGH_ERROR_RATE", "db_query_error_pct", 38.5, 5.0, "Order API database query failure rate spiking: connection timeout exceptions from asyncpg driver", timestamp=get_ts(4.6), dependency="postgresql", tags={"driver": "asyncpg"})
        emit_alert("order-api", "WARNING", "ACTIVE_WORKERS_SATURATION", "active_worker_threads_pct", 88.0, 75.0, "Order API worker thread pool near capacity waiting for I/O completion", timestamp=get_ts(4.9), tags={"workers": "uvicorn_workers"})
        emit_alert("order-api", "CRITICAL", "SERVICE_DEGRADED", "availability_pct", 62.0, 99.0, "Order API service state degraded: order persistence requests rejecting", timestamp=get_ts(5.2), dependency="postgresql", tags={"state": "degraded"})

        time.sleep(1.0 if self.demo_mode else 3.0)

        # STAGE 4: Checkout API Failures & Retry Storms (T+6s)
        if self._stop_event.is_set(): return
        with self._mutex:
            self.status.current_stage = 4
            self.status.affected_services = ["postgresql", "order-api", "checkout-api"]

        telemetry_engine.update_metrics("checkout-api", **scenario.stages[3].metrics_override)
        telemetry_engine.record_event(SystemEvent(
            service="checkout-api",
            event_type="SCENARIO_STAGE_TRANSITION",
            description="Stage 4/6: Checkout Orchestrator Failure - Transactions aborting due to downstream Order API failure.",
            severity="CRITICAL",
            payload={"stage": 4, "service": "checkout-api"}
        ))
        logger.error("DEPENDENCY_TIMEOUT", "Checkout API call to downstream order-api timed out after 4000ms", dependency="order-api", latency_ms=4000.0)
        logger.error("CHECKOUT_FAILED", "Customer checkout session failed: unable to persist order in order-api", dependency="order-api", status_code=503)
        logger.warn("RETRY_EXHAUSTED", "Checkout workflow exhausted max retries (3/3) to order-api", dependency="order-api")

        # Alerts 14 - 19
        emit_alert("checkout-api", "WARNING", "DEPENDENCY_TIMEOUT", "order_api_call_latency_ms", 3200.0, 800.0, "Checkout API upstream call to order-api timed out after 3000ms", timestamp=get_ts(6.1), dependency="order-api", tags={"target_service": "order-api"})
        emit_alert("checkout-api", "CRITICAL", "CHECKOUT_FAILURE", "checkout_failure_rate_pct", 78.0, 2.0, "Checkout transaction failure rate breached critical threshold (78% of checkouts failing)", timestamp=get_ts(6.4), dependency="order-api", tags={"funnel_step": "payment_settle"})
        emit_alert("checkout-api", "WARNING", "RETRY_EXHAUSTED", "checkout_retry_attempts", 3.0, 2.0, "Checkout workflow exhausted 3 retry attempts against downstream order-api", timestamp=get_ts(6.7), dependency="order-api", tags={"retries": "3"})
        emit_alert("checkout-api", "CRITICAL", "CIRCUIT_BREAKER_OPEN", "circuit_breaker_tripped", 1.0, 0.0, "Circuit breaker tripped to OPEN state for downstream dependency 'order-api'", timestamp=get_ts(7.0), dependency="order-api", tags={"breaker": "order_service_breaker"})
        emit_alert("checkout-api", "CRITICAL", "SERVICE_DOWN", "service_error_rate_pct", 92.0, 10.0, "Checkout API core checkout endpoint /api/checkout failing 92% of customer requests", timestamp=get_ts(7.3), dependency="order-api", tags={"endpoint": "/checkout"})
        emit_alert("checkout-api", "WARNING", "HIGH_MEMORY", "in_flight_sessions_count", 310.0, 100.0, "Checkout API pending session buffers accumulating due to unresolved transactions", timestamp=get_ts(7.6), tags={"component": "session_store"})

        time.sleep(1.0 if self.demo_mode else 3.0)

        # STAGE 5: API Gateway Degradation & Upstream 5xx Surge (T+8s)
        if self._stop_event.is_set(): return
        with self._mutex:
            self.status.current_stage = 5
            self.status.affected_services = ["postgresql", "order-api", "checkout-api", "api-gateway"]

        telemetry_engine.update_metrics("api-gateway", **scenario.stages[4].metrics_override)
        telemetry_engine.record_event(SystemEvent(
            service="api-gateway",
            event_type="SCENARIO_STAGE_TRANSITION",
            description="Stage 5/6: API Gateway 502/504 Spike - Upstream timeout surge on checkout and order routes.",
            severity="CRITICAL",
            payload={"stage": 5, "service": "api-gateway"}
        ))
        logger.error("UPSTREAM_504_GATEWAY_TIMEOUT", "API Gateway received HTTP 504 Gateway Timeout from checkout-api", dependency="checkout-api", status_code=504, latency_ms=5000.0)
        logger.warn("RATE_LIMIT_ENGAGED", "Adaptive rate limiting engaged on /api/orders to protect downstream dependencies")

        # Alerts 20 - 24
        emit_alert("api-gateway", "WARNING", "HIGH_LATENCY", "gateway_p99_latency_ms", 3800.0, 1000.0, "API Gateway aggregate p99 latency surged to 3800ms on route /api/checkout", timestamp=get_ts(8.1), dependency="checkout-api", tags={"route": "/api/checkout"})
        emit_alert("api-gateway", "CRITICAL", "UPSTREAM_5XX_SURGE", "gateway_5xx_error_pct", 58.0, 5.0, "API Gateway 504 Gateway Timeout surge from upstream checkout-api and order-api", timestamp=get_ts(8.4), dependency="checkout-api", tags={"status": "504"})
        emit_alert("api-gateway", "CRITICAL", "HIGH_ERROR_RATE", "route_error_rate_pct", 64.0, 5.0, "Route /api/checkout error rate reached 64% with 502/504 responses", timestamp=get_ts(8.7), dependency="checkout-api", tags={"route": "/api/checkout"})
        emit_alert("api-gateway", "WARNING", "RATE_LIMIT_ENGAGED", "throttled_requests_per_sec", 42.0, 10.0, "API Gateway adaptive rate limiting engaged for endpoint /api/orders to protect downstream services", timestamp=get_ts(9.0), tags={"rate_limiter": "token_bucket"})
        emit_alert("api-gateway", "WARNING", "SERVICE_DEGRADED", "healthy_backends_pct", 50.0, 90.0, "API Gateway health probes report 2 of 4 upstream services in degraded/failing state", timestamp=get_ts(9.3), tags={"healthy_ratio": "2/4"})

        time.sleep(1.0 if self.demo_mode else 3.0)

        # STAGE 6: Customer Degradation & Background Noise/Spillover (T+10s)
        if self._stop_event.is_set(): return
        with self._mutex:
            self.status.current_stage = 6
            self.status.affected_services = ["postgresql", "order-api", "checkout-api", "api-gateway", "shopflow-frontend"]
            self.status.recovery_status = "CRITICAL_OUTAGE"

        telemetry_engine.record_event(SystemEvent(
            service="shopflow-frontend",
            event_type="SCENARIO_STAGE_TRANSITION",
            description="Stage 6/6: Customer Checkout Degradation - User checkout unavailable. Graceful degradation active.",
            severity="CRITICAL",
            payload={"stage": 6, "customer_impact": "critical"}
        ))
        logger.error("CUSTOMER_CHECKOUT_DEGRADED", "Customer checkout blocked. Returning user-friendly degradation banner.", service="shopflow-frontend")
        logger.info("CACHE_FALLBACK", "Product API serving catalog responses directly from Redis cache", service="product-api")

        # Alerts 25 - 29 (Total 29 alerts)
        emit_alert("shopflow-frontend", "CRITICAL", "CUSTOMER_CHECKOUT_DEGRADED", "client_checkout_completion_pct", 12.0, 95.0, "Customer checkout completion dropped below 15%; fallback degradation banner activated", timestamp=get_ts(10.1), dependency="api-gateway", tags={"client": "web_spa"})
        emit_alert("api-gateway", "CRITICAL", "CUSTOMER_IMPACT_HIGH", "customer_facing_outage_severity", 3.0, 1.0, "Critical customer-facing outage: Users unable to complete purchases on ShopFlow", timestamp=get_ts(10.4), tags={"impact_tier": "P0"})
        emit_alert("product-api", "INFO", "DB_LATENCY_SPILLOVER", "product_db_query_latency_ms", 220.0, 150.0, "Product API experiencing slight latency bump from shared postgresql host contention", timestamp=get_ts(10.7), dependency="postgresql", tags={"host": "pg-primary-01"})
        emit_alert("redis", "INFO", "CACHE_QUERY_SPIKE", "redis_ops_per_sec", 410.0, 350.0, "Redis cache traffic increased as frontend falls back to cached catalog data", timestamp=get_ts(11.0), dependency="redis", tags={"cache_tier": "l2"})
        emit_alert("auth-service", "WARNING", "DB_TIMEOUT_WARNING", "auth_db_latency_ms", 380.0, 200.0, "Auth Service token verification encountering elevated PostgreSQL session query times", timestamp=get_ts(11.3), dependency="postgresql", tags={"endpoint": "/auth/verify"})

        with self._mutex:
            self.status.state = "COMPLETED"
            self.status.alert_count = len(telemetry_engine.alert_buffer)

    def reset(self) -> Dict[str, Any]:
        with self._mutex:
            self._stop_event.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=1.0)
            self._stop_event.clear()

            # Reset telemetry metrics & clear alerts
            telemetry_engine.reset()

            # Record Service Recovered logs & event
            telemetry_engine.record_event(SystemEvent(
                service="api-gateway",
                event_type="SYSTEM_RECOVERED",
                description="All services recovered to Operational state. Chaos injection cleared.",
                severity="INFO",
                payload={"status": "Operational"}
            ))

            for s in ["postgresql", "order-api", "checkout-api", "api-gateway", "product-api", "auth-service", "redis"]:
                logger.info(
                    "SERVICE_RECOVERED",
                    f"Service {s} recovered to normal operational parameters. Latency and error rates normalized.",
                    dependency=s
                )

            self.status = ChaosStatus(
                active_scenario=None,
                scenario_name=None,
                state="IDLE",
                started_at=None,
                elapsed_seconds=0,
                current_stage=0,
                total_stages=0,
                affected_services=[],
                alert_count=0,
                event_count=len(telemetry_engine.event_buffer),
                log_count=len(telemetry_engine.log_buffer),
                recovery_status="HEALTHY",
                demo_mode=self.demo_mode
            )
            return self.status.model_dump()

# Global chaos engine singleton
chaos_engine = ChaosEngine()
