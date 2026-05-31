"""
Catálogo Adelaide — códigos reais de combustível WebPosto (Posto VIP · Rio Doce).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, Optional

# codigoProduto → rótulo alinhado ao relatório do Posto VIP
FUEL_CATALOG: Dict[str, str] = {
    "1257884": "Gasolina",
    "1257885": "Gasolina aditivada",
    "1975728": "Etanol aditivado",
    "1260803": "Diesel S10",
    "1257999": "Diesel S10",
    "1258001": "Diesel comum",
}

# Custo médio de aquisição por litro (R$) — ajuste com NF entrada / APRIX
DEFAULT_ACQUISITION_COST_PER_LITER: Dict[str, Decimal] = {
    "1257884": Decimal("4.85"),
    "1975728": Decimal("3.42"),
    "1260803": Decimal("5.12"),
    "1257999": Decimal("4.95"),
    "1258001": Decimal("4.78"),
}

CAMPOS_NOME_PRODUTO = (
    "descricaoProduto",
    "nomeProduto",
    "produtoNome",
    "descricaoProdutoCombustivel",
    "produtoDescricao",
    "descricao",
    "nomeCombustivel",
)


def rotulo_combustivel(codigo: str, nome_api: Optional[str] = None) -> str:
    c = str(codigo or "").strip()
    if not c:
        return "—"
    if c in FUEL_CATALOG:
        return FUEL_CATALOG[c]
    if nome_api and str(nome_api).strip():
        return str(nome_api).strip()
    return "Combustível"


def custo_aquisicao_litro(codigo: str) -> Decimal:
    return DEFAULT_ACQUISITION_COST_PER_LITER.get(
        str(codigo or "").strip(), Decimal("0")
    )


def eh_combustivel_codigo(codigo: str) -> bool:
    return str(codigo or "").strip() in FUEL_CATALOG
