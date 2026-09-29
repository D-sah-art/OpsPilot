# OpsPilot Backend (Phase 2 Foundation, Phase 3 Correlation, Phase 4 AI Root-Cause Diagnosis & Phase 5 Safety-Gated Remediation)

OpsPilot is an autonomous AIOps self-healing system designed to ingest telemetry from external microservices, correlate alert storms into unified incidents, isolate root causes with explainable AI reasoning and deterministic fallback, execute safety-gated remediations, verify recovery against observable telemetry signals, and maintain an immutable audit trail.

---

## 🏗️ Architecture & Modules

```
backend/
├── app/
│   ├── main.py                  # FastAPI Application Entrypoint & Lifecycle
│   ├── config.py                # Settings (ShopFlow URL, SQLite DB, LLM keys, Remediation Flags)
│   ├── models/                  # Pydantic Telemetry Data Contracts
│   │   ├── alert.py             # Strongly typed Alert (raw_payload preserved)
│   │   ├── metric.py            # Point-in-time Metric Snapshot
│   │   ├── log_event.py         # Structured Application Log Event
│   │   ├── system_event.py      # Lifecycle & Deployment System Event
│   │   ├── service.py           # Topology Node (Service)
│   │   └── dependency.py        # Directed Dependency Edge
│   ├── database/                # Persistent SQLite Storage Layer
│   │   ├── session.py           # SQLAlchemy Engine, SessionLocal & Lifespan Hooks
│   │   ├── models.py            # SQLAlchemy ORM Tables (Incidents, Alerts, RemediationAuditModel)
│   │   └── repository.py        # Deduplicating Repository with Append-Only Audit Logging
│   ├── topology/                # In-Memory NetworkX Topology Graph
│   │   └── graph.py             # DependencyGraph with Traversal, Upstream/Downstream & Paths
│   ├── ingestion/               # Decoupled Telemetry Ingestion Layer
│   │   ├── adapter.py           # Resilient ShopFlow HTTP Adapter
│   │   ├── normalizer.py        # Telemetry payload normalizer
│   │   └── service.py           # Ingestion orchestrator & synchronizer
│   ├── correlation/             # Phase 3 Dependency-Aware Correlation Engine
│   │   ├── models.py            # Incident, CorrelationEvidence, PairwiseScore, BenchmarkResult
│   │   ├── scoring.py           # Deterministic pairwise scoring with documented component weights
│   │   ├── clustering.py        # Deterministic connected components alert clustering
│   │   ├── evidence.py          # Inspectable evidence builder (temporal span, paths, causal chain)
│   │   ├── strategies/          # Correlation Strategies (dependency_aware, time_only)
│   │   └── service.py           # CorrelationService orchestrator & benchmark runner
│   ├── root_cause/              # Phase 4 AI-Assisted Root-Cause Diagnosis
│   │   ├── models.py            # RootCauseAnalysis, ConfidenceBreakdown, RootCauseRequest
│   │   ├── fallback.py          # Generic topology & causal deterministic fallback analyzer
│   │   ├── prompt_builder.py    # Strict evidence-grounded LLM prompt constructor
│   │   ├── llm_client.py        # OpenAI-compatible client with JSON schema validation & command filtering
│   │   ├── analyzer.py          # RootCauseAnalyzer coordinating LLM and fallback
│   │   └── service.py           # RootCauseService orchestrating diagnosis & SQLite caching
│   ├── remediation/             # Phase 5 Safety-Gated Remediation & Audit
│   │   ├── models.py            # RemediationRequest, SafetyGateResult, RemediationResult, Audit
│   │   ├── allowlist.py         # Deterministic YAML Allow-List Parser & Validator
│   │   ├── safety_gate.py       # 10-Condition Deterministic Safety Gate
│   │   ├── executor.py          # Restricted Typed Handlers (restart_service, reset_connections)
│   │   ├── recovery.py          # Real Telemetry Signal Recovery Verifier
│   │   └── service.py           # Remediation Orchestration & Immutable Audit Logger
│   └── api/                     # REST API Endpoints
│       ├── routes/health.py     # Independent OpsPilot health + ShopFlow connectivity
│       ├── routes/services.py   # Ingested service catalog
│       ├── routes/topology.py   # Topology graph nodes, edges & path queries
│       ├── routes/alerts.py     # Ingested raw alerts & statistics
│       ├── routes/metrics.py    # Metric time-series & snapshots
│       ├── routes/logs.py       # Log streams & query filters
│       ├── routes/events.py     # System event timeline
│       ├── routes/sync.py       # Trigger external ShopFlow sync
│       ├── routes/correlation.py# Trigger correlation & run comparative benchmarks
│       └── routes/incidents.py  # Incident management, Root Cause, Remediation & Audit endpoints
├── config/
│   └── remediation_allowlist.yaml # Declarative allow-list policy
└── tests/                       # Automated Test Suite (57 backend tests)
```

---

## 🛡️ Phase 5: Safety-Gated Remediation & Safety Principles

1. **Strict Safety Boundary**: Remediation **NEVER** executes arbitrary shell commands, `subprocess`, or `eval`/`exec`. Every action is mapped to an explicit typed handler.
2. **Deterministic Allow-List (`config/remediation_allowlist.yaml`)**:
   - `restart_service`: Permitted **only** on stateless services (`api-gateway`, `checkout-api`, `order-api`, `product-api`, `auth-service`). Stateful databases (`postgresql`, `redis`) are strictly prohibited from automated restarts.
   - `reset_connections`: Permitted on connection-pooling targets (`postgresql`, `checkout-api`, `order-api`, `product-api`).
3. **10-Condition Deterministic Safety Gate**:
   - Condition 1: Incident exists in database
   - Condition 2: Action present in YAML allow-list
   - Condition 3: Target service permitted for specified action
   - Condition 4: Target service in incident affected services / topology
   - Condition 5: Valid root-cause diagnosis present
   - Condition 6: Diagnosis confidence meets threshold ($\ge 0.65$)
   - Condition 7: Incident in actionable state (`OPEN`)
   - Condition 8: Parameters conform to schema (e.g. `grace_period_seconds` $\le 60$)
   - Condition 9: Remediation enabled globally
   - Condition 10: Human review required for high-risk / manual targets
4. **Default Simulation Mode (`SIMULATION`)**:
   - Zero host, process, or container mutations.
   - Accurately computes realistic simulation outcomes, logs execution events, and invokes the recovery verifier against real ShopFlow telemetry.
5. **Recovery Verification Layer**:
   - Evaluates 4 distinct observable telemetry signals:
     1. ShopFlow target connectivity & `/health` endpoint
     2. Active critical alert frequencies for target service
     3. Service telemetry metrics (error rate & latency)
     4. Upstream dependency call-chain health
   - Output states: `RECOVERED`, `NOT_RECOVERED`, or `UNKNOWN`.
6. **Immutable Append-Only Audit Trail**:
   - Every remediation attempt (approved, rejected, simulated, or executed) is recorded permanently in the SQLite `remediation_audits` table with actor, condition evaluations, policy snapshots, and timestamps.

---

## 🧠 Phase 4: Evidence-Derived Confidence Scoring

Confidence is computed objectively from telemetry evidence and strictly bounded to $[0.0, 1.0]$:

$$\text{Confidence} = 0.30 \times C_{\text{topo}} + 0.25 \times C_{\text{causal}} + 0.20 \times C_{\text{evidence}} + 0.15 \times C_{\text{symptoms}} + 0.10 \times C_{\text{cohesion}}$$

| Component | Weight | Metric Evaluated |
| :--- | :--- | :--- |
| **`topological_clarity`** | 0.30 | Unambiguous directed path in dependency graph to root service |
| **`causal_consistency`** | 0.25 | Initial trigger alert aligned chronologically with root candidate |
| **`evidence_completeness`** | 0.20 | Availability of causal chain, dependency paths, and pairwise scores |
| **`symptom_breadth`** | 0.15 | Multi-tier cascade propagation across dependent service tiers |
| **`correlation_cohesion`** | 0.10 | Phase 3 incident cohesion score |

---

## 📡 REST API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/health` | `GET` | OpsPilot operational health & ShopFlow target reachability |
| `/api/sync/shopflow` | `POST` | Trigger synchronous ingestion & deduplication pass |
| `/api/services` | `GET` | List all discovered services in the topology |
| `/api/topology` | `GET` | Get complete NetworkX dependency graph nodes & edges |
| `/api/topology/path` | `GET` | Find directed dependency path between two services (`?source=...&target=...`) |
| `/api/alerts` | `GET` | List ingested alerts (`?severity=...&service=...&alert_type=...`) |
| `/api/metrics` | `GET` | Retrieve recorded service metric time-series |
| `/api/logs` | `GET` | Query structured log events (`?service=...&level=...&search=...`) |
| `/api/events` | `GET` | Retrieve system lifecycle & deployment events |
| `/api/correlation` | `POST` | Run correlation on ingested alerts (`?strategy=dependency_aware\|time_only`) |
| `/api/correlation/benchmark` | `GET` | Run comparative benchmark comparing time-only vs dependency-aware strategies |
| `/api/incidents` | `GET` | List correlated incidents (`?status=...&severity=...`) |
| `/api/incidents/{incident_id}` | `GET` | Retrieve incident details, evidence, and cached diagnosis |
| `/api/incidents/{incident_id}/root-cause` | `POST` | Diagnose root cause with AI/fallback (`{"force_refresh": false, "force_fallback": false}`) |
| `/api/incidents/{incident_id}/root-cause` | `GET` | Get cached diagnosis or compute if missing |
| `/api/incidents/{incident_id}/remediate` | `POST` | Execute safety-gated remediation (`{"action": "restart_service", "target_service": "order-api", "mode": "SIMULATION"}`) |
| `/api/incidents/{incident_id}/remediation` | `GET` | Get latest remediation decision and execution result |
| `/api/incidents/{incident_id}/remediate/verify` | `POST` | Trigger real-time recovery verification against telemetry signals |
| `/api/incidents/{incident_id}/audit` | `GET` | Get complete immutable audit trail for incident |
| `/api/incidents` | `DELETE` | Clear all stored incidents |

---

## 🧪 Testing & Validation

Run the complete test suite:
```bash
# Backend suite (57 tests)
python -m pytest backend/tests -v

# ShopFlow testbed suite (26 tests)
python -m pytest shopflow-test/tests -v

# Total: 83 tests passing
```
