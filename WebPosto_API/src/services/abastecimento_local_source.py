"""Fonte local de abastecimentos — D0=pista_cache RAM, histórico=sales_daily_summary.

Evita paginação síncrona em /INTEGRACAO/ABASTECIMENTO no hot path de
composition / analytics / data-audit.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select

from src.core.config import OFFICIAL_COMPANY_CODES
from src.domain.adelaide.fuel_catalog import rotulo_combustivel
from src.utils.filial_normalizer import resolve_empresa_codigo

logger = logging.getLogger(__name__)


def _targets(empresa_codigo: int | None) -> list[int]:
    empresa = resolve_empresa_codigo(empresa_codigo)
    if empresa is not None:
        return [int(empresa)]
    return list(OFFICIAL_COMPANY_CODES)


def _row_from_baixado(it: Any) -> dict[str, Any]:
    emp = int(getattr(it, "idEmpresa", 0) or 0)
    prod = getattr(it, "idProduto", None)
    return {
        "abastecimentoCodigo": getattr(it, "idAbastecimento", None),
        "codigo": getattr(it, "idAbastecimento", None),
        "empresaCodigo": emp,
        "empresa": emp,
        "dataHoraAbastecimento": getattr(it, "dataHora", None),
        "dataFiscal": getattr(it, "dataHora", None),
        "codigoBico": getattr(it, "bico", None),
        "bico": getattr(it, "bico", None),
        "quantidade": float(getattr(it, "litros", 0) or 0),
        "quantidadeLitros": float(getattr(it, "litros", 0) or 0),
        "litros": float(getattr(it, "litros", 0) or 0),
        "valorTotal": float(getattr(it, "valorTotal", 0) or 0),
        "valorVenda": float(getattr(it, "valorTotal", 0) or 0),
        "codigoProduto": str(prod) if prod is not None else "",
        "produtoCodigo": str(prod) if prod is not None else "",
        "produtoDescricao": str(getattr(it, "descricaoProduto", None) or ""),
        "nomeProduto": str(getattr(it, "descricaoProduto", None) or ""),
        "vendaCodigo": getattr(it, "idVenda", None),
        "fonteLocal": "pista_cache_RAM",
    }


def ingest_ram(empresa_codigo: int | None = None) -> tuple[list[dict[str, Any]], str]:
    """Lê baixados do snapshot RAM. Retorna (rows, fonte)."""
    from src.services.pista_cache_service import get_pista_cache

    snap = get_pista_cache().get_snapshot()
    items = list(snap.baixados or [])
    if not items:
        return [], "pista_cache_vazio"

    allowed = set(_targets(empresa_codigo))
    rows: list[dict[str, Any]] = []
    for it in items:
        emp = int(getattr(it, "idEmpresa", 0) or 0)
        if emp not in allowed:
            continue
        litros = float(getattr(it, "litros", 0) or 0)
        valor = float(getattr(it, "valorTotal", 0) or 0)
        if litros <= 0 and valor <= 0:
            continue
        rows.append(_row_from_baixado(it))
    return rows, f"pista_cache_RAM data_ref={snap.data_ref} n={len(rows)}"


async def ingest_db(
    data_inicial: str,
    data_final: str,
    empresa_codigo: int | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """Expande sales_daily_summary em linhas sintéticas compatíveis com composition."""
    try:
        from src.infrastructure.config.database import AsyncSessionLocal
        from src.models.sales_daily_summary_model import SalesDailySummaryModel

        start = date.fromisoformat(data_inicial)
        end = date.fromisoformat(data_final)
        hoje = date.today()
        if end >= hoje:
            end = hoje - timedelta(days=1)
        if start > end:
            return [], "sales_daily_summary(sem_historico)"

        allowed = set(_targets(empresa_codigo))
        rows: list[dict[str, Any]] = []
        async with AsyncSessionLocal() as session:
            stmt = select(SalesDailySummaryModel).where(
                SalesDailySummaryModel.data_referencia >= start,
                SalesDailySummaryModel.data_referencia <= end,
                SalesDailySummaryModel.empresa_codigo.in_(allowed),
            )
            result = await session.execute(stmt)
            summaries = list(result.scalars().all())

        for s in summaries:
            qtd = max(int(s.quantidade_abastecimentos or 0), 0)
            litros = float(s.litros_vendidos or 0)
            valor = float(s.faturamento_bruto or 0)
            if qtd <= 0 and (litros > 0 or valor > 0):
                qtd = 1
            if qtd <= 0:
                continue
            litros_each = litros / qtd
            valor_each = valor / qtd
            prod = str(s.codigo_produto_webposto or "")
            nome = (
                str(s.nome_produto or "").strip()
                or rotulo_combustivel(prod)
                or f"Produto {prod or '?'}"
            )
            dia = s.data_referencia.isoformat()
            for i in range(qtd):
                aid = f"sds-{s.empresa_codigo}-{dia}-{prod}-{i}"
                rows.append(
                    {
                        "abastecimentoCodigo": aid,
                        "codigo": aid,
                        "empresaCodigo": int(s.empresa_codigo),
                        "empresa": int(s.empresa_codigo),
                        "dataHoraAbastecimento": f"{dia}T12:00:00",
                        "dataFiscal": dia,
                        "codigoBico": None,
                        "quantidade": litros_each,
                        "quantidadeLitros": litros_each,
                        "litros": litros_each,
                        "valorTotal": valor_each,
                        "valorVenda": valor_each,
                        "codigoProduto": prod,
                        "produtoCodigo": prod,
                        "produtoDescricao": nome,
                        "nomeProduto": nome,
                        "fonteLocal": "sales_daily_summary",
                    }
                )
        return rows, f"sales_daily_summary n={len(rows)} dias={start}..{end}"
    except Exception as exc:
        logger.warning("ingest_db abastecimentos falhou: %s", exc)
        return [], f"sales_daily_summary(erro): {exc}"


async def fetch_abastecimentos_local_first(
    data_inicial: str,
    data_final: str,
    empresa_codigo: int | None = None,
    *,
    allow_http_fallback: bool = False,
    http_fetcher=None,
) -> tuple[list[dict[str, Any]], str]:
    """D0→RAM; histórico→DB; opcionalmente HTTP se vazio."""
    hoje = date.today().isoformat()
    empresa = resolve_empresa_codigo(empresa_codigo)
    single = data_inicial == data_final
    is_d0 = single and data_inicial == hoje

    rows: list[dict[str, Any]] = []
    fontes: list[str] = []

    if is_d0 or (data_inicial <= hoje <= data_final):
        ram_rows, ram_fonte = ingest_ram(empresa)
        if ram_rows:
            rows.extend(ram_rows)
            fontes.append(ram_fonte)

    if not is_d0 or not rows:
        db_rows, db_fonte = await ingest_db(data_inicial, data_final, empresa)
        if db_rows:
            # Evita duplicar D0 se RAM já cobriu o dia
            if is_d0 and rows:
                pass
            else:
                rows.extend(db_rows)
                fontes.append(db_fonte)
        elif db_fonte:
            fontes.append(db_fonte)

    if rows:
        return rows, "+".join(fontes) if fontes else "local"

    # D0 nunca bloqueia em ABASTECIMENTO HTTP — UI espera RAM do PistaSyncWorker
    if is_d0:
        return [], "pista_cache_vazio(D0_sem_http)"

    if allow_http_fallback and callable(http_fetcher):
        import asyncio

        try:
            http_rows = await asyncio.wait_for(
                http_fetcher(data_inicial, data_final, empresa),
                timeout=1.5,
            )
            return list(http_rows or []), "ABASTECIMENTO(http_fallback)"
        except Exception as exc:
            logger.warning("HTTP fallback abastecimentos falhou: %s", exc)
            return [], f"local_vazio+http_erro: {exc}"

    return [], "local_vazio"
