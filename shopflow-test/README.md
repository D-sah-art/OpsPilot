# ShopFlow — Production-Like E-Commerce Test Subject

> **IMPORTANT**: ShopFlow is an external production-like test subject for the OpsPilot AIOps system.  
> It represents the monitored target system and provides realistic microservices behavior, rich telemetry, and safe chaos simulations. It intentionally does **not** contain incident correlation, root-cause analysis, or AI remediation logic (which belong exclusively to OpsPilot).

---

## 1. Architecture & Logical Topology

ShopFlow models an authentic local production e-commerce platform composed of 7 logical services and datastores:

```
Customer Browser
       │
ShopFlow Frontend (React + Vite + Tailwind)
       │
API Gateway (Port 8000)
 ├── Product API (Port 8001) ─── Redis (Cache / Port 6379)
 ├── Order API (Port 8002) ───── PostgreSQL (Port 5432)
 ├── Checkout API (Port 8003) ── Product API & Order API & PostgreSQL
 └── Auth Service (Port 8004) ── PostgreSQL
```

### Microservices Breakdown:
- **`api-gateway`**: Reverse proxy, request routing, authentication validation, health aggregation, and edge telemetry.
- **`product-api`**: Product catalog, category listings, keyword search, inventory levels, and Redis caching.
- **`order-api`**: Order persistence, state transitions (`CONFIRMED`, `SHIPPED`, `DELIVERED`), and history retrieval.
- **`checkout-api`**: Checkout orchestration, inventory validation, simulated payment processing, and audit trail.
- **`auth-service`**: JWT authentication, session verification, and seeded demo accounts (`alex@shopflow.dev`, `sarah@shopflow.dev`).
- **`postgresql`**: Primary relational datastore for orders, line items, and customer profiles.
- **`redis`**: In-memory caching tier for product queries and catalog acceleration.

---

## 2. Machine-Readable Topology (`GET /api/topology`)

Exposes a real machine-readable JSON representation of all nodes and dependency edges with protocol and criticality attributes:

```json
{
  "version": "1.0",
  "nodes": [
    { "id": "shopflow-frontend", "type": "frontend", "tier": "presentation", "criticality": "high" },
    { "id": "api-gateway", "type": "gateway", "tier": "edge", "port": 8000, "criticality": "critical" },
    { "id": "product-api", "type": "service", "tier": "core", "port": 8001, "criticality": "high" },
    { "id": "order-api", "type": "service", "tier": "core", "port": 8002, "criticality": "critical" },
    { "id": "checkout-api", "type": "service", "tier": "core", "port": 8003, "criticality": "critical" },
    { "id": "auth-service", "type": "service", "tier": "core", "port": 8004, "criticality": "high" },
    { "id": "postgresql", "type": "database", "tier": "data", "port": 5432, "criticality": "critical" },
    { "id": "redis", "type": "cache", "tier": "data", "port": 6379, "criticality": "medium" }
  ],
  "edges": [
    { "source": "api-gateway", "target": "product-api", "protocol": "HTTP/REST", "type": "sync" },
    { "source": "api-gateway", "target": "checkout-api", "protocol": "HTTP/REST", "type": "sync" },
    { "source": "checkout-api", "target": "order-api", "protocol": "HTTP/REST", "type": "sync" },
    { "source": "order-api", "target": "postgresql", "protocol": "TCP/SQL", "type": "sync" }
  ]
}
```

---

## 3. Quick Start & Setup

### Option A: Local Python & Node (Recommended for Fast Local Development)
```bash
# 1. Install dependencies
cd shopflow-test
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..

# 2. Start API Gateway & Services
# On Linux/macOS:
./start.sh
# On Windows (PowerShell):
.\start.ps1
```
Visit `http://localhost:8000` in your browser.

### Option B: Docker Compose
```bash
cd shopflow-test
docker compose up --build
```

---

## 4. API & Telemetry Contract

### Standard Service Endpoints:
- `GET /health` — Liveness health check
- `GET /ready` — Readiness check
- `GET /live` — Application status
- `GET /api/topology` — Real dependency graph
- `GET /api/health-summary` — Aggregated status across all services
- `GET /status` — Service telemetry overview

### Shopping Journey Endpoints:
- `GET /api/products` — Catalog listing (supports `?category=` and `?q=`)
- `GET /api/products/{id}` — Product detail & specifications
- `GET /api/categories` — Unique category tags
- `POST /api/cart` & `GET /api/cart/{session_id}` — Cart session management
- `POST /api/checkout` — Multi-item order placement & validation
- `GET /api/orders` & `GET /api/orders/{id}` — Order history & tracking
- `POST /api/auth/login` & `GET /api/auth/users` — Demo authentication

### Telemetry Hub:
- `GET /telemetry/metrics` — Live CPU, RAM, Latency (p50/p90/p99), error rates, DB pool, Redis hits/misses
- `GET /telemetry/logs` — Structured JSON logs with `service`, `level`, `event`, `latency_ms`, `status_code`
- `GET /telemetry/alerts` — Active alerts with `id`, `timestamp`, `severity`, `alert_type`, `metric`, `tags`
- `GET /telemetry/events` — System lifecycle and state transition events
- `GET /telemetry/services` — Live service health registry

---

## 5. Chaos Simulation Lab (`/chaos`)

ShopFlow provides a dedicated developer control plane at `/chaos` with non-destructive, safe in-memory fault injections.

### Primary Scenario: `database_cascade`
Simulates a realistic 6-stage database failure cascading upstream:
1. **Stage 1 (T+0s)**: PostgreSQL query latency degradation (`DB_QUERY_SLOW`, `DB_LOCK_CONTENTION`).
2. **Stage 2 (T+2s)**: PostgreSQL connection pool reaches 98% saturation (`DB_CONNECTION_EXHAUSTION`).
3. **Stage 3 (T+4s)**: Order API DB timeouts & connection queue overflows (`DEPENDENCY_TIMEOUT`, `HIGH_ERROR_RATE`).
4. **Stage 4 (T+6s)**: Checkout API downstream failure & retry storms (`CHECKOUT_FAILURE`, `CIRCUIT_BREAKER_OPEN`).
5. **Stage 5 (T+8s)**: API Gateway responds with HTTP 504 Gateway Timeout surge (`UPSTREAM_5XX_SURGE`).
6. **Stage 6 (T+10s)**: Customer checkout fails gracefully with user-friendly degradation banner while catalog browsing remains available.

> Produces **29 distinct, causally ordered, varied alerts** across services.

### Other Scenarios:
- `redis_failure`: Cache miss storm & DB fallback.
- `high_memory`: Memory leak simulation in checkout-api.
- `high_latency`: Inter-service network packet latency injection.
- `traffic_spike`: 10x surge in incoming visitor requests.
- `checkout_failure`: Isolated simulated payment gateway error.
- `unknown_issue`: Multi-service intermittent metric jitter.
- `POST /api/chaos/reset`: One-click restoration of all services to clean `Operational` baseline.

---

## 6. Running Automated Tests

Run the complete pytest test suite:
```bash
pytest tests/ -v
```

All 26 automated tests verify:
- Health and status endpoints
- Product catalog, search, and category filtering
- Authentication and demo users
- Cart and checkout workflows
- Topology schema and dependency edges
- Telemetry contracts (metrics, logs, alerts, events)
- Deterministic `database_cascade` causal ordering, ~28–30 alerts, customer degradation, and recovery
- Clean chaos reset
