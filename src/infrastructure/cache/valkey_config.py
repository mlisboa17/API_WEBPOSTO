import asyncio
from typing import Any, Optional
import logging
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class ValkeyCache:
    def __init__(self, url: str = "redis://localhost:6379/0", default_ttl: int = 10):
        self.url = url
        self.default_ttl = default_ttl
        self._client: Optional[redis.Redis] = None
        self.hits = 0
        self.misses = 0

    async def connect(self):
        if self._client is None:
            self._client = redis.from_url(self.url, decode_responses=True)
            await self._client.ping()

    async def get(self, key: str) -> Optional[Any]:
        if self._client is None:
            await self.connect()
        val = await self._client.get(key)
        if val is None:
            self.misses += 1
            return None
        self.hits += 1
        return val

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        if self._client is None:
            await self.connect()
        ttl = ttl or self.default_ttl
        await self._client.setex(key, int(ttl), value)
        return True

    def hit_ratio(self) -> float:
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return float(self.hits) / float(total)
