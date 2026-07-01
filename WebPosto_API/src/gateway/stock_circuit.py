"""RT-02 — Circuit breaker isolado para fluxo /v1/stock."""
from __future__ import annotations

from src.gateway.webposto_client import WebPostoClient

STOCK_ENDPOINT_KEYS = frozenset(
    {
        "produto_estoque",
        "produto",
        "tanque",
        "estoque_periodo",
    }
)

STOCK_GATE_ENDPOINT = "produto_estoque"


def stock_circuit_status(client: WebPostoClient) -> str:
    statuses = [client.breaker.get_status(key) for key in STOCK_ENDPOINT_KEYS]
    if any(status == "OPEN" for status in statuses):
        return "OPEN"
    if any(status == "HALF_OPEN" for status in statuses):
        return "HALF_OPEN"
    return "CLOSED"


def stock_circuit_open(client: WebPostoClient) -> bool:
    return stock_circuit_status(client) == "OPEN"


def record_stock_live_failure(client: WebPostoClient, *, block_seconds: int) -> None:
    client.breaker.record_failure(STOCK_GATE_ENDPOINT)
    client.breaker.block_endpoint(STOCK_GATE_ENDPOINT, duration_seconds=block_seconds)
    for key in STOCK_ENDPOINT_KEYS:
        if key != STOCK_GATE_ENDPOINT:
            client.breaker.record_failure(key)
