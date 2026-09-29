import json
from typing import Dict, Any, List

SYSTEM_PROMPT = """You are an expert AIOps and Site Reliability Engineering (SRE) diagnostic intelligence agent.
Your task is to analyze a correlated operational incident and determine its true root cause with structured evidence.

CRITICAL GROUNDING RULES:
1. Base your diagnosis STRICTLY and EXCLUSIVELY on the provided correlation evidence, causal chain, topology, and metrics.
2. Do NOT invent, hallucinate, or assume any external services, nodes, infrastructure components, or metrics not present in the evidence.
3. The 'root_cause_service' MUST be one of the services listed in the incident's 'affected_services'.
4. 'recommended_action' MUST be purely informational and analytical advice for human engineers. DO NOT provide executable bash/shell scripts, CLI commands (e.g. systemctl, docker, kubectl, rm, kill), or automated scripts.
5. Provide an evidence-derived confidence score between 0.0 and 1.0 reflecting how clearly the telemetry supports the conclusion.
6. You must output ONLY a valid JSON object matching the requested schema without markdown code fences or conversational text.
"""

def build_diagnosis_prompt(incident_data: Dict[str, Any], hindsight_context: str = "") -> str:
    """
    Constructs an evidence-rich, strictly grounded prompt for the LLM,
    including historical Hindsight memory context when available.
    """
    evidence = incident_data.get("correlation_evidence") or {}
    if hasattr(evidence, "model_dump"):
        evidence = evidence.model_dump()

    incident_id = incident_data.get("incident_id", "unknown")
    title = incident_data.get("title", "Correlated Incident")
    severity = incident_data.get("severity", "CRITICAL")
    affected_services = incident_data.get("affected_services", [])
    alert_count = incident_data.get("alert_count", 0)
    correlation_score = incident_data.get("correlation_score", 1.0)
    started_at = incident_data.get("created_at") or incident_data.get("started_at", "")

    temporal_span = evidence.get("temporal_span_seconds", 0.0)
    earliest_alert = evidence.get("earliest_alert", {})
    latest_alert = evidence.get("latest_alert", {})
    causal_chain = evidence.get("causal_chain", [])
    dependency_paths = evidence.get("dependency_paths", [])
    top_pairwise = evidence.get("top_pairwise_correlations", [])

    prompt_lines = []
    
    if hindsight_context:
        prompt_lines.append(hindsight_context)
        prompt_lines.append("")

    prompt_lines.extend([
        f"INCIDENT SUMMARY:",
        f"- Incident ID: {incident_id}",
        f"- Title: {title}",
        f"- Severity: {severity}",
        f"- Started At: {started_at}",
        f"- Total Correlated Alerts: {alert_count}",
        f"- Correlation Cohesion Score: {correlation_score}",
        f"- Affected Services: {json.dumps(affected_services)}",
        f"- Temporal Span: {temporal_span:.2f} seconds",
        "",
        "EARLIEST ALERT (Initial Trigger Signal):",
        json.dumps(earliest_alert, indent=2) if earliest_alert else "None recorded",
        "",
        "CHRONOLOGICAL CAUSAL CHAIN:",
        json.dumps(causal_chain[:10], indent=2) if causal_chain else "None recorded",
        "",
        "TOPOLOGICAL DEPENDENCY PATHS:",
        json.dumps(dependency_paths, indent=2) if dependency_paths else "None recorded",
        "",
        "TOP PAIRWISE CORRELATIONS & REASONS:",
        json.dumps(top_pairwise[:5], indent=2) if top_pairwise else "None recorded",
        "",
        "REQUIRED JSON OUTPUT FORMAT:",
        json.dumps({
            "root_cause_service": "<exact service name from affected_services>",
            "root_cause_summary": "<concise 1-2 sentence explanation of the underlying failure>",
            "causal_narrative": "<clear step-by-step narrative describing the propagation from root to callers>",
            "propagation_path": ["<root_service>", "<intermediate_service>", "..."],
            "evidence_summary": [
                "<bullet 1 highlighting initial alert and metric>",
                "<bullet 2 highlighting dependency cascade>",
                "<bullet 3 highlighting correlation cohesion>"
            ],
            "recommended_action": "<informational recommendation for operators without shell commands>",
            "confidence_score": 0.95
        }, indent=2),
        "",
        "Return ONLY the raw JSON object."
    ])

    return "\n".join(prompt_lines)

