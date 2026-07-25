import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from src.domain.departmental_facts import DepartmentalFactKind, DepartmentalFactStatus
from src.services.departmental_fact_builder import DepartmentalFactBuilder


LINEAGE_TIME = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)


def build(kind, rows, product_groups=None):
    return DepartmentalFactBuilder.build(
        kind,
        rows,
        endpoint="/INTEGRACAO/VENDA_ITEM",
        logical_token="POSTO_VIP",
        product_groups=product_groups,
        period_start="2026-07-23",
        period_end="2026-07-23",
        collected_at=LINEAGE_TIME,
    )


def test_classifies_by_confirmed_group_and_preserves_lineage():
    batch = build(
        DepartmentalFactKind.SALE,
        [
            {
                "empresaCodigo": 11495,
                "vendaItemCodigo": 1,
                "produtoCodigo": 10,
                "totalVenda": "100.25",
                "dataMovimento": "2026-07-23T10:00:00",
            }
        ],
        {10: 24554},
    )

    assert len(batch.facts) == 1
    fact = batch.facts[0]
    assert fact.departamento == "combustiveis"
    assert fact.status == DepartmentalFactStatus.CLASSIFIED
    assert fact.lineage.endpoint == "/INTEGRACAO/VENDA_ITEM"
    assert fact.lineage.logical_token == "POSTO_VIP"
    assert batch.reconciliation_difference == Decimal("0")


def test_ambiguous_and_missing_groups_are_explicitly_quarantined():
    batch = build(
        DepartmentalFactKind.SALE,
        [
            {"empresaCodigo": 5555, "vendaItemCodigo": 1, "grupoCodigo": 26039, "totalVenda": 10},
            {"empresaCodigo": 5555, "vendaItemCodigo": 2, "totalVenda": 20},
        ],
    )

    assert not batch.facts
    assert [fact.quarantine_reason for fact in batch.quarantine] == [
        "GRUPO_AMBIGUO:DIVERSOS",
        "SEM_GRUPO",
    ]
    assert batch.source_total == batch.reconciled_total == Decimal("30")


def test_rejects_unlicensed_company_and_removes_duplicate_source_identity():
    row = {"empresaCodigo": 74014, "vendaItemCodigo": 7, "grupoCodigo": 24555, "totalVenda": 50}
    batch = build(
        DepartmentalFactKind.SALE,
        [row, dict(row), {"empresaCodigo": 5256, "vendaItemCodigo": 8, "totalVenda": 999}],
    )

    assert len(batch.facts) == 1
    assert batch.duplicates_removed == 1
    assert batch.rejected_unlicensed == 1
    assert batch.source_total == Decimal("50")


def test_builds_cost_expense_stock_and_cash_fact_values():
    cases = [
        (DepartmentalFactKind.COST, {"totalCusto": "12.50"}),
        (DepartmentalFactKind.EXPENSE, {"valor": "13.50"}),
        (DepartmentalFactKind.STOCK, {"saldoEstoque": "14.50"}),
        (DepartmentalFactKind.CASH, {"apurado": "15.50"}),
    ]
    for index, (kind, value_field) in enumerate(cases, start=1):
        row = {
            "empresaCodigo": 11495,
            "codigo": index,
            "grupoCodigo": 24554,
            **value_field,
        }
        batch = build(kind, [row])
        assert batch.facts[0].kind == kind
        assert batch.reconciliation_difference == Decimal("0")


def test_stock_identity_includes_product_inside_same_stock_location():
    batch = build(
        DepartmentalFactKind.STOCK,
        [
            {
                "empresaCodigo": 11495,
                "estoqueCodigo": 1,
                "produtoCodigo": 10,
                "grupoCodigo": 24554,
                "saldoEstoque": 5,
            },
            {
                "empresaCodigo": 11495,
                "estoqueCodigo": 1,
                "produtoCodigo": 20,
                "grupoCodigo": 24554,
                "saldoEstoque": 7,
            },
        ],
    )

    assert len(batch.facts) == 2
    assert batch.duplicates_removed == 0
    assert batch.identity_conflicts == 0
    assert batch.source_total == Decimal("12")


def test_conflicting_rows_with_same_business_identity_are_not_silently_deduplicated():
    base = {
        "empresaCodigo": 11495,
        "vendaCodigo": 1,
        "vendaItemCodigo": 2,
        "grupoCodigo": 24554,
    }
    batch = build(
        DepartmentalFactKind.SALE,
        [{**base, "totalVenda": 10}, {**base, "totalVenda": 11}],
    )

    assert len(batch.facts) == 1
    assert batch.duplicates_removed == 0
    assert batch.identity_conflicts == 1


def test_captured_rows_are_always_classified_quarantined_or_rejected():
    evidence_dir = Path("etl/evidence/sprint_21a_r2_hotfix")
    endpoint_kinds = {
        "VENDA_ITEM": DepartmentalFactKind.SALE,
        "CONSULTAR_DESPESAS_FINANCEIRO_REDE": DepartmentalFactKind.EXPENSE,
        "CAIXA": DepartmentalFactKind.CASH,
    }

    checked = 0
    for evidence_file in evidence_dir.glob("*.json"):
        evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
        kind = endpoint_kinds.get(evidence.get("endpoint"))
        sample = evidence.get("sample_payload")
        if kind is None or not evidence.get("success") or not isinstance(sample, dict):
            continue
        batch = DepartmentalFactBuilder.build(
            kind,
            [sample],
            endpoint=evidence["path"],
            logical_token=evidence["tenant"],
            collected_at=LINEAGE_TIME,
        )
        assert batch.reconciliation_difference == Decimal("0")
        assert len(batch.facts) + len(batch.quarantine) + batch.rejected_unlicensed == 1
        assert all(fact.empresa_codigo in {11495, 5555, 74014} for fact in batch.facts)
        checked += 1

    assert checked == 6
