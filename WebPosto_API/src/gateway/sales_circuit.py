"""HOTFIX P0 — Circuit breaker isolado para fluxo /v1/sales."""
from __future__ import annotations

from src.gateway.webposto_client import WebPostoClient

SALES_ENDPOINT_KEYS = frozenset(
    {
        "venda",
        "venda_item",
        "venda_item_rede",
        "venda_forma_pagamento",
        "venda_forma_pagamento_rede",
    }
)

SALES_GATE_ENDPOINT = "venda"


def sales_circuit_status(client: WebPostoClient) -> str:
    statuses = [client.breaker.get_status(key) for key in SALES_ENDPOINT_KEYS]
    if any(status == "OPEN" for status in statuses):
        return "OPEN"
    if any(status == "HALF_OPEN" for status in statuses):
        return "HALF_OPEN"
    return "CLOSED"


def sales_circuit_open(client: WebPostoClient) -> bool:
    return sales_circuit_status(client) == "OPEN"


def record_sales_live_failure(client: WebPostoClient, *, block_seconds: int) -> None:
    """Registra falha no gate principal e abre circuito sales imediatamente."""
    client.breaker.record_failure(SALES_GATE_ENDPOINT)
    client.breaker.block_endpoint(SALES_GATE_ENDPOINT, duration_seconds=block_seconds)
    for key in SALES_ENDPOINT_KEYS:
        if key != SALES_GATE_ENDPOINT:
            client.breaker.record_failure(key)
