"""Testes unitários para o relatório executivo consolidado."""

from __future__ import annotations

import pytest

from src.services.executive_consolidated_report_service import (
    ExecutiveConsolidatedReportService,
    generate_report,
)


class TestExecutiveConsolidatedReportService:
    @pytest.mark.asyncio
    async def test_generate_report_returns_markdown(self) -> None:
        report, markdown = await generate_report()
        assert report.bloco_6_despesas.total_despesas_gerenciais > 0
        assert "# Relatório Executivo Consolidado" in markdown
        assert report.bloco_1_combustiveis.status == "DISPONÍVEL"

    @pytest.mark.asyncio
    async def test_block_12_contains_readiness_rows(self) -> None:
        service = ExecutiveConsolidatedReportService()
        report = await service.build_report()
        assert len(report.bloco_12_prontidao.tabela) >= 10
        assert any(
            "INDISPONÍVEL" in row["confiabilidade"] or "INDISPONÍVEL" in row["valor"]
            for row in report.bloco_12_prontidao.tabela
        )

    @pytest.mark.asyncio
    async def test_fuel_and_convenience_available(self) -> None:
        service = ExecutiveConsolidatedReportService()
        report = await service.build_report()
        assert report.bloco_1_combustiveis.status == "DISPONÍVEL"
        assert report.bloco_3_margens.status == "DISPONÍVEL"
        assert report.bloco_4_conveniencia.status == "DISPONÍVEL"
        assert len(report.bloco_4_conveniencia.filiais) >= 1
        assert report.bloco_1_combustiveis.resumo.total_litros > 0
        assert report.bloco_1_combustiveis.resumo.total_valor > 0

    @pytest.mark.asyncio
    async def test_auto_classificacao_despesas(self) -> None:
        service = ExecutiveConsolidatedReportService()
        report = await service.build_report()
        assert report.bloco_5_dre.resumo_auto_classificacao["total_classificadas"] > 0
        assert len(report.bloco_6_despesas.auto_classificadas) > 0
        assert report.bloco_5_dre.despesas_auto_classificadas
