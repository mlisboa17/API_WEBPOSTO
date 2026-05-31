from __future__ import annotations

from typing import Awaitable, Callable, TypeVar

from src.infrastructure.resilience.circuit_breaker import get_webposto_circuit_breaker

T = TypeVar("T")


async def execute_report_call(fn: Callable[[], Awaitable[T]]) -> T:
    """Protege chamadas a relatórios com circuit breaker compartilhado."""
    breaker = get_webposto_circuit_breaker()
    if not breaker.allow_request():
        raise RuntimeError("Circuit breaker 'webposto_api' está OPEN")

    try:
        result = await fn()
        breaker.record_success()
        return result
    except Exception:
        breaker.record_failure()
        raise
