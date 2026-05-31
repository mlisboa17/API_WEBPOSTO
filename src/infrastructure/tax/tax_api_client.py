import httpx
import asyncio
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class CircuitOpen(Exception):
    pass


class TaxAPIClient:
    def __init__(self, base_url: str, timeout: float = 5.0):
        self.base_url = base_url
        self.timeout = timeout
        self._failures = 0
        self._lock = asyncio.Lock()

    async def get_ncm_info(self, ncm: str) -> Optional[Dict[str, Any]]:
        # Simple circuit breaker: open after 3 consecutive failures
        async with self._lock:
            if self._failures >= 3:
                raise CircuitOpen("Circuit open for Tax API")

        url = f"{self.base_url}/ncm/{ncm}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.get(url)
                r.raise_for_status()
                async with self._lock:
                    self._failures = 0
                return r.json()
        except Exception as e:
            async with self._lock:
                self._failures += 1
            logger.warning("Tax API call failed: %s", e)
            return None
