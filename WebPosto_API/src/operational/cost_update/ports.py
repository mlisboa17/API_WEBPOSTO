"""Interfaces futuras de escrita. Sem implementacao concreta nesta fase."""

from __future__ import annotations

from typing import Any, Protocol

WRITES_NOT_IMPLEMENTED = "COST_UPDATE_WRITES_NOT_IMPLEMENTED"


class CostUpdateWriteError(RuntimeError):
    def __init__(self, message: str = WRITES_NOT_IMPLEMENTED) -> None:
        super().__init__(message)


class CostUpdateGatewayPort(Protocol):
    def update_cost(self, proposal: Any) -> dict[str, Any]: ...


class CostUpdateVerificationPort(Protocol):
    def verify_updated_cost(self, produto_codigo: int, expected_cost: Any) -> dict[str, Any]: ...


class UnimplementedCostUpdateGateway:
    """PUT futuro: /INTEGRACAO/ALTERAR_PRODUTO/{id} com precoCusto. Nao enviar."""

    def update_cost(self, proposal: Any) -> dict[str, Any]:
        raise CostUpdateWriteError()


class UnimplementedCostUpdateVerifier:
    def verify_updated_cost(self, produto_codigo: int, expected_cost: Any) -> dict[str, Any]:
        raise CostUpdateWriteError()
