import json
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.domain.webposto.schemas import (
    WebPostoDespesa,
    WebPostoMovimentoCaixa,
    WebPostoVenda,
    WebPostoVendaItem,
)


def test_venda_and_item_accept_known_webposto_aliases():
    venda = WebPostoVenda.model_validate(
        {
            "codigo": 101,
            "filialCodigo": 11495,
            "dataVenda": "2026-07-23T10:30:00",
            "valor": "150.25",
        }
    )
    item = WebPostoVendaItem.model_validate(
        {
            "codigoVenda": 101,
            "codigoProduto": 55,
            "quantidade": "10.5",
            "precoUnitario": "12.00",
            "valor": "126.00",
            "grupoCodigo": 24554,
        }
    )

    assert venda.venda_codigo == item.venda_codigo == 101
    assert venda.empresa_codigo == 11495
    assert venda.valor_total == Decimal("150.25")
    assert item.grupo_codigo == 24554
    assert item.quantidade == Decimal("10.5")


def test_expense_and_cash_do_not_invent_missing_classification():
    despesa = WebPostoDespesa.model_validate(
        {
            "empresaCodigo": 5555,
            "planoContaGerencialCodigo": 7,
            "data": "2026-07-23T00:00:00",
            "valor": "89.90",
        }
    )
    caixa = WebPostoMovimentoCaixa.model_validate(
        {"caixaCodigo": 8, "empresaCodigo": 5555, "valor": "-20"}
    )

    assert despesa.despesa_codigo is None
    assert despesa.plano_conta_gerencial_codigo == 7
    assert despesa.centro_custo_codigo is None
    assert despesa.data_movimento is not None
    assert caixa.data_movimento is None
    assert caixa.valor == Decimal("-20")


@pytest.mark.parametrize(
    ("schema", "payload"),
    [
        (WebPostoVenda, {"valor": 10}),
        (WebPostoVendaItem, {"vendaCodigo": 1}),
        (WebPostoDespesa, {"valor": 10}),
        (WebPostoMovimentoCaixa, {"valor": 10}),
    ],
)
def test_transaction_contracts_reject_rows_without_identity(schema, payload):
    with pytest.raises(ValidationError):
        schema.model_validate(payload)


@pytest.mark.parametrize(
    ("endpoint", "schema"),
    [
        ("VENDA", WebPostoVenda),
        ("VENDA_ITEM", WebPostoVendaItem),
        ("CONSULTAR_DESPESAS_FINANCEIRO_REDE", WebPostoDespesa),
        ("CAIXA", WebPostoMovimentoCaixa),
    ],
)
def test_contracts_against_captured_webposto_evidence(endpoint, schema):
    evidence_dir = Path("etl/evidence/sprint_21a_r2_hotfix")
    files = [
        evidence_file
        for evidence_file in sorted(evidence_dir.glob("*.json"))
        if json.loads(evidence_file.read_text(encoding="utf-8")).get("endpoint") == endpoint
    ]

    assert len(files) == 2, f"Esperadas evidências de POSTO_VIP e CASA_CAIADA para {endpoint}"
    for evidence_file in files:
        evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
        assert evidence["success"] is True
        assert evidence["records_count"] > 0
        schema.model_validate(evidence["sample_payload"])
