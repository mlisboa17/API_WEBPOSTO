"""Motor de proposta de custo — fixtures ficticios, sem store fiscal real e sem rede."""

from __future__ import annotations

import importlib.util
import json
from decimal import Decimal
from pathlib import Path

import pytest

from src.operational.dfe import store
from src.operational.product_registration import dfe_cost_resolver as resolver
from src.operational.cost_update.current_cost_reader import CurrentProductCostReader
from src.operational.cost_update.decimal_utils import to_decimal
from src.operational.cost_update.evidence_resolver import CostEvidenceResolver
from src.operational.cost_update.ports import UnimplementedCostUpdateGateway, WRITES_NOT_IMPLEMENTED
from src.operational.cost_update.proposal_policy import CostUpdateProposalPolicy
from src.operational.cost_update.proposal_store import CostProposalStore
from src.operational.cost_update.schemas import CurrentProductState
from src.operational.cost_update.service import CostUpdateService, _proposal_hash

ROOT = Path(__file__).resolve().parents[2]
EAN = "7891000377130"


def _document(doc_id: str, issued_at: str, protocol: dict, recipient="02080237000155") -> dict:
    return {
        "id": doc_id,
        "company_code": 118508,
        "access_key_masked": "262607***1857",
        "document_type": "PROC_NFE",
        "issuer_cnpj": "60409075013998",
        "issuer_name": "Fornecedor Teste",
        "recipient_cnpj": recipient,
        "nNF": "1",
        "serie": "1",
        "issued_at": issued_at,
        "protocol": protocol,
    }


def _item(
    ean: str,
    *,
    v_prod="15.91",
    q_com=6.0,
    u_com="UNI",
    u_trib="UNI",
    q_trib=6.0,
    v_desc=None,
    v_frete=None,
    v_seg=None,
    v_outro=None,
    ipi_cst="51",
    v_ipi=None,
    v_icms_st=None,
) -> dict:
    return {
        "line_number": 1,
        "normalized_json": {
            "c_ean": ean,
            "c_ean_trib": ean,
            "x_prod": "PRODUTO TESTE",
            "ncm": "19053100",
            "cest": "1705300",
            "cfop": "5405",
            "u_com": u_com,
            "q_com": q_com,
            "u_trib": u_trib,
            "q_trib": q_trib,
            "v_prod": v_prod,
            "v_desc": v_desc,
            "v_frete": v_frete,
            "v_seg": v_seg,
            "v_outro": v_outro,
            "ipi": {"IPI.CST": ipi_cst, "IPI.vIPI": v_ipi},
            "icms": {"ICMS.vICMSST": v_icms_st},
        },
    }


@pytest.fixture
def fake_store(monkeypatch):
    state: dict = {
        "documents": [],
        "items": {},
        "totals": resolver.InvoiceTotals(produtos=Decimal("100")),
    }
    monkeypatch.setattr(store, "list_documents", lambda company_code=None: state["documents"])
    monkeypatch.setattr(store, "load_items", lambda doc_id: state["items"].get(doc_id, []))
    monkeypatch.setattr(resolver, "read_invoice_totals", lambda doc_id: state["totals"])
    return state


class FakeReader:
    def __init__(self, catalog, links) -> None:
        self.catalog = catalog
        self.links = links

    def get_catalog(self, key, cursor, page_size):
        return self.catalog

    def get_company_links(self, key, cursor, page_size):
        return self.links


def _current(**overrides) -> CurrentProductState:
    payload = dict(
        ok=True,
        empresa_codigo=118508,
        produto_codigo=2481511,
        ean_confirmado=True,
        ativo=True,
        custo_atual=Decimal("0"),
        preco_venda=Decimal("4.90"),
        ncm="19053100",
        cest="1705300",
        classification="OK",
    )
    payload.update(overrides)
    return CurrentProductState(**payload)


def test_decimal_rejects_float_bool():
    with pytest.raises(TypeError):
        to_decimal(True)
    assert to_decimal("2.6517") == Decimal("2.6517")


def test_formula_discount_freight_insurance_other_ipi_st(fake_store):
    totals = resolver.InvoiceTotals(
        produtos=Decimal("100"),
        frete=Decimal("10"),
        seguro=Decimal("2"),
        outras=Decimal("3"),
        desconto=Decimal("5"),
    )
    item = _item(EAN, v_prod="20", q_com=2, ipi_cst="50", v_ipi="1.00", v_icms_st="0.50")["normalized_json"]
    computed = resolver.compute_unit_cost(item, totals)
    assert computed["desconto_item"] == Decimal("1.000000")
    assert computed["frete_rateado"] == Decimal("2.000000")
    assert computed["seguro_rateado"] == Decimal("0.400000")
    assert computed["outras_rateadas"] == Decimal("0.600000")
    assert computed["ipi_nao_recuperavel"] == Decimal("1.00")
    assert computed["icms_st_cobrado"] == Decimal("0.50")
    assert isinstance(computed["preco_custo"], Decimal)


def test_ipi_non_taxed_cst_is_not_cost():
    item = _item(EAN, ipi_cst="51", v_ipi="9.99")["normalized_json"]
    assert resolver.item_ipi_non_recoverable(item) == Decimal("0")


def test_qtrib_atomic_unit_is_used():
    item = _item(EAN, u_com="CX", q_com=1, u_trib="UNI", q_trib=12)["normalized_json"]
    qty, origin = resolver.resolve_sale_unit_quantity(item)
    assert qty == Decimal("12")
    assert origin == resolver.QUANTITY_FROM_TAXABLE


def test_indeterminate_packaging_blocks_unit():
    item = _item(EAN, u_com="CX", q_com=1, u_trib="CX", q_trib=1)["normalized_json"]
    qty, origin = resolver.resolve_sale_unit_quantity(item)
    assert origin is None
    assert qty == Decimal("0")


def test_latest_authorized_nfe_wins(fake_store):
    fake_store["documents"] = [
        _document("dfe_doc_old", "2026-01-01", {"cStat": "100", "cancelled": False}),
        _document("dfe_doc_new", "2026-08-01", {"cStat": "100", "cancelled": False}),
    ]
    fake_store["items"] = {
        "dfe_doc_old": [_item(EAN, v_prod="10", q_com=1)],
        "dfe_doc_new": [_item(EAN, v_prod="20", q_com=1)],
    }
    evidence = CostEvidenceResolver().resolve(EAN, use_index=True)
    assert evidence.resolved
    assert evidence.document_id == "dfe_doc_new"
    assert evidence.preco_custo == Decimal("20.0000")


def test_cancelled_and_wrong_recipient_are_blocked(fake_store):
    fake_store["documents"] = [
        _document("dfe_doc_c", "2026-08-01", {"cStat": "100", "cancelled": True}),
        _document("dfe_doc_r", "2026-08-02", {"cStat": "100", "cancelled": False}, recipient="11495000000100"),
    ]
    fake_store["items"] = {
        "dfe_doc_c": [_item(EAN)],
        "dfe_doc_r": [_item("7891000000999")],
    }
    missing = CostEvidenceResolver().resolve(EAN, use_index=True)
    assert missing.status == resolver.STATUS_NOT_FOUND
    wrong = CostEvidenceResolver().resolve("7891000000999", use_index=True)
    assert wrong.status == "BLOCKED_RECIPIENT_MISMATCH"


def test_policy_classifications(fake_store):
    fake_store["documents"] = [_document("dfe_doc_a", "2026-08-01", {"cStat": "100", "cancelled": False})]
    fake_store["items"]["dfe_doc_a"] = [_item(EAN, v_prod="2.65", q_com=1)]
    evidence = CostEvidenceResolver().resolve(EAN)
    policy = CostUpdateProposalPolicy()
    proposed = policy.classify(current=_current(custo_atual=Decimal("0")), evidence=evidence, expected_ean=EAN)
    assert proposed["status"] == "PROPOSED"
    same = policy.classify(
        current=_current(custo_atual=Decimal("2.6500")),
        evidence=evidence,
        expected_ean=EAN,
    )
    assert same["status"] == "NO_CHANGE"
    review = policy.classify(
        current=_current(custo_atual=Decimal("1.00"), preco_venda=Decimal("2.00")),
        evidence=evidence,
        expected_ean=EAN,
    )
    assert review["status"] == "REVIEW_REQUIRED"
    blocked = policy.classify(
        current=_current(ok=False, ean_confirmado=False, classification="BLOCKED_EAN_MISMATCH"),
        evidence=evidence,
        expected_ean=EAN,
    )
    assert blocked["status"] == "BLOCKED"
    other = policy.classify(
        current=_current(empresa_codigo=11495, classification="BLOCKED_WRONG_COMPANY"),
        evidence=evidence,
        expected_ean=EAN,
    )
    assert other["status"] == "BLOCKED"


def test_dfe_not_found(fake_store):
    evidence = CostEvidenceResolver().resolve("0000000000000")
    decision = CostUpdateProposalPolicy().classify(
        current=_current(),
        evidence=evidence,
        expected_ean="0000000000000",
    )
    assert decision["status"] == "DFE_NOT_FOUND"


def test_reader_detects_wrong_company_and_ambiguous():
    reader = CurrentProductCostReader(
        FakeReader(
            [{"produtoCodigo": 10, "produtoCodigoBarra": [{"codigoBarra": EAN}], "ncm": "19053100"}],
            [{"produtoCodigo": 10, "empresaCodigo": 11495, "precoCusto": 1, "precoVenda": 2, "ativo": True}],
        )
    )
    state = reader.read("k", 10, EAN)
    assert state.classification == "BLOCKED_WRONG_COMPANY"
    amb = CurrentProductCostReader(FakeReader([], [])).read("k", 10, EAN)
    assert amb.ambiguous is True


def test_proposal_hash_and_store_idempotency(tmp_path, fake_store):
    fake_store["documents"] = [_document("dfe_doc_a", "2026-08-01", {"cStat": "100", "cancelled": False})]
    fake_store["items"]["dfe_doc_a"] = [_item(EAN, v_prod="2.65", q_com=1)]
    pending = tmp_path / "pending.json"
    pending.write_text(
        json.dumps(
            {
                EAN: {
                    "ean": EAN,
                    "descricao": "TESTE",
                    "produtoCodigo": 10,
                    "precoCustoCadastrado": 0,
                    "precoVenda": 4.9,
                }
            }
        ),
        encoding="utf-8",
    )
    reader = CurrentProductCostReader(
        FakeReader(
            [
                {
                    "produtoCodigo": 10,
                    "nome": "TESTE",
                    "ncm": "19053100",
                    "cest": "1705300",
                    "produtoCodigoBarra": [{"codigoBarra": EAN}],
                }
            ],
            [{"produtoCodigo": 10, "empresaCodigo": 118508, "precoCusto": 0, "precoVenda": 4.9, "ativo": True}],
        )
    )
    service = CostUpdateService(
        tmp_path / "out",
        reader=reader,
        pending_path=pending,
        price_review_path=tmp_path / "missing.json",
        checkpoint_path=tmp_path / "missing.json",
        accountant_path=tmp_path / "missing.json",
    )
    first = service.propose("fake-key")
    second = service.propose("fake-key")
    assert first["counts"]["PROPOSED"] == 1
    assert second["api_writes"] == 0
    store = CostProposalStore(tmp_path / "out")
    index = store.load_index()
    assert len(index["by_ean"][EAN]) == 1
    first_hash = index["by_ean"][EAN][0]
    changed = _proposal_hash(118508, 10, EAN, Decimal("1"), Decimal("2.65"), {"document_id": "x"})
    assert changed != first_hash


def test_gateway_has_no_write_method_implementation():
    with pytest.raises(RuntimeError, match=WRITES_NOT_IMPLEMENTED):
        UnimplementedCostUpdateGateway().update_cost(None)


def test_increase_and_decrease_thresholds(fake_store):
    fake_store["documents"] = [_document("dfe_doc_a", "2026-08-01", {"cStat": "100", "cancelled": False})]
    fake_store["items"]["dfe_doc_a"] = [_item(EAN, v_prod="2.65", q_com=1)]
    evidence = CostEvidenceResolver().resolve(EAN)
    policy = CostUpdateProposalPolicy()
    increase = policy.classify(
        current=_current(custo_atual=Decimal("1.00"), preco_venda=Decimal("9.90")),
        evidence=evidence,
        expected_ean=EAN,
    )
    assert increase["status"] == "REVIEW_REQUIRED"
    assert any("aumento" in risk for risk in increase["riscos"])
    decrease = policy.classify(
        current=_current(custo_atual=Decimal("10.00"), preco_venda=Decimal("9.90")),
        evidence=evidence,
        expected_ean=EAN,
    )
    assert decrease["status"] == "REVIEW_REQUIRED"
    modest = policy.classify(
        current=_current(custo_atual=Decimal("2.40"), preco_venda=Decimal("4.90")),
        evidence=evidence,
        expected_ean=EAN,
    )
    assert modest["status"] == "PROPOSED"


def test_negative_margin_and_tolerance(fake_store):
    fake_store["documents"] = [_document("dfe_doc_a", "2026-08-01", {"cStat": "100", "cancelled": False})]
    fake_store["items"]["dfe_doc_a"] = [_item(EAN, v_prod="5.00", q_com=1)]
    evidence = CostEvidenceResolver().resolve(EAN)
    policy = CostUpdateProposalPolicy(pct_tolerance=Decimal("0.10"))
    decision = policy.classify(
        current=_current(custo_atual=Decimal("1.00"), preco_venda=Decimal("4.00")),
        evidence=evidence,
        expected_ean=EAN,
    )
    assert decision["status"] == "REVIEW_REQUIRED"
    assert any("margem" in risk for risk in decision["riscos"])
    close = policy.classify(
        current=_current(custo_atual=Decimal("5.00"), preco_venda=Decimal("9.90")),
        evidence=evidence,
        expected_ean=EAN,
    )
    assert close["status"] == "NO_CHANGE"


def test_cli_execute_refused(monkeypatch):
    path = ROOT / "scripts" / "cost_update_118508.py"
    spec = importlib.util.spec_from_file_location("cost_update_cli", path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(cli.sys, "argv", ["cost_update_118508.py", "--execute", "status"])
    assert cli.main() == 5
