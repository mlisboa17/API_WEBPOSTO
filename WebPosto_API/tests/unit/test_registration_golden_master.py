"""Golden master sanitizado: decisao fiscal, body, hash e verificacao."""

from __future__ import annotations

import json
from pathlib import Path

from src.operational.product_registration.dfe_cost_resolver import is_atomic_unit
from src.operational.product_registration.engine_schemas import (
    ProductRegistrationRequest,
    RiskAuthorization,
)
from src.operational.product_registration.final_wave import classify_final_duplicate
from src.operational.product_registration.policies.fiscal_policy import FiscalPolicy
from src.operational.product_registration.registration_body import RegistrationBodyBuilder

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "product_registration" / "golden" / "cases.json"


def _cases() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]


def _request(case: dict) -> ProductRegistrationRequest:
    return ProductRegistrationRequest(
        empresa=118508,
        centro=24886,
        ean=case["ean"],
        descricao=case["descricao"],
        preco_venda=case["preco_venda"],
        ncm=case["ncm"],
        cest=case.get("cest"),
        custo=case["custo"],
        cost_source="DFE" if case["custo"] else "PENDING_DFE",
        cost_status="RESOLVED" if case["custo"] else "PENDING",
        authorization=RiskAuthorization(accept_fiscal_risk=True, allow_pending_dfe_cost=True),
        perfil_fiscal={
            "cfop_entrada": "1.102",
            "cfop_saida": "5.405" if case["entry"] == "ST_COMPROVADA" else "5.102",
            "tributacao_monofasica": 0,
            "tributo_icms": {"cstSaida": "060" if case["entry"] == "ST_COMPROVADA" else "000"},
            "tributo_pis_cofins": {"cstPisSaida": "01"},
        },
    )


def test_golden_fiscal_decisions_differ_for_st_and_cst00():
    fiscal = FiscalPolicy()
    cases = {item["id"]: item for item in _cases() if "entry" in item}
    st = fiscal.evaluate_entry_classification(cases["bono_st"]["entry"])
    taxed = fiscal.evaluate_entry_classification(cases["cst00_taxed"]["entry"])
    assert st.decision == "ST_COMPROVADA"
    assert taxed.decision == "SEM_ST_COMPROVADA"
    assert st.decision != taxed.decision


def test_golden_bodies_and_hashes_are_stable():
    builder = RegistrationBodyBuilder()
    hashes = {}
    for case in _cases():
        if "ean" not in case:
            continue
        body = builder.build(_request(case))
        assert "empresaCodigo" not in body
        if case["id"] == "no_cest":
            assert "codigoCest" not in body
        hashes[case["id"]] = builder.hash(body)
        assert hashes[case["id"]] == builder.hash(body)
    assert hashes["bono_st"] != hashes["cst00_taxed"]
    assert hashes["no_cest"] != hashes["bono_st"]


def test_golden_duplicate_and_variant():
    cases = {item["id"]: item for item in _cases()}
    assert (
        classify_final_duplicate(cases["duplicate"]["descricao"], cases["duplicate"]["existing"])[0]
        == cases["duplicate"]["expected"]
    )
    assert (
        classify_final_duplicate(
            cases["legitimate_variant"]["descricao"], cases["legitimate_variant"]["existing"]
        )[0]
        == cases["legitimate_variant"]["expected"]
    )


def test_golden_packaging_conversion():
    cases = {item["id"]: item for item in _cases()}
    assert is_atomic_unit(cases["convertible_pack"]["u_trib"]) is True
    assert is_atomic_unit(cases["indeterminate_pack"]["u_trib"]) is False
