import json
import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx

from app.config import settings
from .models import HindsightMemoryItem, HindsightRecallResult

logger = logging.getLogger("opspilot.memory.hindsight")

class HindsightClient:
    """
    Official Hindsight (by Vectorize) Client Abstraction.
    Supports both official `hindsight-client` Python SDK and direct HTTP REST API calls.
    Features robust connection status verification and distinguishable fallback tracking.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        bank_id: Optional[str] = None,
        enabled: Optional[bool] = None,
    ):
        self.base_url = (base_url or settings.hindsight_base_url).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.hindsight_api_key
        self.bank_id = bank_id or settings.hindsight_bank_id
        self.enabled = enabled if enabled is not None else settings.hindsight_enabled
        self.timeout = settings.hindsight_timeout_seconds

        self._sdk_client = None
        self._local_storage_path = os.path.join(os.getcwd(), "hindsight_memory_bank.json")

        self._init_sdk()

    def _init_sdk(self):
        """Initializes official hindsight-client SDK if available."""
        if not self.enabled:
            return
        try:
            from hindsight_client import Hindsight
            kwargs = {"base_url": self.base_url}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            self._sdk_client = Hindsight(**kwargs)
            logger.info(f"[HINDSIGHT] Initialized official Hindsight SDK targeting {self.base_url} (Bank: {self.bank_id})")
        except Exception as e:
            logger.warning(f"[HINDSIGHT] SDK initialization notice (using REST/Fallback): {e}")

    def check_connection(self) -> Dict[str, Any]:

        """
        Verifies live HTTP / API connection to the Hindsight server.
        """
        if not self.enabled:
            return {
                "connected": False,
                "status": "DISABLED",
                "message": "Hindsight memory system is disabled in config"
            }

        # 1. Try SDK version call
        if self._sdk_client:
            try:
                version_info = self._sdk_client.get_version()
                return {
                    "connected": True,
                    "status": "CONNECTED_TO_HINDSIGHT",
                    "mode": "SDK (hindsight-client 0.10.1)",
                    "base_url": self.base_url,
                    "api_version": str(version_info)
                }
            except Exception as e:
                logger.debug(f"[HINDSIGHT] SDK check_connection failed: {e}")

        # 2. Try REST health check
        health_urls = [
            f"{self.base_url}/health/ready",
            f"{self.base_url}/health/live",
            f"{self.base_url}/v1/default/banks/{self.bank_id}/profile"
        ]

        for url in health_urls:
            try:
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(url, headers=headers)
                    if resp.status_code == 200:
                        return {
                            "connected": True,
                            "status": "CONNECTED_TO_HINDSIGHT",
                            "mode": "REST API",
                            "base_url": self.base_url,
                            "details": resp.json()
                        }
            except Exception as e:
                logger.debug(f"[HINDSIGHT] REST health check failed for {url}: {e}")

        return {
            "connected": False,
            "status": "HINDSIGHT_UNAVAILABLE",
            "mode": "LOCAL_FALLBACK",
            "base_url": self.base_url,
            "message": "Hindsight server unavailable — local fallback active"
        }

    def retain_incident(
        self,
        incident_id: str,
        title: str,
        content: str,
        affected_services: List[str],
        root_cause_service: Optional[str] = None,
        remediation_action: Optional[str] = None,
        recovery_verified: bool = False,
        tags: Optional[List[str]] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
        target_bank_id: Optional[str] = None,
    ) -> bool:
        """
        Retains an operational incident memory into Hindsight.
        """
        if not self.enabled:
            logger.debug("[HINDSIGHT] Retention skipped (Hindsight disabled)")
            return False

        bank = target_bank_id or self.bank_id
        memory_id = f"mem_{incident_id}_{int(datetime.now(timezone.utc).timestamp())}"
        timestamp_str = datetime.now(timezone.utc).isoformat()
        memory_tags = tags or ["opspilot", "incident_resolution"]
        if root_cause_service:
            memory_tags.append(f"service:{root_cause_service}")

        metadata = {
            "incident_id": incident_id,
            "title": title,
            "affected_services": json.dumps(affected_services),
            "root_cause_service": root_cause_service or "unknown",
            "remediation_action": remediation_action or "none",
            "recovery_verified": str(recovery_verified).lower(),
            "retained_at": timestamp_str,
            **(extra_metadata or {})
        }

        memory_item = HindsightMemoryItem(
            id=memory_id,
            incident_id=incident_id,
            title=title,
            content=content,
            affected_services=affected_services,
            root_cause_service=root_cause_service,
            remediation_action=remediation_action,
            recovery_verified=recovery_verified,
            tags=memory_tags,
            timestamp=timestamp_str,
        )

        retained_remote = False

        # 1. Try SDK retain
        if self._sdk_client:
            try:
                self._sdk_client.retain(
                    bank_id=bank,
                    content=content,
                    context=f"Incident {incident_id} resolution context",
                    metadata=metadata,
                    tags=memory_tags,
                )
                logger.info(f"[HINDSIGHT] Retained incident memory '{memory_id}' via SDK into bank '{bank}'")
                retained_remote = True
            except Exception as e:
                logger.warning(f"[HINDSIGHT] Remote SDK retain call failed: {e}")

        # 2. Try REST API retain if SDK wasn't used or failed
        if not retained_remote:
            try:
                endpoint = f"{self.base_url}/v1/default/banks/{bank}/retain"
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                payload = {
                    "content": content,
                    "context": f"Incident {incident_id} resolution context",
                    "metadata": metadata,
                    "tags": memory_tags
                }
                
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(endpoint, json=payload, headers=headers)
                    if resp.status_code in (200, 201, 202):
                        logger.info(f"[HINDSIGHT] Retained incident memory '{memory_id}' via REST API into bank '{bank}'")
                        retained_remote = True
            except Exception as e:
                logger.warning(f"[HINDSIGHT] REST retain endpoint offline/unreachable: {e}")

        # Update local backup storage
        self._save_to_local_bank(memory_item)

        return True

    def recall_memories(
        self,
        query: str,
        affected_services: List[str],
        top_k: int = 3,
        target_bank_id: Optional[str] = None
    ) -> HindsightRecallResult:
        """
        Recalls historical operational incident memories matching the query.
        Explicitly tracks connection status and memory source.
        """
        if not self.enabled:
            return HindsightRecallResult(
                enabled=False,
                connection_status="DISABLED",
                memory_source="None",
                status="DISABLED",
                bank_id=self.bank_id,
                memories_recalled=0,
                memories=[],
                formatted_context="",
            )

        bank = target_bank_id or self.bank_id
        conn_check = self.check_connection()
        is_connected = conn_check.get("connected", False)

        logger.info(f"[HINDSIGHT] Recall started for query: '{query[:80]}...' (Bank: '{bank}', Server Status: {conn_check.get('status')})")

        recalled_items: List[HindsightMemoryItem] = []
        remote_success = False

        # 1. Try SDK recall
        if is_connected and self._sdk_client:
            try:
                response = self._sdk_client.recall(
                    bank_id=bank,
                    query=query,
                )
                if hasattr(response, "results") and response.results:
                    for idx, res in enumerate(response.results[:top_k]):
                        text = getattr(res, "text", getattr(res, "content", str(res)))
                        meta = getattr(res, "metadata", {}) or {}
                        item = HindsightMemoryItem(
                            id=meta.get("id", f"remote_{idx}"),
                            incident_id=meta.get("incident_id", "historical"),
                            title=meta.get("title", f"Historical Incident {idx+1}"),
                            content=text,
                            affected_services=json.loads(meta.get("affected_services", "[]")) if isinstance(meta.get("affected_services"), str) else (meta.get("affected_services") or affected_services),
                            root_cause_service=meta.get("root_cause_service"),
                            remediation_action=meta.get("remediation_action"),
                            recovery_verified=str(meta.get("recovery_verified")).lower() == "true",
                            tags=getattr(res, "tags", ["hindsight"]),
                            timestamp=meta.get("retained_at", datetime.now(timezone.utc).isoformat()),
                        )
                        recalled_items.append(item)
                    remote_success = True
                    logger.info(f"[HINDSIGHT] Recalled {len(recalled_items)} memories via SDK from bank '{bank}'")
            except Exception as e:
                logger.warning(f"[HINDSIGHT] Remote SDK recall call failed: {e}")

        # 2. Try REST API recall if SDK wasn't used or returned 0
        if is_connected and not remote_success:
            try:
                endpoint = f"{self.base_url}/v1/default/banks/{bank}/recall"
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                payload = {"query": query, "top_k": top_k}
                
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(endpoint, json=payload, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        results = data.get("results", [])
                        for idx, res in enumerate(results[:top_k]):
                            text = res.get("text", res.get("content", ""))
                            meta = res.get("metadata", {})
                            item = HindsightMemoryItem(
                                id=meta.get("id", f"rest_{idx}"),
                                incident_id=meta.get("incident_id", "historical"),
                                title=meta.get("title", f"Historical Incident {idx+1}"),
                                content=text,
                                affected_services=json.loads(meta.get("affected_services", "[]")) if isinstance(meta.get("affected_services"), str) else (meta.get("affected_services") or affected_services),
                                root_cause_service=meta.get("root_cause_service"),
                                remediation_action=meta.get("remediation_action"),
                                recovery_verified=str(meta.get("recovery_verified")).lower() == "true",
                                tags=res.get("tags", ["hindsight"]),
                                timestamp=meta.get("retained_at", datetime.now(timezone.utc).isoformat()),
                            )
                            recalled_items.append(item)
                        remote_success = True
                        logger.info(f"[HINDSIGHT] Recalled {len(recalled_items)} memories via REST API from bank '{bank}'")
            except Exception as e:
                logger.warning(f"[HINDSIGHT] REST recall endpoint error: {e}")

        # Determine explicit connection status and memory source
        if remote_success or is_connected:
            conn_status = "CONNECTED_TO_HINDSIGHT"
            mem_source = "Vectorize Hindsight Engine"
        else:
            conn_status = "HINDSIGHT_UNAVAILABLE"
            mem_source = "Local Fallback Cache"
            # Fallback to local file if server is offline
            recalled_items = self._recall_from_local_bank(affected_services, query, top_k)
            if recalled_items:
                logger.info(f"[HINDSIGHT] Recalled {len(recalled_items)} memories from local fallback cache")

        formatted_context = self._format_recalled_context(recalled_items)

        return HindsightRecallResult(
            enabled=self.enabled,
            connection_status=conn_status,
            memory_source=mem_source,
            status="OK" if recalled_items else ("EMPTY" if is_connected else "OFFLINE"),
            bank_id=bank,
            memories_recalled=len(recalled_items),
            memories=recalled_items,
            formatted_context=formatted_context,
        )

    def clear_bank(self, bank_id: Optional[str] = None) -> bool:
        """Clears memory bank using real Hindsight DELETE API and local file cleanup."""
        target_bank = bank_id or self.bank_id
        success = False

        # 1. Try SDK delete_bank
        if self._sdk_client:
            try:
                self._sdk_client.delete_bank(target_bank)
                logger.info(f"[HINDSIGHT] Cleared memory bank '{target_bank}' via SDK")
                success = True
            except Exception as e:
                logger.debug(f"[HINDSIGHT] SDK delete_bank notice: {e}")

        # 2. Try REST DELETE endpoint
        if not success:
            try:
                endpoint = f"{self.base_url}/v1/default/banks/{target_bank}"
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.delete(endpoint, headers=headers)
                    if resp.status_code in (200, 204):
                        logger.info(f"[HINDSIGHT] Cleared memory bank '{target_bank}' via REST DELETE")
                        success = True
            except Exception as e:
                logger.debug(f"[HINDSIGHT] REST delete_bank notice: {e}")

        # Clean local storage file as well
        try:
            if os.path.exists(self._local_storage_path):
                os.remove(self._local_storage_path)
            data_dir = os.path.join(os.getcwd(), "hindsight_data")
            bank_file = os.path.join(data_dir, f"bank_{target_bank}.json")
            if os.path.exists(bank_file):
                os.remove(bank_file)
            success = True
        except Exception as e:
            logger.error(f"[HINDSIGHT] Error removing local files: {e}")

        return success

    def _save_to_local_bank(self, memory_item: HindsightMemoryItem):
        """Persists memory item to local storage file."""
        try:
            memories = []
            if os.path.exists(self._local_storage_path):
                with open(self._local_storage_path, "r", encoding="utf-8") as f:
                    memories = json.load(f)
            
            memories = [m for m in memories if m.get("incident_id") != memory_item.incident_id]
            memories.append(memory_item.model_dump())
            
            with open(self._local_storage_path, "w", encoding="utf-8") as f:
                json.dump(memories, f, indent=2)
        except Exception as e:
            logger.error(f"[HINDSIGHT] Error writing to local bank: {e}")

    def _recall_from_local_bank(self, affected_services: List[str], query: str, top_k: int) -> List[HindsightMemoryItem]:
        """Retrieves memories from local storage file if server is offline."""
        if not os.path.exists(self._local_storage_path):
            return []
        try:
            with open(self._local_storage_path, "r", encoding="utf-8") as f:
                raw_memories = json.load(f)
            
            scored_memories = []
            query_lower = query.lower()
            affected_set = set(svc.lower() for svc in affected_services)
            
            for item_dict in raw_memories:
                item = HindsightMemoryItem(**item_dict)
                score = 0.0
                
                item_services = set(svc.lower() for svc in item.affected_services)
                overlap = affected_set.intersection(item_services)
                score += len(overlap) * 3.0
                
                if item.root_cause_service and item.root_cause_service.lower() in affected_set:
                    score += 2.0
                    
                content_lower = item.content.lower()
                for token in query_lower.split():
                    if len(token) > 3 and token in content_lower:
                        score += 1.0
                        
                if score > 0:
                    scored_memories.append((score, item))
                    
            scored_memories.sort(key=lambda x: x[0], reverse=True)
            return [m[1] for m in scored_memories[:top_k]]
        except Exception as e:
            logger.error(f"[HINDSIGHT] Error reading local bank: {e}")
            return []

    def _format_recalled_context(self, memories: List[HindsightMemoryItem]) -> str:
        """Formats recalled memories into clean context for LLM RCA."""
        if not memories:
            return ""
        
        lines = [
            "=== HISTORICAL INCIDENT MEMORY (HINDSIGHT RECALL) ===",
            "NOTE: The following are verified historical incidents recalled from Hindsight memory.",
            "Use them as historical context and supporting evidence to inform your diagnosis.",
            "Current live telemetry remains authoritative if evidence conflicts.",
            ""
        ]
        
        for idx, mem in enumerate(memories, 1):
            lines.append(f"--- RECALLED MEMORY #{idx} ---")
            lines.append(f"Incident Title: {mem.title}")
            lines.append(f"Affected Microservices: {', '.join(mem.affected_services)}")
            lines.append(f"Identified Root Cause: {mem.root_cause_service or 'Unknown'}")
            lines.append(f"Successful Remediation: {mem.remediation_action or 'None'}")
            lines.append(f"Recovery Verified: {'YES' if mem.recovery_verified else 'NO'}")
            lines.append(f"Operational Lessons & Summary: {mem.content}")
            lines.append("")
            
        lines.append("=====================================================")
        return "\n".join(lines)

hindsight_client = HindsightClient()
