import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import dateutil.parser

from app.models.alert import Alert
from app.topology.graph import DependencyGraph
from .models import PairwiseScore

logger = logging.getLogger("opspilot.correlation.scoring")

# =====================================================================
# Documented Deterministic Weights for Correlation Scoring
# Dependency and Causal Topology heavily outweigh pure Temporal Proximity
# =====================================================================
WEIGHT_DEPENDENCY = 0.25
WEIGHT_GRAPH_DISTANCE = 0.20
WEIGHT_CAUSAL_ORDER = 0.15
WEIGHT_TEMPORAL = 0.15
WEIGHT_SERVICE = 0.10
WEIGHT_ALERT_TYPE = 0.05
WEIGHT_SEVERITY = 0.05
WEIGHT_TAG_AND_METRIC = 0.05

assert abs(
    WEIGHT_DEPENDENCY
    + WEIGHT_GRAPH_DISTANCE
    + WEIGHT_CAUSAL_ORDER
    + WEIGHT_TEMPORAL
    + WEIGHT_SERVICE
    + WEIGHT_ALERT_TYPE
    + WEIGHT_SEVERITY
    + WEIGHT_TAG_AND_METRIC
    - 1.0
) < 1e-6, "Weights must sum exactly to 1.00"

def parse_iso_timestamp(ts: str) -> float:
    """Parses ISO timestamp string to Unix epoch seconds."""
    try:
        dt = dateutil.parser.isoparse(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return 0.0

def compute_temporal_score(delta_seconds: float) -> Tuple[float, str]:
    """
    Computes temporal proximity score with continuous decay.
    0 - 15s   -> 1.0 (immediate cluster)
    15 - 60s  -> [1.0 -> 0.7] (rapid cascade)
    60 - 180s -> [0.7 -> 0.3] (gradual cascade)
    180 - 600s-> [0.3 -> 0.0] (tail propagation)
    > 600s    -> 0.0
    """
    dt = abs(delta_seconds)
    if dt <= 15.0:
        return 1.0, f"Occurred within {round(dt, 1)}s (immediate)"
    elif dt <= 60.0:
        score = 1.0 - 0.3 * ((dt - 15.0) / 45.0)
        return round(score, 4), f"Occurred within {round(dt, 1)}s (rapid)"
    elif dt <= 180.0:
        score = 0.7 - 0.4 * ((dt - 60.0) / 120.0)
        return round(score, 4), f"Occurred within {round(dt, 1)}s (gradual)"
    elif dt <= 600.0:
        score = 0.3 - 0.3 * ((dt - 180.0) / 420.0)
        return round(score, 4), f"Occurred within {round(dt, 1)}s (tail)"
    else:
        return 0.0, f"Occurred {round(dt, 1)}s apart (outside correlation window)"

def compute_graph_distance_score(distance: Optional[int]) -> Tuple[float, str]:
    """Computes topological proximity score based on shortest path distance."""
    if distance is None:
        return 0.0, "No topological path between services (disconnected)"
    if distance == 0:
        return 1.0, "Same service (distance 0)"
    elif distance == 1:
        return 0.9, "Directly adjacent service (distance 1 hop)"
    elif distance == 2:
        return 0.7, "Downstream/upstream neighbor (distance 2 hops)"
    elif distance == 3:
        return 0.5, "Connected through 3 hops in topology"
    else:
        return 0.3, f"Distant topology connection ({distance} hops)"

def compute_dependency_score(
    service_a: str,
    service_b: str,
    graph: DependencyGraph
) -> Tuple[float, str]:
    """
    Evaluates topological dependency connection between services.
    Graph edges represent: caller -> dependency.
    """
    if service_a == service_b:
        return 1.0, "Same service"
    
    # Direct edge caller -> callee or callee -> caller
    if (graph.graph.has_edge(service_a, service_b) or 
        graph.graph.has_edge(service_b, service_a)):
        return 1.0, f"Direct dependency relationship between {service_a} and {service_b}"
    
    # Transitive directed path in graph
    if (graph.get_path(service_a, service_b) is not None):
        return 0.8, f"Transitive dependency chain between {service_a} and {service_b}"
    
    # Undirected path
    if graph.is_dependency_related(service_a, service_b):
        return 0.5, f"Shared component subsystem between {service_a} and {service_b}"
    
    return 0.0, f"No dependency relationship between {service_a} and {service_b}"

def compute_causal_order_score(
    alert_a: Alert,
    alert_b: Alert,
    graph: DependencyGraph,
    t_a: float,
    t_b: float
) -> Tuple[float, str]:
    """
    Evaluates if temporal order aligns with dependency failure propagation.
    In the dependency graph, edge is caller -> dependency (e.g. order-api -> postgresql).
    Upstream failure (postgresql) propagating to downstream caller (order-api) means
    the dependency alerts BEFORE or AT THE SAME TIME as the caller.
    """
    if alert_a.service == alert_b.service:
        return 1.0, "Same service temporal progression"

    # Identify which alert happened first
    if t_a <= t_b:
        first_alert, second_alert = alert_a, alert_b
    else:
        first_alert, second_alert = alert_b, alert_a

    s_first = first_alert.service
    s_second = second_alert.service

    # Is s_first an upstream dependency of s_second?
    # In graph: s_second -> ... -> s_first (s_second depends on s_first)
    upstreams_of_second = graph.get_upstream_services(s_second)
    if s_first in upstreams_of_second:
        return 1.0, f"Causal propagation: upstream dependency {s_first} degraded before caller {s_second}"

    # Did caller alert before dependency?
    downstreams_of_second = graph.get_downstream_services(s_second)
    if s_first in downstreams_of_second:
        return 0.6, f"Caller {s_first} alerted before downstream dependency {s_second}"

    if graph.is_dependency_related(s_first, s_second):
        return 0.5, f"Connected subsystem alerts in chronological sequence"

    return 0.0, "No causal dependency relationship"

def categorize_alert_family(alert_type: str, metric_name: str) -> str:
    """Generically categorizes alert into broad telemetry error/latency/resource families."""
    name_combined = f"{alert_type} {metric_name}".lower()
    if any(k in name_combined for k in ["latency", "slow", "delay", "time", "duration", "lag"]):
        return "latency"
    elif any(k in name_combined for k in ["error", "fail", "50", "timeout", "exception", "broken"]):
        return "error_rate"
    elif any(k in name_combined for k in ["conn", "pool", "exhaust", "saturation", "cpu", "mem", "queue", "capacity"]):
        return "resource_saturation"
    elif any(k in name_combined for k in ["circuit", "rate_limit", "degrade", "block"]):
        return "resilience"
    return "general"

def compute_alert_type_score(alert_a: Alert, alert_b: Alert) -> Tuple[float, str]:
    """Computes generic alert similarity without scenario-specific hardcoding."""
    if alert_a.alert_type == alert_b.alert_type:
        return 1.0, f"Identical alert type ({alert_a.alert_type})"
    
    fam_a = categorize_alert_family(alert_a.alert_type, alert_a.metric)
    fam_b = categorize_alert_family(alert_b.alert_type, alert_b.metric)
    
    if fam_a == fam_b and fam_a != "general":
        return 0.8, f"Related telemetry category: {fam_a}"
    
    # Generic telemetry correlation
    return 0.5, "Standard telemetry alert signals"

def compute_severity_score(sev_a: str, sev_b: str) -> Tuple[float, str]:
    """Computes alignment of alert severity levels."""
    sa = (sev_a or "").upper()
    sb = (sev_b or "").upper()
    if sa == "CRITICAL" and sb == "CRITICAL":
        return 1.0, "Dual CRITICAL severity alert alignment"
    elif ("CRITICAL" in (sa, sb)) and ("WARNING" in (sa, sb)):
        return 0.8, "CRITICAL and WARNING alert cascade alignment"
    elif sa == "WARNING" and sb == "WARNING":
        return 0.7, "Dual WARNING alert alignment"
    else:
        return 0.5, f"Severity levels: {sa} / {sb}"

def compute_tag_and_metric_score(alert_a: Alert, alert_b: Alert) -> Tuple[float, str]:
    """Checks explicit dependency references or shared metadata tags."""
    # Check if alert_b explicitly references alert_a's service as dependency or vice-versa
    dep_a = alert_a.dependency or alert_a.tags.get("dependency")
    dep_b = alert_b.dependency or alert_b.tags.get("dependency")

    if dep_a == alert_b.service or dep_b == alert_a.service:
        return 1.0, f"Explicit dependency reference in telemetry payload ({dep_a or dep_b})"

    # Check shared tags
    tags_a = set(alert_a.tags.keys())
    tags_b = set(alert_b.tags.keys())
    if tags_a and tags_b and (tags_a & tags_b):
        return 0.8, f"Shared metadata tags: {list(tags_a & tags_b)}"

    return 0.5, "Standard telemetry metadata"

def calculate_pairwise_score(
    alert_a: Alert,
    alert_b: Alert,
    graph: DependencyGraph
) -> PairwiseScore:
    """
    Computes a fully deterministic, inspectable correlation score between two alerts.
    """
    t_a = parse_iso_timestamp(alert_a.timestamp)
    t_b = parse_iso_timestamp(alert_b.timestamp)
    delta_t = abs(t_a - t_b)

    # 1. Temporal Score
    s_temporal, r_temporal = compute_temporal_score(delta_t)

    # 2. Service Score
    s_service = 1.0 if alert_a.service == alert_b.service else 0.0
    r_service = f"Same service ({alert_a.service})" if s_service == 1.0 else f"Different services ({alert_a.service} vs {alert_b.service})"

    # 3. Dependency Score
    s_dep, r_dep = compute_dependency_score(alert_a.service, alert_b.service, graph)

    # 4. Graph Distance Score
    dist = graph.dependency_distance(alert_a.service, alert_b.service)
    s_dist, r_dist = compute_graph_distance_score(dist)

    # 5. Causal Order Score
    s_causal, r_causal = compute_causal_order_score(alert_a, alert_b, graph, t_a, t_b)

    # 6. Alert Type Score
    s_type, r_type = compute_alert_type_score(alert_a, alert_b)

    # 7. Severity Score
    s_sev, r_sev = compute_severity_score(alert_a.severity, alert_b.severity)

    # 8. Tag and Metric Score
    s_tag, r_tag = compute_tag_and_metric_score(alert_a, alert_b)

    # Weighted Total Score
    total = (
        WEIGHT_DEPENDENCY * s_dep
        + WEIGHT_GRAPH_DISTANCE * s_dist
        + WEIGHT_CAUSAL_ORDER * s_causal
        + WEIGHT_TEMPORAL * s_temporal
        + WEIGHT_SERVICE * s_service
        + WEIGHT_ALERT_TYPE * s_type
        + WEIGHT_SEVERITY * s_sev
        + WEIGHT_TAG_AND_METRIC * s_tag
    )
    total = max(0.0, min(1.0, round(total, 4)))

    reasons = [r_dep, r_dist, r_causal, r_temporal]
    if s_service == 1.0:
        reasons.append(r_service)
    if s_tag == 1.0:
        reasons.append(r_tag)

    return PairwiseScore(
        alert_a_id=alert_a.id,
        alert_b_id=alert_b.id,
        service_a=alert_a.service,
        service_b=alert_b.service,
        total_score=total,
        dependency_score=s_dep,
        graph_distance_score=s_dist,
        causal_order_score=s_causal,
        temporal_score=s_temporal,
        service_score=s_service,
        alert_type_score=s_type,
        severity_score=s_sev,
        tag_and_metric_score=s_tag,
        reasons=reasons
    )
