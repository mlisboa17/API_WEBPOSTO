"""Garante que a base de ICMS venha de evidência, nunca do NCM.

O erro que estes testes travam: aplicar a base do BONO/NEGRESCO (CST 060, mercadoria
substituída) a qualquer alimento do capítulo 19, inclusive a produtos que entraram com
CST 00 e ICMS destacado.
"""

from __future__ import annotations

import pytest

from src.operational.product_registration.fiscal_resolver import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_NONE,
    RISK_ASSUMED_BY_OWNER,
    ST_ABSENT,
    ST_ANTICIPATION_POSSIBLE,
    ST_NO_EVIDENCE,
    ST_PROVEN,
    EntryEvidence,
    FiscalEvidenceError,
    FiscalResolver,
    classify_entry,
    evaluate_equivalents,
    require_declared,
    value_or_missing,
)
from src.operational.product_registration.schemas import ProductAnalysis

NEGRESCO_BASIS = {
    "cstEntrada": "060",
    "cstSaida": "060",
    "percentualIcmsEntrada": 0.0,
    "percentualIcmsSaida": 0.0,
    "dsCsosnEntrada": "0",
    "dsCsosnSaida": "0",
    "valorPercentualFcp": 0,
}
PIS_COFINS_BASIS = {"cstPisSaida": "01", "percentualPisSaida": 0.65}

TAXED_BASIS = {
    "cstEntrada": "000",
    "cstSaida": "000",
    "percentualIcmsEntrada": 17.0,
    "percentualIcmsSaida": 0.0,
}


def _evidence(**overrides) -> EntryEvidence:
    base = {
        "cst_icms": "00",
        "icms_st_retido": None,
        "cest": "1703200",
        "ncm": "20052000",
        "cfop_fornecedor": "5104",
        "invoice_reference": "7625/1",
    }
    base.update(overrides)
    return EntryEvidence(**base)


# --- Exigências explícitas da autorização ------------------------------------


def test_ncm_19059090_with_cst_00_never_receives_cst_060():
    """NCM do capítulo 19 com entrada tributada não pode virar substituído."""
    evidence = _evidence(cst_icms="00", ncm="19059090", cest=None)

    decision = FiscalResolver().decide(
        evidence,
        substituted_basis=NEGRESCO_BASIS,
        substituted_table_reference="0000000061",
        pis_cofins_basis=PIS_COFINS_BASIS,
    )

    assert decision.st_classification == ST_ABSENT
    assert decision.icms_basis is None
    assert not decision.can_register
    assert "NO_MEASURABLE_EQUIVALENT_BASIS" in decision.blockers


def test_product_without_st_does_not_inherit_negresco_basis():
    """Mesmo com a base de ST disponível, ela não é oferecida a quem entrou tributado."""
    evidence = _evidence(cst_icms="00", ncm="19053100", cest="1705300")

    decision = FiscalResolver().decide(
        evidence,
        substituted_basis=NEGRESCO_BASIS,
        substituted_table_reference="0000000061",
        pis_cofins_basis=PIS_COFINS_BASIS,
        equivalents_distribution={"0000000063": 9},
        basis_catalog={"0000000063": TAXED_BASIS},
    )

    assert decision.st_classification == ST_ANTICIPATION_POSSIBLE
    assert decision.icms_basis == TAXED_BASIS
    assert decision.icms_table_reference == "0000000063"
    assert decision.icms_basis["cstSaida"] != "060"
    assert decision.fiscal_risk == RISK_ASSUMED_BY_OWNER
    assert decision.requires_accountant_review is True


def test_empty_field_is_never_converted_to_zero():
    assert value_or_missing("") is None
    assert value_or_missing(None) is None
    assert value_or_missing("   ") is None
    assert value_or_missing(0) == 0
    assert value_or_missing("0") == "0"

    with pytest.raises(FiscalEvidenceError, match="cstSaida"):
        require_declared("", "cstSaida")


def test_empty_cst_does_not_become_absent_st():
    """CST vazio é ausência de evidência, não ausência de ST."""
    assert classify_entry(_evidence(cst_icms="")) == ST_NO_EVIDENCE
    assert classify_entry(_evidence(cst_icms=None)) == ST_NO_EVIDENCE


# --- Classificação ------------------------------------------------------------


def test_cst_60_is_st_proven():
    assert classify_entry(_evidence(cst_icms="60", icms_st_retido=1.71)) == ST_PROVEN


def test_st_withheld_value_alone_proves_st():
    assert classify_entry(_evidence(cst_icms="10", icms_st_retido=0.55)) == ST_PROVEN


def test_cst_00_with_cest_is_anticipation_possible():
    assert classify_entry(_evidence(cst_icms="00", cest="1703200")) == ST_ANTICIPATION_POSSIBLE


def test_cst_00_without_cest_is_st_absent():
    assert classify_entry(_evidence(cst_icms="00", cest=None)) == ST_ABSENT


def test_cst_00_with_empty_cest_is_st_absent():
    assert classify_entry(_evidence(cst_icms="00", cest="")) == ST_ABSENT


def test_st_proven_applies_substituted_basis_with_high_confidence():
    evidence = _evidence(cst_icms="60", icms_st_retido=1.71, ncm="19053100", cest="1705300")

    decision = FiscalResolver().decide(
        evidence,
        substituted_basis=NEGRESCO_BASIS,
        substituted_table_reference="0000000061",
        pis_cofins_basis=PIS_COFINS_BASIS,
        pis_cofins_table_reference="0000000007",
    )

    assert decision.st_classification == ST_PROVEN
    assert decision.icms_basis == NEGRESCO_BASIS
    assert decision.confidence == CONFIDENCE_HIGH
    assert decision.requires_accountant_review is False
    assert decision.can_register


def test_st_proven_without_matching_table_is_blocked():
    evidence = _evidence(cst_icms="60", icms_st_retido=1.71)

    decision = FiscalResolver().decide(evidence, pis_cofins_basis=PIS_COFINS_BASIS)

    assert "NO_MATCHING_ST_TABLE" in decision.blockers
    assert decision.icms_basis is None


# --- Critério de inferência ---------------------------------------------------


def test_inference_requires_five_equivalents_and_eighty_percent():
    reference, confidence, total, share = evaluate_equivalents({"A": 8, "B": 2})

    assert reference == "A"
    assert total == 10
    assert share == pytest.approx(0.8)
    assert confidence == CONFIDENCE_HIGH


def test_inference_below_eighty_percent_is_low_confidence():
    _, confidence, _, share = evaluate_equivalents({"A": 7, "B": 3})

    assert share == pytest.approx(0.7)
    assert confidence == CONFIDENCE_LOW


def test_inference_with_few_equivalents_is_low_confidence():
    _, confidence, total, _ = evaluate_equivalents({"A": 4})

    assert total == 4
    assert confidence == CONFIDENCE_LOW


def test_empty_distribution_is_not_consensus():
    reference, confidence, total, share = evaluate_equivalents({})

    assert reference is None
    assert confidence == CONFIDENCE_NONE
    assert total == 0
    assert share == 0.0


def test_predominant_reference_absent_from_local_tables_is_blocked():
    decision = FiscalResolver().decide(
        _evidence(),
        equivalents_distribution={"9999999999": 9},
        basis_catalog={"0000000063": TAXED_BASIS},
        pis_cofins_basis=PIS_COFINS_BASIS,
    )

    assert "BASIS_REFERENCE_NOT_IN_LOCAL_TABLES" in decision.blockers
    assert decision.icms_basis is None


# --- Base derivada da alíquota da própria NF-e --------------------------------

PE_TAXED_BASIS = {
    "percentualIcmsEntrada": 20.5,
    "cstEntrada": "000",
    "percentualIcmsSaida": 20.5,
    "cstSaida": "000",
    "dsCsosnEntrada": "0",
    "dsCsosnSaida": "0",
    "valorPercentualFcp": 0.0,
}


def test_taxed_entry_uses_rate_from_invoice_with_low_confidence():
    decision = FiscalResolver().decide(
        _evidence(cst_icms="00", cest="1703200"),
        substituted_basis=NEGRESCO_BASIS,
        substituted_table_reference="0000000061",
        taxed_basis=PE_TAXED_BASIS,
        taxed_table_reference="0000000044",
        pis_cofins_basis=PIS_COFINS_BASIS,
        pis_cofins_table_reference="0000000007",
        equivalents_distribution={},
    )

    assert decision.icms_basis == PE_TAXED_BASIS
    assert decision.icms_table_reference == "0000000044"
    assert decision.confidence == CONFIDENCE_LOW
    assert decision.fiscal_risk == RISK_ASSUMED_BY_OWNER
    assert decision.requires_accountant_review is True
    assert decision.can_register


def test_substituted_basis_is_refused_as_taxed_basis():
    """Blindagem: nem por engano a base 060 entra pelo caminho do produto tributado."""
    decision = FiscalResolver().decide(
        _evidence(cst_icms="00", cest="1703200"),
        taxed_basis=NEGRESCO_BASIS,
        taxed_table_reference="0000000061",
        pis_cofins_basis=PIS_COFINS_BASIS,
        equivalents_distribution={},
    )

    assert decision.icms_basis is None
    assert "SUBSTITUTED_BASIS_OFFERED_TO_TAXED_PRODUCT" in decision.blockers


def test_st_proven_ignores_taxed_basis():
    decision = FiscalResolver().decide(
        _evidence(cst_icms="60", icms_st_retido=1.71),
        substituted_basis=NEGRESCO_BASIS,
        substituted_table_reference="0000000061",
        taxed_basis=PE_TAXED_BASIS,
        taxed_table_reference="0000000044",
        pis_cofins_basis=PIS_COFINS_BASIS,
    )

    assert decision.icms_basis == NEGRESCO_BASIS
    assert decision.confidence == CONFIDENCE_HIGH


def test_measured_equivalents_take_precedence_over_invoice_rate():
    decision = FiscalResolver().decide(
        _evidence(cst_icms="00", cest="1703200"),
        taxed_basis=PE_TAXED_BASIS,
        taxed_table_reference="0000000044",
        pis_cofins_basis=PIS_COFINS_BASIS,
        equivalents_distribution={"0000000063": 9},
        basis_catalog={"0000000063": TAXED_BASIS},
    )

    assert decision.icms_table_reference == "0000000063"
    assert decision.confidence == CONFIDENCE_HIGH


# --- Produto sem NF-e de entrada ---------------------------------------------


def test_without_entry_evidence_and_without_candidates_nothing_is_assigned():
    decision = FiscalResolver().decide(
        _evidence(cst_icms=None),
        substituted_basis=NEGRESCO_BASIS,
        substituted_table_reference="0000000061",
        pis_cofins_basis=PIS_COFINS_BASIS,
    )

    assert decision.st_classification == ST_NO_EVIDENCE
    assert decision.icms_basis is None
    assert not decision.can_register
    assert decision.blockers == ["NO_ENTRY_TAX_EVIDENCE"]


def test_without_entry_evidence_cst_060_is_never_presumed():
    """A base de ST disponível não pode ser aplicada só porque existe."""
    decision = FiscalResolver().decide(
        _evidence(cst_icms=None, cest="1705300", ncm="19053100"),
        substituted_basis=NEGRESCO_BASIS,
        substituted_table_reference="0000000061",
        pis_cofins_basis=PIS_COFINS_BASIS,
    )

    assert decision.icms_basis is None
    assert decision.confidence == CONFIDENCE_NONE


def test_without_entry_evidence_two_plausible_bases_block_the_product():
    decision = FiscalResolver().decide(
        _evidence(cst_icms=None),
        no_evidence_candidates=[("0000000061", NEGRESCO_BASIS), ("0000000012", TAXED_BASIS)],
        pis_cofins_basis=PIS_COFINS_BASIS,
    )

    assert decision.blockers == ["AMBIGUOUS_BASIS_WITHOUT_ENTRY_EVIDENCE"]
    assert decision.icms_basis is None
    assert decision.fiscal_risk == RISK_ASSUMED_BY_OWNER


def test_without_entry_evidence_single_basis_is_low_confidence_and_reviewable():
    decision = FiscalResolver().decide(
        _evidence(cst_icms=None),
        no_evidence_candidates=[("0000000061", NEGRESCO_BASIS)],
        pis_cofins_basis=PIS_COFINS_BASIS,
    )

    assert decision.can_register
    assert decision.icms_table_reference == "0000000061"
    # Sem prova de entrada, confianca alta e proibida mesmo com base unica.
    assert decision.confidence == CONFIDENCE_LOW
    assert decision.fiscal_risk == RISK_ASSUMED_BY_OWNER
    assert decision.requires_accountant_review is True
    assert "tributoIcms" in decision.inferred_fields


def test_without_entry_evidence_repeated_reference_is_not_ambiguous():
    """Vários produtos apontando para a mesma tabela convergem, não conflitam."""
    decision = FiscalResolver().decide(
        _evidence(cst_icms=None),
        no_evidence_candidates=[
            ("0000000061", NEGRESCO_BASIS),
            ("0000000061", NEGRESCO_BASIS),
            ("0000000061", NEGRESCO_BASIS),
        ],
        pis_cofins_basis=PIS_COFINS_BASIS,
    )

    assert decision.can_register
    assert decision.equivalents_considered == 3


def test_without_entry_evidence_missing_pis_cofins_blocks():
    decision = FiscalResolver().decide(
        _evidence(cst_icms=None),
        no_evidence_candidates=[("0000000061", NEGRESCO_BASIS)],
        pis_cofins_basis=None,
    )

    assert decision.blockers == ["NO_MATCHING_PIS_COFINS_TABLE"]
    assert not decision.can_register


# --- Integração com o fluxo de análise ---------------------------------------


def _analysis() -> ProductAnalysis:
    return ProductAnalysis(
        ean="7892840817978",
        descricao="BATATA ORIGINAL RUFFLES 115G",
        preco_venda=20.50,
        gate="PENDING",
        status="READY_TO_CREATE",
        confidence="NONE",
        risk_level="MÉDIO_RISCO",
    )


def test_resolve_without_evidence_does_not_assign_basis():
    analysis = FiscalResolver().resolve(_analysis(), ncm="19053100", description="BISCOITO")

    assert analysis.status == "REVIEW_REQUIRED"
    assert analysis.tributo_icms in (None, {})
    assert analysis.field_provenance["icms_model"]["confidence"] == CONFIDENCE_NONE


def test_resolve_no_longer_applies_bono_by_ncm_prefix():
    """Antes, qualquer NCM 19* recebia CST 060 com confiança HIGH."""
    analysis = FiscalResolver().resolve(_analysis(), ncm="19041000", description="SALGADINHO")

    provenance = analysis.field_provenance["icms_model"]
    assert provenance["source"] != "FISCAL_RESOLVER_BONO"
    assert provenance["confidence"] != CONFIDENCE_HIGH


def test_resolve_blocks_forbidden_categories():
    analysis = FiscalResolver().resolve(_analysis(), ncm="27101259", description="GASOLINA COMUM")

    assert analysis.status == "BLOCKED"
    assert analysis.gate == "BLOCKED_KEYWORD_GASOLINA"
