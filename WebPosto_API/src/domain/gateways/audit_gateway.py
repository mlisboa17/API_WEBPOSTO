"""Contrato ACL para dados de auditoria — sem HTTP no domínio."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from src.domain.entities.audit import AuditRawData, SubCentroCusto


class AuditGateway(ABC):
    @abstractmethod
    async def fetch_transactions(
        self,
        data_inicio: date,
        data_fim: date,
        sub_centro: SubCentroCusto,
        *,
        posto_id: str = "default",
        filial: list[int] | None = None,
    ) -> AuditRawData:
        """Busca caixa, apresentado, abastecimento/vendas e despesas do período."""
