"""
Cliente HTTP assíncrono com timeout estrito (5s) e circuit breaker.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from src.infrastructure.config.settings import settings
from src.infrastructure.resilience.circuit_breaker import get_webposto_circuit_breaker

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 5.0


def _timeout() -> httpx.Timeout:
    total = float(
        getattr(settings, "webposto_http_timeout_seconds", None)
        or settings.webposto_timeout_seconds
        or DEFAULT_TIMEOUT_S
    )
    total = min(total, 30.0)
    return httpx.Timeout(total, connect=min(2.0, total))


class ExternalHttpClient:
    """GET/POST à API Quality com limites de tempo e resiliência."""

    def __init__(self, base_url: str, *, verify_ssl: bool = True) -> None:
        self.base_url = base_url.rstrip("/")
        self.verify_ssl = verify_ssl
        self._breaker = get_webposto_circuit_breaker()

    async def get(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        url = f"{self.base_url}{path if path.startswith('/') else '/' + path}"

        async def _do() -> httpx.Response:
            async with httpx.AsyncClient(timeout=_timeout(), verify=self.verify_ssl) as client:
                return await client.get(url, params=params or {}, headers=headers)

        if not self._breaker.allow_request():
            raise RuntimeError("Circuit breaker webposto_api OPEN — chamada bloqueada")
        try:
            response = await _do()
            if response.status_code >= 500:
                self._breaker.record_failure()
            else:
                self._breaker.record_success()
            return response
        except Exception:
            self._breaker.record_failure()
            raise

    async def head_connectivity(self) -> tuple[bool, int, int]:
        """Teste rápido de conectividade (sem CHAVE)."""
        try:
            async with httpx.AsyncClient(timeout=_timeout(), verify=self.verify_ssl) as client:
                r = await client.head(self.base_url)
                return True, r.status_code, 0
        except httpx.TimeoutException:
            return False, 0, 504
        except Exception:
            return False, 0, 502
