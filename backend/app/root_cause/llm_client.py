import json
import re
import logging
from typing import Dict, Any, Optional
import httpx

from app.config import settings
from .prompt_builder import SYSTEM_PROMPT, build_diagnosis_prompt

logger = logging.getLogger("opspilot.root_cause.llm_client")

# Safety checks: Prevent any executable code/commands in recommended actions
BANNED_COMMAND_PATTERNS = [
    r"\b(sudo|systemctl|service|docker|kubectl|helm|bash|sh|zsh|kill|pkill|rm\s+-rf|chmod|chown)\b",
    r"(\$\(.*\)|`.*`|\|.*bash|;\s*rm\s+)"
]

class LLMClient:
    """
    OpenAI-compatible LLM client for Phase 4 Root-Cause Diagnosis.
    Supports OpenAI, Azure OpenAI, LocalAI, vLLM, Ollama, and mock test servers.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        temperature: Optional[float] = None
    ):
        self.api_key = api_key if api_key is not None else settings.llm_api_key
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.model = model or settings.llm_model
        self.timeout_seconds = timeout_seconds or settings.llm_timeout_seconds
        self.temperature = temperature if temperature is not None else settings.llm_temperature

    def is_configured(self) -> bool:
        """Returns True if an API key or local endpoint is configured."""
        return bool(self.api_key or "localhost" in self.base_url or "127.0.0.1" in self.base_url)

    def diagnose_incident(self, incident_data: Dict[str, Any], hindsight_context: str = "") -> Optional[Dict[str, Any]]:
        """
        Calls the LLM chat completions endpoint, extracts JSON response,
        validates grounding against incident data, and screens for dangerous commands.
        Returns None if call fails or output is invalid.
        """
        if not self.is_configured():
            logger.debug("LLM is not configured (no API key or local URL); using fallback")
            return None

        prompt = build_diagnosis_prompt(incident_data, hindsight_context=hindsight_context)

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "response_format": {"type": "json_object"}
        }

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(endpoint, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

            content = data["choices"][0]["message"]["content"]
            parsed_json = self._extract_json(content)
            
            # Validate output grounding & safety
            if self._validate_llm_response(parsed_json, incident_data):
                return parsed_json
            else:
                logger.warning("LLM response failed grounding or safety validation")
                return None

        except httpx.TimeoutException:
            logger.warning(f"LLM request timed out after {self.timeout_seconds}s")
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(f"LLM API returned HTTP {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            logger.warning(f"LLM diagnosis failed: {e}")
            return None

    def _extract_json(self, content: str) -> Dict[str, Any]:
        """Extracts JSON dict from raw LLM string, handling markdown fences."""
        cleaned = content.strip()
        if cleaned.startswith("```"):
            # Strip ```json and ```
            lines = cleaned.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        return json.loads(cleaned)

    def _validate_llm_response(self, response_dict: Dict[str, Any], incident_data: Dict[str, Any]) -> bool:
        """
        Strictly validates that:
        1. Required schema keys exist.
        2. root_cause_service is one of the affected_services.
        3. recommended_action contains no banned shell/CLI commands.
        4. confidence_score is a valid float in [0.0, 1.0].
        """
        required_keys = [
            "root_cause_service",
            "root_cause_summary",
            "causal_narrative",
            "propagation_path",
            "evidence_summary",
            "recommended_action"
        ]
        for key in required_keys:
            if key not in response_dict or not response_dict[key]:
                logger.warning(f"Validation failed: missing or empty key '{key}'")
                return False

        # Grounding check: root_cause_service must be in affected_services
        affected_services = set(incident_data.get("affected_services", []))
        root_svc = response_dict["root_cause_service"]
        if affected_services and root_svc not in affected_services:
            logger.warning(f"Validation failed: root_cause_service '{root_svc}' not in affected_services {affected_services}")
            return False

        # Safety check: recommended_action must not contain executable commands
        action_text = response_dict.get("recommended_action", "")
        for pattern in BANNED_COMMAND_PATTERNS:
            if re.search(pattern, action_text, re.IGNORECASE):
                logger.warning(f"Validation failed: executable command detected in recommended_action: '{action_text}'")
                return False

        return True
