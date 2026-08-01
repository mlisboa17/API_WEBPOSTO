"""Rota para Relatório Executivo Consolidado — Sprint 55.

GET /api/v1/executive/consolidated-report          -> JSON completo
GET /api/v1/executive/consolidated-report/markdown -> Markdown para exportação
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.services.executive_consolidated_report_service import (
    ExecutiveConsolidatedReportService,
    ExecutiveReport,
)
from src.utils.filial_normalizer import resolve_empresa_codigo

LOGGER = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/executive/consolidated-report",
    tags=["Executive Consolidated Report"],
)


class MarkdownResponse(BaseModel):
    markdown: str


def _default_period() -> tuple[str, str]:
    """Retorna período padrão: últimos 7 dias."""
    hoje = date.today()
    inicio = hoje - timedelta(days=6)
    return str(inicio), str(hoje)


def _resolve_empresa(
    empresa_codigo: int | None,
    filial: str | None,
) -> int | None:
    raw = filial if filial is not None and str(filial).strip() != "" else empresa_codigo
    resolved = resolve_empresa_codigo(raw)
    LOGGER.info(
        "[Pista & Volumetria] Filial buscada: %s | ID resolvido: %s",
        raw if raw is not None else "TODAS",
        resolved if resolved is not None else "TODAS",
    )
    return resolved


@router.get("", response_model=ExecutiveReport)
async def executive_consolidated_report(
    dataInicial: str | None = Query(None, description="Data inicial (YYYY-MM-DD)"),
    dataFinal: str | None = Query(None, description="Data final (YYYY-MM-DD)"),
    empresaCodigo: int | None = Query(None, description="Código da empresa (filial)"),
    filial: str | None = Query(
        None, description="Alias de filial (Casa Caiada, VIP, TODAS, 001…)"
    ),
) -> ExecutiveReport:
    """Retorna o relatório executivo consolidado em JSON com dados reais WebPosto."""
    default_start, default_end = _default_period()
    start = dataInicial or default_start
    end = dataFinal or default_end
    empresa = _resolve_empresa(empresaCodigo, filial)

    service = ExecutiveConsolidatedReportService()
    return await service.build_report(
        data_inicial=start,
        data_final=end,
        empresa_codigo=empresa,
    )


@router.get("/markdown", response_model=MarkdownResponse)
async def executive_consolidated_report_markdown(
    dataInicial: str | None = Query(None, description="Data inicial (YYYY-MM-DD)"),
    dataFinal: str | None = Query(None, description="Data final (YYYY-MM-DD)"),
    empresaCodigo: int | None = Query(None, description="Código da empresa (filial)"),
    filial: str | None = Query(
        None, description="Alias de filial (Casa Caiada, VIP, TODAS, 001…)"
    ),
) -> MarkdownResponse:
    """Retorna o relatório executivo consolidado em Markdown."""
    default_start, default_end = _default_period()
    start = dataInicial or default_start
    end = dataFinal or default_end
    empresa = _resolve_empresa(empresaCodigo, filial)

    service = ExecutiveConsolidatedReportService()
    report = await service.build_report(
        data_inicial=start,
        data_final=end,
        empresa_codigo=empresa,
    )
    return MarkdownResponse(markdown=service.to_markdown(report))
