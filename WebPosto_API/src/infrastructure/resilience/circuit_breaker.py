"""
Circuit breaker para chamadas à API externa WebPosto.
Estados: CLOSED → OPEN → HALF_OPEN → CLOSED.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failures: int = field(default=0, init=False)
    _opened_at: float = field(default=0.0, init=False)
    _lock: Lock = field(default_factory=Lock, init=False)

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.monotonic() - self._opened_at >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
            return self._state

    def allow_request(self) -> bool:
        st = self.state
        return st in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
                logger.warning(
                    "Circuit breaker '%s' OPEN após %s falhas",
                    self.name,
                    self._failures,
                )

    def call(self, fn: Callable[[], T], *, on_open: Optional[Callable[[], T]] = None) -> T:
        if not self.allow_request():
            if on_open is not None:
                return on_open()
            raise RuntimeError(f"Circuit breaker '{self.name}' está OPEN")
        try:
            result = fn()
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failures": self._failures,
                "failure_threshold": self.failure_threshold,
                "recovery_timeout_s": self.recovery_timeout,
            }


_webposto_breaker = CircuitBreaker(
    name="webposto_api",
    failure_threshold=5,
    recovery_timeout=60.0,
)


def get_webposto_circuit_breaker() -> CircuitBreaker:
    return _webposto_breaker
