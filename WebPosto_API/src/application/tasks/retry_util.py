"""Retry com backoff exponencial para chamadas externas."""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    base_delay: float = 0.5,
    retry_on: tuple = (TimeoutError, ConnectionError, OSError),
) -> T:
    last: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except retry_on as e:
            last = e
            if attempt >= max_attempts:
                break
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning("retry %s/%s após %ss: %s", attempt, max_attempts, delay, e)
            await asyncio.sleep(delay)
    assert last is not None
    raise last
