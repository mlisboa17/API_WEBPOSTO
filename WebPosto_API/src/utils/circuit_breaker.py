from __future__ import annotations

from datetime import datetime, timedelta, timezone


class SimpleCircuitBreaker:
    def __init__(self, failure_threshold: int = 3, block_seconds: int = 3600) -> None:
        self._threshold = failure_threshold
        self._block_seconds = block_seconds
        self._failures: dict[str, int] = {}
        self._blocked_until: dict[str, datetime] = {}

    def is_blocked(self, endpoint_key: str) -> bool:
        until = self._blocked_until.get(endpoint_key)
        if not until:
            return False
        if datetime.now(timezone.utc) >= until:
            self._blocked_until.pop(endpoint_key, None)
            self._failures[endpoint_key] = 0
            return False
        return True

    def record_success(self, endpoint_key: str) -> None:
        self._failures[endpoint_key] = 0
        self._blocked_until.pop(endpoint_key, None)

    def record_failure(self, endpoint_key: str) -> None:
        count = self._failures.get(endpoint_key, 0) + 1
        self._failures[endpoint_key] = count
        if count >= self._threshold:
            self._blocked_until[endpoint_key] = datetime.now(timezone.utc) + timedelta(seconds=self._block_seconds)

    def block_endpoint(self, endpoint_key: str, duration_seconds: int | None = None) -> None:
        secs = duration_seconds if duration_seconds is not None else self._block_seconds
        self._blocked_until[endpoint_key] = datetime.now(timezone.utc) + timedelta(seconds=secs)
