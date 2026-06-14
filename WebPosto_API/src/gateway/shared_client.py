"""Singleton WebPostoClient — circuit breaker compartilhado (F08.0)."""
from __future__ import annotations

from src.gateway.webposto_client import WebPostoClient

_CLIENT: WebPostoClient | None = None


def get_webposto_client() -> WebPostoClient:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = WebPostoClient()
    return _CLIENT
