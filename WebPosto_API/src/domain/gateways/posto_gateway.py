"""
Contrato de integração com o posto (ACL) — domínio não conhece HTTP.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from src.domain.entities.sales import Filial, Product, SalesInvoice, TankVolume


class PostoGateway(ABC):
    @abstractmethod
    async def get_vendas_recentes(self, horas: int = 24) -> List[SalesInvoice]:
        """Vendas emitidas no período (horas retroativas)."""

    @abstractmethod
    async def get_volume_tanques(self) -> List[TankVolume]:
        """Leitura atual dos tanques."""

    @abstractmethod
    async def get_produto(self, produto_id: int) -> Optional[Product]:
        """Cadastro de um produto."""

    @abstractmethod
    async def listar_produtos(
        self,
        *,
        pagina: int = 0,
        tamanho: int = 50,
        nome: Optional[str] = None,
    ) -> List[Product]:
        """Catálogo paginado."""

    @abstractmethod
    async def listar_filiais(self) -> List[Filial]:
        """Empresas/filiais da chave."""

    @abstractmethod
    async def get_caixa_periodo(
        self,
        data_inicial: date,
        data_final: date,
    ) -> List[dict]:
        """Movimentos de caixa no período (dict bruto para fechamento)."""
