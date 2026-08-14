"""Politica de custo pelo DF-e e trava de POST unico do piloto (sem rede, sem escrita)."""

from __future__ import annotations

import importlib.util
import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from src.operational.dfe import store
from src.operational.product_registration import dfe_cost_resolver as resolver
from src.operational.product_registration.tax_table_matcher import (
    MATCH_AMBIGUOUS,
    MATCH_NOT_FOUND,
    MATCH_UNIQUE,
    IcmsRow,
    match_icms,
)

ROOT = Path(__file__).resolve().parents[2]
EAN = "7891000377130"

AUTHORIZED_PROTOCOL = {"cStat": "100", "nProt": "1", "cancelled": False}
CANCELLED_PROTOCOL = {"cStat": "100", "nProt": "1", "cancelled": True}
DENIED_PROTOCOL = {"cStat": "302", "nProt": None, "cancelled": False}


def _document(doc_id: str, issued_at: str, protocol: dict) -> dict:
    return {
        "id": doc_id,
        "company_code": 118508,
        "access_key": "26" + doc_id.replace("d", "1").ljust(42, "0")[:42],
        "access_key_masked": "262607***1857",
        "document_type": "PROC_NFE",
        "issuer_cnpj": "60409075013998",
        "issuer_name": "Fornecedor Teste",
        "recipient_cnpj": "02080237000155",
        "nNF": "1",
        "serie": "1",
        "issued_at": issued_at,
        "protocol": protocol,
    }


def _item(ean: str, *, v_prod="15.91", q_com=6.0, x_prod="NEGRESCO Biscoito", ipi_cst="51") -> dict:
    return {
        "line_number": 8,
        "normalized_json": {
            "c_ean": ean,
            "c_ean_trib": ean,
            "x_prod": x_prod,
            "ncm": "19053100",
            "cest": "1705300",
            "cfop": "5405",
            "u_com": "UNI",
            "q_com": q_com,
            "v_prod": v_prod,
            "v_desc": None,
            "v_frete": None,
            "ipi": {"IPI.CST": ipi_cst},
        },
    }


@pytest.fixture
def fake_store(monkeypatch):
    """Store DF-e injetavel, com totais lidos sem tocar em XML real."""
    state: dict = {"documents": [], "items": {}, "totals": resolver.InvoiceTotals(produtos=Decimal("391.76"))}

    monkeypatch.setattr(store, "list_documents", lambda company_code=None: state["documents"])
    monkeypatch.setattr(store, "load_items", lambda doc_id: state["items"].get(doc_id, []))
    monkeypatch.setattr(resolver, "read_invoice_totals", lambda doc_id: state["totals"])
    return state


# --- Custo obrigatorio pelo DF-e ---------------------------------------------


def test_cost_is_resolved_from_authorized_invoice(fake_store):
    fake_store["documents"] = [_document("doc_a", "2026-07-30T13:35:47-03:00", AUTHORIZED_PROTOCOL)]
    fake_store["items"] = {"doc_a": [_item(EAN)]}

    evidence = resolver.find_cost_evidence(EAN, 118508)

    assert evidence.status == resolver.STATUS_RESOLVED
    assert evidence.match_type == resolver.MATCH_EXACT_EAN
    assert evidence.preco_custo == Decimal("2.6517")
    assert evidence.resolved


def test_missing_invoice_blocks_product(fake_store):
    evidence = resolver.find_cost_evidence(EAN, 118508)

    assert evidence.status == resolver.STATUS_NOT_FOUND
    assert evidence.preco_custo is None
    assert not evidence.resolved


def test_required_cost_raises_when_not_found(fake_store):
    with pytest.raises(resolver.DfeCostError, match="BLOCKED_DFE_COST_NOT_FOUND"):
        resolver.resolve_required_cost(EAN, 118508)


def test_cancelled_invoice_cannot_be_used(fake_store):
    fake_store["documents"] = [_document("doc_c", "2026-07-30T00:00:00-03:00", CANCELLED_PROTOCOL)]
    fake_store["items"] = {"doc_c": [_item(EAN)]}

    evidence = resolver.find_cost_evidence(EAN, 118508)

    assert evidence.status == resolver.STATUS_NOT_FOUND
    assert evidence.notas_descartadas[0]["reason"] == "CANCELADA"


def test_unauthorized_invoice_cannot_be_used(fake_store):
    fake_store["documents"] = [_document("doc_d", "2026-07-30T00:00:00-03:00", DENIED_PROTOCOL)]
    fake_store["items"] = {"doc_d": [_item(EAN)]}

    evidence = resolver.find_cost_evidence(EAN, 118508)

    assert evidence.status == resolver.STATUS_NOT_FOUND
    assert "NAO_AUTORIZADA" in evidence.notas_descartadas[0]["reason"]


def test_most_recent_authorized_invoice_wins(fake_store):
    fake_store["documents"] = [
        _document("doc_old", "2026-05-01T00:00:00-03:00", AUTHORIZED_PROTOCOL),
        _document("doc_new", "2026-07-30T00:00:00-03:00", AUTHORIZED_PROTOCOL),
    ]
    fake_store["items"] = {
        "doc_old": [_item(EAN, v_prod="12.00", q_com=6.0)],
        "doc_new": [_item(EAN, v_prod="15.91", q_com=6.0)],
    }

    evidence = resolver.find_cost_evidence(EAN, 118508)

    assert evidence.document_id == "doc_new"
    assert evidence.preco_custo == Decimal("2.6517")


def test_description_only_match_never_auto_approves(fake_store):
    fake_store["documents"] = [_document("doc_e", "2026-07-30T00:00:00-03:00", AUTHORIZED_PROTOCOL)]
    fake_store["items"] = {"doc_e": [_item("9999999999999", x_prod="NEGRESCO Biscoito")]}

    evidence = resolver.find_cost_evidence(EAN, 118508, description="NEGRESCO Biscoito")

    assert evidence.status == resolver.STATUS_REVIEW_DESCRIPTION_ONLY
    assert evidence.match_type == resolver.MATCH_DESCRIPTION
    assert not evidence.resolved

    with pytest.raises(resolver.DfeCostError):
        resolver.resolve_required_cost(EAN, 118508)


# --- Calculo do custo ---------------------------------------------------------


def test_cost_calculation_applies_discount_and_allocations():
    totals = resolver.InvoiceTotals(
        produtos=Decimal("100.00"),
        frete=Decimal("10.00"),
        seguro=Decimal("5.00"),
        outras=Decimal("2.00"),
        desconto=Decimal("4.00"),
    )
    item = {"v_prod": "50.00", "q_com": 10, "ipi": {"IPI.CST": "51"}}

    result = resolver.compute_unit_cost(item, totals)

    # Item representa metade da nota: recebe metade de cada despesa e do desconto.
    assert result["frete_rateado"] == Decimal("5.000000")
    assert result["seguro_rateado"] == Decimal("2.500000")
    assert result["outras_rateadas"] == Decimal("1.000000")
    assert result["desconto_item"] == Decimal("2.000000")
    assert result["valor_liquido_item"] == Decimal("56.500000")
    assert result["preco_custo"] == Decimal("5.6500")


def test_item_level_expenses_take_precedence_over_allocation():
    totals = resolver.InvoiceTotals(produtos=Decimal("100.00"), frete=Decimal("10.00"))
    item = {"v_prod": "50.00", "q_com": 5, "v_frete": "1.00", "ipi": {"IPI.CST": "51"}}

    result = resolver.compute_unit_cost(item, totals)

    assert result["frete_rateado"] == Decimal("1.00")
    assert result["preco_custo"] == Decimal("10.2000")


def test_non_recoverable_ipi_enters_cost():
    totals = resolver.InvoiceTotals(produtos=Decimal("50.00"))
    item = {"v_prod": "50.00", "q_com": 10, "ipi": {"IPI.CST": "50", "IPI.vIPI": "5.00"}}

    result = resolver.compute_unit_cost(item, totals)

    assert result["ipi_nao_recuperavel"] == Decimal("5.00")
    assert result["preco_custo"] == Decimal("5.5000")


def test_non_taxed_ipi_does_not_enter_cost():
    item = {"v_prod": "50.00", "q_com": 10, "ipi": {"IPI.CST": "51", "IPI.vIPI": "5.00"}}

    assert resolver.item_ipi_non_recoverable(item) == Decimal("0")


def test_zero_quantity_is_rejected():
    with pytest.raises(resolver.DfeCostError, match="Quantidade comercial invalida"):
        resolver.compute_unit_cost({"v_prod": "10", "q_com": 0}, resolver.InvoiceTotals())


def test_negresco_cost_matches_real_store_evidence():
    """Reproduz o custo com o store real do projeto, sem rede."""
    evidence = resolver.find_cost_evidence(EAN, 118508)

    assert evidence.resolved
    assert evidence.preco_custo == Decimal("2.6517")
    assert evidence.protocolo_cstat == "100"
    assert evidence.cancelada is False
    assert evidence.destinatario_cnpj == "02080237000155"
    assert evidence.item_ncm == "19053100"
    assert evidence.item_cest == "1705300"


# --- ICMS-ST cobrado na entrada -----------------------------------------------


def test_icms_st_charged_on_entry_composes_cost():
    """Em CST 10 o fornecedor cobra a ST, que não é recuperável e é custo."""
    item = {
        "v_prod": "50.76",
        "q_com": 9.0,
        "icms": {"ICMS.CST": "10", "ICMS.vICMS": "10.41", "ICMS.vICMSST": "6.73"},
    }
    computed = resolver.compute_unit_cost(item, resolver.InvoiceTotals(produtos=Decimal("50.76")))

    assert computed["icms_st_cobrado"] == Decimal("6.73")
    assert computed["preco_custo"] == Decimal("6.3878")


def test_icms_st_retained_earlier_does_not_change_cost():
    """Em CST 60 a ST foi retida antes na cadeia: nada é cobrado nesta nota."""
    item = {
        "v_prod": "50.50",
        "q_com": 25.0,
        "icms": {"ICMS.CST": "60", "ICMS.vICMSSTRet": "0.00"},
    }
    computed = resolver.compute_unit_cost(item, resolver.InvoiceTotals(produtos=Decimal("50.50")))

    assert computed["icms_st_cobrado"] == Decimal("0")
    assert computed["preco_custo"] == Decimal("2.0200")


def test_icms_own_operation_is_not_deducted_from_cost():
    """Mercadoria em ST sai sem débito: o ICMS próprio da entrada não é creditável."""
    item = {
        "v_prod": "100.00",
        "q_com": 10.0,
        "icms": {"ICMS.CST": "10", "ICMS.vICMS": "20.50", "ICMS.vICMSST": "0.00"},
    }
    computed = resolver.compute_unit_cost(item, resolver.InvoiceTotals(produtos=Decimal("100.00")))

    assert computed["preco_custo"] == Decimal("10.0000")


# --- Normalização de unidade --------------------------------------------------


def test_atomic_units_are_recognized():
    for unit in ("UN", "UNI", "UN1", "und", " unidade ", "PC"):
        assert resolver.is_atomic_unit(unit), unit


def test_grouping_units_are_not_atomic():
    for unit in ("CX", "DP", "FD", "PCT", "KG", "L", "CT", None, ""):
        assert not resolver.is_atomic_unit(unit), unit


def test_box_unit_blocks_cost_resolution(fake_store):
    """Caixa a R$ 83,20 com 6 unidades não pode virar custo unitário de R$ 83,20."""
    fake_store["documents"] = [_document("doc_cx", "2026-08-01T00:00:00-03:00", AUTHORIZED_PROTOCOL)]
    item = _item(EAN, v_prod="83.20", q_com=1.0)
    item["normalized_json"]["u_com"] = "CX"
    item["normalized_json"]["u_trib"] = "KG"
    item["normalized_json"]["q_trib"] = 3.6
    fake_store["items"] = {"doc_cx": [item]}
    fake_store["totals"] = resolver.InvoiceTotals(produtos=Decimal("83.20"))

    evidence = resolver.find_cost_evidence(EAN, 118508)

    assert evidence.status == resolver.STATUS_REVIEW_UNIT
    assert evidence.unidade_atomica is False
    assert not evidence.resolved
    assert "fator de conversão" in evidence.reason

    with pytest.raises(resolver.DfeCostError):
        resolver.resolve_required_cost(EAN, 118508)


def test_atomic_unit_keeps_cost_resolved(fake_store):
    fake_store["documents"] = [_document("doc_un", "2026-08-01T00:00:00-03:00", AUTHORIZED_PROTOCOL)]
    item = _item(EAN)
    item["normalized_json"]["u_com"] = "UNI"
    fake_store["items"] = {"doc_un": [item]}

    evidence = resolver.find_cost_evidence(EAN, 118508)

    assert evidence.status == resolver.STATUS_RESOLVED
    assert evidence.unidade_atomica is True
    assert evidence.resolved


def test_index_and_direct_search_agree(fake_store):
    """O índice em lote deve produzir a mesma evidência da busca individual."""
    fake_store["documents"] = [_document("doc_a", "2026-07-30T13:35:47-03:00", AUTHORIZED_PROTOCOL)]
    fake_store["items"] = {"doc_a": [_item(EAN)]}

    direct = resolver.find_cost_evidence(EAN, 118508)
    indexed = resolver.cost_from_index(EAN, resolver.build_authorized_index(118508))

    assert indexed.status == direct.status
    assert indexed.preco_custo == direct.preco_custo
    assert indexed.document_id == direct.document_id


def test_index_returns_not_found_for_unknown_ean():
    evidence = resolver.cost_from_index("0000000000000", {})

    assert evidence.status == resolver.STATUS_NOT_FOUND
    assert not evidence.resolved


def test_evidence_dict_does_not_expose_full_access_key(fake_store):
    fake_store["documents"] = [_document("doc_a", "2026-07-30T13:35:47-03:00", AUTHORIZED_PROTOCOL)]
    fake_store["items"] = {"doc_a": [_item(EAN)]}
    full_access_key = fake_store["documents"][0]["access_key"]

    evidence = resolver.find_cost_evidence(EAN, 118508)
    payload = json.dumps(resolver.evidence_to_dict(evidence))

    assert "access_key_masked" in payload
    assert full_access_key not in payload


# --- Tabela ICMS: ausencia de CSOSN nao e zero -------------------------------


def _icms_row(ref: str, csosn: str | None, fcp: float | None) -> IcmsRow:
    return IcmsRow(
        referencia=ref,
        descricao="SAI CST 060 ICMS 0 | ENT CST 060 ICMS 0",
        cst_entrada="060",
        cst_saida="060",
        icms_entrada=0.0,
        icms_saida=0.0,
        csosn_entrada=csosn,
        csosn_saida=csosn,
        fcp=fcp,
        mva=None,
    )


def _match(rows):
    return match_icms(
        rows,
        cst_entrada="060",
        cst_saida="060",
        icms_entrada=0.0,
        icms_saida=0.0,
        csosn_entrada="0",
        csosn_saida="0",
        fcp=0.0,
    )


def test_icms_row_without_declared_csosn_is_not_treated_as_zero():
    """Vazio diferente de "0" foi a causa do RET=3; nao repetir a confusao."""
    status, matches = _match([_icms_row("A", None, None)])

    assert status == MATCH_NOT_FOUND
    assert matches == [_icms_row("A", None, None)]


def test_icms_match_is_unique_when_csosn_zero_declared():
    rows = [_icms_row("A", None, None), _icms_row("B", "0", 0.0), _icms_row("C", "900", 0.0)]

    status, matches = _match(rows)

    assert status == MATCH_UNIQUE
    assert matches[0].referencia == "B"


def test_icms_match_reports_ambiguity_when_two_rows_are_identical():
    status, matches = _match([_icms_row("B", "0", 0.0), _icms_row("D", "0", 0.0)])

    assert status == MATCH_AMBIGUOUS
    assert len(matches) == 2


# --- Executor: custo manual e recusado ---------------------------------------


def _load_executor():
    path = ROOT / "scripts" / "execute_ready_products_118508.py"
    spec = importlib.util.spec_from_file_location("executor_cost_gate", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _product_with_cost(**overrides) -> dict:
    product = {
        "ean": EAN,
        "descricao": "BISCOITO NEGRESCO RECHEADO CHOCOLATE 90G",
        "preco_venda": 4.9,
        "grupo_codigo_api": 55446,
        "tax_basis_status": "APPROVED",
        "ncm": "19053100",
        "cest": "1705300",
        "tributoIcms": {"cstSaida": "060"},
        "tributoPisCofins": {"cstPisSaida": "01"},
        "cost_source": "DFE",
        "dfe_cost_evidence": {"numero": "2400289", "precoCusto": 2.6517},
        "preco_custo": 2.6517,
        "body_preparado": {"precoCompra": 2.6517, "precoCusto": 2.6517},
    }
    product.update(overrides)
    return product


def test_executor_rejects_cost_without_dfe_source():
    executor = _load_executor()

    with pytest.raises(ValueError, match="Custo sem origem DF-e"):
        executor.ProductRegistrationExecutor.rebuild_body(None, _product_with_cost(cost_source="MANUAL"))


def test_executor_rejects_cost_without_evidence():
    executor = _load_executor()

    with pytest.raises(ValueError, match="Evidência DF-e ausente"):
        executor.ProductRegistrationExecutor.rebuild_body(
            None, _product_with_cost(dfe_cost_evidence=None)
        )


def test_executor_rejects_zero_cost():
    executor = _load_executor()
    product = _product_with_cost(preco_custo=0)
    product["body_preparado"]["precoCusto"] = 0

    with pytest.raises(ValueError, match="Preço de custo inválido"):
        executor.ProductRegistrationExecutor.rebuild_body(None, product)


def test_executor_accepts_dfe_backed_cost():
    executor = _load_executor()

    body = executor.ProductRegistrationExecutor.rebuild_body(None, _product_with_cost())

    assert body["precoCusto"] == 2.6517
    assert body["codigoExterno"] == EAN


# --- Piloto: apenas um POST ---------------------------------------------------


def _load_pilot():
    path = ROOT / "scripts" / "execute_negresco_pilot_118508.py"
    spec = importlib.util.spec_from_file_location("pilot_single_post", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_pilot_allows_post_when_no_lock(tmp_path, monkeypatch):
    pilot = _load_pilot()
    monkeypatch.setattr(pilot, "PILOT_LOCK", tmp_path / "lock.json")

    pilot.assert_single_post_allowed()


def test_pilot_refuses_second_post(tmp_path, monkeypatch):
    pilot = _load_pilot()
    lock = tmp_path / "lock.json"
    lock.write_text(json.dumps({"sentAt": "2026-08-14T00:00:00Z", "bodyHash": "abc", "postCount": 1}))
    monkeypatch.setattr(pilot, "PILOT_LOCK", lock)

    with pytest.raises(pilot.PilotBlocked, match="Segunda tentativa recusada"):
        pilot.assert_single_post_allowed()


def test_pilot_sanitizes_url():
    pilot = _load_pilot()

    sanitized = pilot.sanitize("https://host/INTEGRACAO/INCLUIR_PRODUTO?CHAVE=segredo123")

    assert "segredo123" not in sanitized
    assert sanitized.endswith("CHAVE=***REDACTED***")
