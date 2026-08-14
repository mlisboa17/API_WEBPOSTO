"""Perfis fiscais: nivel expressa forca da evidencia e familia nunca e atravessada."""

from __future__ import annotations

from src.operational.product_registration.fiscal_profiles import (
    LEVEL_B,
    LEVEL_C,
    TREATMENT_SUBSTITUTED,
    TREATMENT_TAXED,
    build_profile_id,
    place_from_evidence,
    read_evidence,
    special_category,
)


def _entry(*, family="BISCOITO", classification="ST_COMPROVADA", cst="60", rate=None, nfe="1/1"):
    return {
        "familiaComercial": family,
        "classification": classification,
        "cstIcms": cst,
        "aliquotaEntrada": rate,
        "nfe": nfe,
    }


def _summary(entries, *, invoices=None, suppliers=1):
    return {
        "itens": len(entries),
        "notasDistintas": invoices if invoices is not None else len({e["nfe"] for e in entries}),
        "fornecedoresDistintos": suppliers,
        "classificacoes": sorted({e["classification"] for e in entries}),
        "distribuicaoCst": {},
        "familiasObservadas": {},
    }


def test_substituted_evidence_in_many_invoices_and_suppliers_is_strong():
    entries = [_entry(nfe=f"{i}/1") for i in range(6)]

    reading = read_evidence(entries, _summary(entries, suppliers=3), "BISCOITO")
    placement = place_from_evidence(reading)

    assert placement.level == LEVEL_B
    assert placement.treatment == TREATMENT_SUBSTITUTED


def test_single_supplier_reduces_the_level_without_blocking():
    """Fornecedor unico deixa de barrar: passa a ser analogia reduzida."""
    entries = [_entry(nfe=f"{i}/1") for i in range(4)]

    placement = place_from_evidence(read_evidence(entries, _summary(entries, suppliers=1), "BISCOITO"))

    assert placement.level == LEVEL_C


def test_two_invoices_is_reduced_level():
    entries = [_entry(nfe="1/1"), _entry(nfe="2/1")]

    placement = place_from_evidence(read_evidence(entries, _summary(entries, suppliers=2), "BISCOITO"))

    assert placement.level == LEVEL_C


def test_taxed_evidence_needs_a_single_entry_rate():
    entries = [
        _entry(classification="SEM_ST_COMPROVADA", cst="00", rate=20.5, nfe="1/1"),
        _entry(classification="SEM_ST_COMPROVADA", cst="00", rate=20.5, nfe="2/1"),
        _entry(classification="SEM_ST_COMPROVADA", cst="00", rate=20.5, nfe="3/1"),
    ]

    placement = place_from_evidence(read_evidence(entries, _summary(entries, suppliers=2), "BISCOITO"))

    assert placement.level == LEVEL_B
    assert placement.treatment == TREATMENT_TAXED
    assert placement.entry_rate == 20.5


def test_divergent_entry_rates_block_the_profile():
    entries = [
        _entry(classification="SEM_ST_COMPROVADA", cst="00", rate=20.5, nfe="1/1"),
        _entry(classification="SEM_ST_COMPROVADA", cst="00", rate=12.0, nfe="2/1"),
    ]

    placement = place_from_evidence(read_evidence(entries, _summary(entries, suppliers=2), "BISCOITO"))

    assert placement.level is None
    assert placement.blocked_reason == "ALIQUOTAS_DE_ENTRADA_DIVERGENTES"


def test_mixed_treatments_block_the_profile():
    entries = [
        _entry(classification="ST_COMPROVADA", nfe="1/1"),
        _entry(classification="SEM_ST_COMPROVADA", cst="00", rate=20.5, nfe="2/1"),
    ]

    placement = place_from_evidence(read_evidence(entries, _summary(entries, suppliers=2), "BISCOITO"))

    assert placement.level is None
    assert placement.blocked_reason == "TRATAMENTOS_CONCORRENTES_NA_EVIDENCIA"


def test_evidence_from_another_family_does_not_support_the_product():
    entries = [_entry(family="CONGELADO_PRONTO", nfe=f"{i}/1") for i in range(4)]

    placement = place_from_evidence(read_evidence(entries, _summary(entries, suppliers=2), "BOLO_INDUSTRIAL"))

    assert placement.level is None
    assert placement.blocked_reason == "FAMILIA_COMERCIAL_DIVERGENTE"


def test_unclassifiable_supplier_description_is_silence_not_divergence():
    """Descricao de fornecedor que nao se classifica nao contradiz nada; o nivel cai."""
    entries = [_entry(family=None, nfe=f"{i}/1") for i in range(4)]

    placement = place_from_evidence(
        read_evidence(entries, _summary(entries, suppliers=2), "BISCOITO")
    )

    assert placement.level == LEVEL_C
    assert placement.evidence.family_evidence == "NEUTRA"


def test_candidate_without_family_still_relies_on_ncm_and_cest():
    entries = [_entry(nfe=f"{i}/1") for i in range(4)]

    placement = place_from_evidence(read_evidence(entries, _summary(entries, suppliers=2), None))

    assert placement.level == LEVEL_C


def test_recognized_family_in_minority_still_blocks():
    entries = [_entry(family="CONGELADO_PRONTO", nfe=f"{i}/1") for i in range(3)]
    entries.append(_entry(family="BISCOITO", nfe="9/1"))

    placement = place_from_evidence(read_evidence(entries, _summary(entries, suppliers=2), "BISCOITO"))

    assert placement.level is None
    assert placement.blocked_reason == "FAMILIA_COMERCIAL_DIVERGENTE"


def test_confirmed_family_is_required_for_strong_analogy():
    """Sem familia confirmada, muitas notas e fornecedores nao elevam para analogia forte."""
    entries = [_entry(family=None, nfe=f"{i}/1") for i in range(8)]

    placement = place_from_evidence(
        read_evidence(entries, _summary(entries, suppliers=4), "BISCOITO")
    )

    assert placement.level == LEVEL_C


def test_special_categories_are_detected_by_ncm_chapter():
    assert special_category("22030000") == "BEBIDA_ALCOOLICA"
    assert special_category("24022000") == "TABACO"
    assert special_category("30049099") == "MEDICAMENTO"
    assert special_category("19053100") is None


def test_profile_id_separates_family_and_reference():
    first = build_profile_id("PROFILE_B", "BISCOITO", "19053100", "1705300", "0000000061")
    second = build_profile_id("PROFILE_B", "BOLO_INDUSTRIAL", "19053100", "1705300", "0000000061")

    assert first != second
    assert first == "PB-BISCOITO-19053100-1705300-0000000061"
