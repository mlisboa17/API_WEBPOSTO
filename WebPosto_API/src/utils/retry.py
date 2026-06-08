from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


async def retry_async(fn: Callable[[], Awaitable[T]], attempts: int = 3) -> T:
    last_exc: Exception | None = None
    for idx in range(attempts):
        try:
            return await fn()
        except Exception as exc:
            last_exc = exc
            if idx < attempts - 1:
                await asyncio.sleep(0.15 * (idx + 1))
    assert last_exc is not None
    raise last_exc
