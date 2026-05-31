from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Tuple

from src.infrastructure.cache.valkey_manager import ValkeyManager, get_cache


class ExpenseDeduplicator:
    def __init__(self, cache: ValkeyManager | None = None, ttl_seconds: int = 24 * 3600) -> None:
        self._cache = cache or get_cache()
        self._ttl_seconds = ttl_seconds

    @staticmethod
    def payload_hash(payload: Any) -> str:
        raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def check_and_mark(self, payload: Any) -> Tuple[bool, float]:
        start = time.perf_counter()
        digest = self.payload_hash(payload)
        key = f"expense:dedupe:{digest}"
        duplicated = self._cache.get_json(key) is not None
        if not duplicated:
            self._cache.set_json(key, {"hash": digest}, ttl=self._ttl_seconds)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return duplicated, elapsed_ms
