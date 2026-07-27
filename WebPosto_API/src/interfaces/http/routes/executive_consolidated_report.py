"""Rota para Relatório Executivo Consolidado — Sprint 55.

GET /api/v1/executive/consolidated-report          -> JSON completo
GET /api/v1/executive/consolidated-report/markdown -> Markdown para exportação
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from src.services.executive_consolidated_report_service import (
    ExecutiveConsolidatedReportService,
    ExecutiveReport,
)

router = APIRouter(
    prefix="/api/v1/executive/consolidated-report",
    tags=["Executive Consolidated Report"],
)


class MarkdownResponse(BaseModel):
    markdown: str


@router.get("", response_model=ExecutiveReport)
async def executive_consolidated_report() -> ExecutiveReport:
    """Retorna o relatório executivo consolidado em JSON com dados reais WebPosto."""
    service = ExecutiveConsolidatedReportService()
    return await service.build_report()


@router.get("/markdown", response_model=MarkdownResponse)
async def executive_consolidated_report_markdown() -> MarkdownResponse:
    """Retorna o relatório executivo consolidado em Markdown."""
    service = ExecutiveConsolidatedReportService()
    report = await service.build_report()
    return MarkdownResponse(markdown=service.to_markdown(report))
