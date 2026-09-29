import json
import logging
import sys
from typing import Optional, Any, Dict
from datetime import datetime, timezone
from .models import LogEntry
from .engine import telemetry_engine

class StructuredLogger:
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.std_logger = logging.getLogger(f"shopflow.{service_name}")
        if not self.std_logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter('%(message)s'))
            self.std_logger.addHandler(handler)
            self.std_logger.setLevel(logging.INFO)

    def _log(
        self,
        level: str,
        event: str,
        message: str,
        request_id: Optional[str] = None,
        dependency: Optional[str] = None,
        latency_ms: Optional[float] = None,
        status_code: Optional[int] = None,
        service: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> LogEntry:
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            service=service or self.service_name,
            level=level,
            event=event,
            message=message,
            request_id=request_id,
            dependency=dependency,
            latency_ms=round(latency_ms, 2) if latency_ms is not None else None,
            status_code=status_code,
            metadata=metadata or {}
        )
        # Output structured JSON log to stdout
        self.std_logger.info(json.dumps(entry.model_dump()))
        # Record into centralized TelemetryEngine buffer
        telemetry_engine.record_log(entry)
        return entry

    def info(self, event: str, message: str, **kwargs):
        return self._log("INFO", event, message, **kwargs)

    def warn(self, event: str, message: str, **kwargs):
        return self._log("WARN", event, message, **kwargs)

    def error(self, event: str, message: str, **kwargs):
        return self._log("ERROR", event, message, **kwargs)

    def debug(self, event: str, message: str, **kwargs):
        return self._log("DEBUG", event, message, **kwargs)

def get_logger(service_name: str) -> StructuredLogger:
    return StructuredLogger(service_name)
