"""
Filtros client-side para abastecimentos WebPosto (espelha dashboard operacional).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from src.domain.adelaide.fuel_catalog import FUEL_CATALOG


def is_afericao(row: dict[str, Any]) -> bool:
    v = row.get("afericao")
    if v is True or v == 1:
        return True
    return str(v or "").lower() == "true"


def valor_financeiro_abastecimento(row: dict[str, Any]) -> Decimal:
    """Prioriza valorTotal; senão quantidade × valorUnitario."""
    try:
        vt = Decimal(str(row.get("valorTotal") or 0))
    except Exception:
        vt = Decimal("0")
    if vt > 0:
        return vt
    try:
        q = Decimal(str(row.get("quantidade") or 0))
        vu = Decimal(str(row.get("valorUnitario") or 0))
    except Exception:
        return Decimal("0")
    if q > 0 and vu > 0:
        return (q * vu).quantize(Decimal("0.01"))
    return Decimal("0")


def codigo_produto(row: dict[str, Any]) -> str:
    return str(row.get("codigoProduto") or row.get("produtoCodigo") or "").strip()


def aplicar_filtros_abastecimento(
    registros: list[dict[str, Any]],
    *,
    excluir_afericao: bool = True,
    codigos_produto: Optional[list[str]] = None,
    apenas_combustivel: bool = False,
) -> list[dict[str, Any]]:
    """
    codigos_produto:
      - None: não filtra por código
      - []: filtro ativo, nenhum código permitido (lista vazia)
      - [..]: só esses códigos
    """
    out: list[dict[str, Any]] = []
    filtrar_codigo = codigos_produto is not None
    codigos_set = (
        {str(c).strip() for c in codigos_produto if str(c).strip()}
        if filtrar_codigo
        else set()
    )
    catalogo = set(FUEL_CATALOG.keys())

    for row in registros:
        if excluir_afericao and is_afericao(row):
            continue
        cod = codigo_produto(row)
        if apenas_combustivel and cod and cod not in catalogo:
            continue
        if filtrar_codigo and cod not in codigos_set:
            continue
        out.append(row)
    return out


def normalizar_registro_valor(row: dict[str, Any]) -> dict[str, Any]:
    """Garante valorTotal coerente para agregação Adelaide."""
    if row.get("valorTotal"):
        return row
    vf = valor_financeiro_abastecimento(row)
    if vf > 0:
        return {**row, "valorTotal": float(vf)}
    return row
