import os
import time
from typing import Optional, Any
import redis
from telemetry.logger import get_logger

logger = get_logger("redis-client")

class RedisClientWrapper:
    def __init__(self):
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", "6379"))
        self._client = None
        self._memory_cache = {}
        self._memory_ttls = {}
        self._connected = False
        self._try_connect()

    def _try_connect(self):
        try:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                socket_timeout=1.0,
                decode_responses=True
            )
            self._client.ping()
            self._connected = True
            logger.info("REDIS_CONNECTED", f"Connected to Redis at {self.host}:{self.port}")
        except Exception:
            self._connected = False
            self._client = None
            logger.info("REDIS_FALLBACK", "Redis server unavailable, using internal in-memory cache store")

    def get(self, key: str) -> Optional[str]:
        if self._connected and self._client:
            try:
                val = self._client.get(key)
                return val
            except Exception:
                self._connected = False

        # In-memory fallback
        if key in self._memory_cache:
            exp = self._memory_ttls.get(key)
            if exp and time.time() > exp:
                del self._memory_cache[key]
                del self._memory_ttls[key]
                return None
            return self._memory_cache[key]
        return None

    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        if self._connected and self._client:
            try:
                return bool(self._client.set(key, value, ex=ex))
            except Exception:
                self._connected = False

        # In-memory fallback
        self._memory_cache[key] = value
        if ex:
            self._memory_ttls[key] = time.time() + ex
        return True

    def delete(self, key: str) -> bool:
        if self._connected and self._client:
            try:
                return bool(self._client.delete(key))
            except Exception:
                pass
        self._memory_cache.pop(key, None)
        self._memory_ttls.pop(key, None)
        return True

redis_client = RedisClientWrapper()
