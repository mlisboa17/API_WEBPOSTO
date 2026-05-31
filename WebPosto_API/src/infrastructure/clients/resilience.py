"""
Resiliência WebPosto — retry exponencial + jitter, circuit breaker em 401/403 (Grok).
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Awaitable, Callable, TypeVar

from src.infrastructure.resilience.circuit_breaker import get_webposto_circuit_breaker
from src.webposto.exceptions import AuthError, ServerError, WebPostoError

logger = logging.getLogger(__name__)

T = TypeVar("T")

RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


def log_auth_critical(exc: AuthError, *, path: str = "") -> None:
    logger.critical(
        "WEBPOSTO_AUTH_FAILURE path=%s status=%s — verifique WEBPOSTO_API_KEY e permissões no contrato Quality",
        path or "?",
        getattr(exc, "status_code", 401),
        exc_info=False,
    )
    get_webposto_circuit_breaker().record_failure()


async def with_exponential_backoff(
    fn: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 4,
    base_delay: float = 0.4,
    max_delay: float = 8.0,
    retry_on_status: frozenset[int] = RETRYABLE_STATUS,
) -> T:
    """
    Retry assíncrono com jitter para 429/5xx.
    401/403: log crítico imediato, sem retry.
    """
    last: Exception | None = None
    breaker = get_webposto_circuit_breaker()

    if not breaker.allow_request():
        raise RuntimeError("Circuit breaker webposto_api OPEN")

    for attempt in range(1, max_attempts + 1):
        try:
            result = await fn()
            breaker.record_success()
            return result
        except AuthError as e:
            log_auth_critical(e)
            raise
        except (ServerError, WebPostoError) as e:
            code = getattr(e, "status_code", 500)
            if code in retry_on_status and attempt < max_attempts:
                delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                delay += random.uniform(0, delay * 0.25)
                logger.warning(
                    "webposto retry %s/%s HTTP %s — aguardando %.2fs",
                    attempt,
                    max_attempts,
                    code,
                    delay,
                )
                last = e
                await asyncio.sleep(delay)
                continue
            breaker.record_failure()
            raise
        except (TimeoutError, ConnectionError, OSError) as e:
            if attempt >= max_attempts:
                breaker.record_failure()
                raise
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            delay += random.uniform(0, delay * 0.2)
            logger.warning("webposto retry rede %s/%s: %s", attempt, max_attempts, e)
            last = e
            await asyncio.sleep(delay)

    assert last is not None
    raise last
