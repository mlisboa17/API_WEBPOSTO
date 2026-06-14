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

    def get_status(self, endpoint_key: str) -> str:
        if self.is_blocked(endpoint_key):
            return "OPEN"
        if self._failures.get(endpoint_key, 0) > 0:
            return "HALF_OPEN"
        return "CLOSED"

    def reset(self, endpoint_key: str | None = None) -> None:
        if endpoint_key is None:
            self._failures.clear()
            self._blocked_until.clear()
            return
        self._failures.pop(endpoint_key, None)
        self._blocked_until.pop(endpoint_key, None)

    def reset_many(self, endpoint_keys: set[str]) -> None:
        for key in endpoint_keys:
            self.reset(key)

    def snapshot_status(self, endpoint_keys: set[str] | None = None) -> dict[str, str]:
        keys = endpoint_keys or set(self._failures.keys()) | set(self._blocked_until.keys())
        return {key: self.get_status(key) for key in sorted(keys)}

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
