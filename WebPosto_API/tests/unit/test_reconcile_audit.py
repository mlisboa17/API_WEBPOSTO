"""Testes do caso de uso reconcile_audit."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.application.usecases.reconcile_audit import ReconcileAuditUseCase
from src.domain.entities.audit import (
    AuditDespesa,
    AuditRawData,
    AuditTurno,
    AuditVendaLinha,
    SubCentroCusto,
)


@pytest.fixture
def gateway_pista():
    gw = AsyncMock()
    gw.fetch_transactions.return_value = AuditRawData(
        posto_id="1",
        sub_centro=SubCentroCusto.PISTA,
        data_inicio=date(2026, 5, 1),
        data_fim=date(2026, 5, 17),
        turnos=[
            AuditTurno(turno_id="1", valor_caixa=Decimal("1000"), valor_sistema=Decimal("950")),
        ],
        vendas=[
            AuditVendaLinha(produto_codigo="1257884", litros=Decimal("100.5"), faturamento=Decimal("700")),
        ],
        despesas=[AuditDespesa(descricao="Despesa pista", valor=Decimal("50"), sub_centro=SubCentroCusto.PISTA)],
        caixa_apurado_total=Decimal("1000"),
        caixa_apresentado_total=Decimal("950"),
    )
    return gw


@pytest.fixture
def gateway_loja():
    gw = AsyncMock()
    gw.fetch_transactions.return_value = AuditRawData(
        posto_id="1",
        sub_centro=SubCentroCusto.LOJA,
        data_inicio=date(2026, 5, 1),
        data_fim=date(2026, 5, 17),
        turnos=[
            AuditTurno(turno_id="1", valor_caixa=Decimal("500"), valor_sistema=Decimal("500")),
        ],
        vendas=[
            AuditVendaLinha(categoria="Conveniencia", faturamento=Decimal("300")),
        ],
        caixa_apurado_total=Decimal("500"),
        caixa_apresentado_total=Decimal("500"),
    )
    return gw


def test_pista_galonagem_e_divergencia(gateway_pista):
    import asyncio

    uc = ReconcileAuditUseCase(gateway_pista)
    result = asyncio.run(uc.execute(date(2026, 5, 1), date(2026, 5, 17), "PISTA", use_cache=False))
    assert result.sub_centro == SubCentroCusto.PISTA
    assert result.galonagem_litros == Decimal("100.50")
    assert result.faturamento_periodo == Decimal("700.00")
    assert result.divergencia == Decimal("50.00")
    assert result.turnos_totais == 1


def test_loja_zera_galonagem(gateway_loja):
    import asyncio

    uc = ReconcileAuditUseCase(gateway_loja)
    result = asyncio.run(uc.execute(date(2026, 5, 1), date(2026, 5, 17), "LOJA", use_cache=False))
    assert result.galonagem_litros == Decimal("0.00")
    assert result.faturamento_periodo == Decimal("300.00")
    assert result.divergencia == Decimal("0.00")
