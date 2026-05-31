"""
WebPosto Async HTTP Client with Connection Pooling and Retries
"""
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from typing import Any, Dict, Optional

class WebPostoClient:
    def __init__(self, base_url: str, timeout: float = 5.0, max_connections: int = 10):
        import asyncio
        self.base_url = base_url
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            limits=httpx.Limits(max_connections=max_connections, max_keepalive_connections=max_connections)
        )
        self._semaphore = asyncio.Semaphore(10)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        async with self._semaphore:
            return await self.client.get(endpoint, params=params)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def post(self, endpoint: str, json: Optional[Dict[str, Any]] = None) -> httpx.Response:
        async with self._semaphore:
            return await self.client.post(endpoint, json=json)

    async def close(self) -> None:
        await self.client.aclose()
