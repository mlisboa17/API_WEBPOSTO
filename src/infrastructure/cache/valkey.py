import redis.asyncio as redis
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class Valkey:
    def __init__(self, url: str = "redis://localhost:6379/0", ttl_seconds: int = 86400):
        self.url = url
        self.ttl = ttl_seconds
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
        v = await self._client.get(key)
        if v is None:
            self.misses += 1
            return None
        self.hits += 1
        return v

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        if self._client is None:
            await self.connect()
        await self._client.setex(key, int(ttl or self.ttl), value)
        return True

    def hit_ratio(self) -> float:
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return float(self.hits) / float(total)
