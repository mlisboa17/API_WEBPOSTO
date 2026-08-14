"""Correspondência de tabela ICMS pela alíquota destacada na NF-e de entrada."""

from __future__ import annotations

import pytest

from src.operational.product_registration.tax_table_matcher import (
    MATCH_AMBIGUOUS,
    MATCH_NOT_FOUND,
    MATCH_UNIQUE,
    IcmsRow,
    basis_from_row,
    match_icms_by_entry_rate,
)


def _row(ref: str, ent: float, sai: float, csosn: str | None, fcp: float | None, cst_ent="000") -> IcmsRow:
    return IcmsRow(
        referencia=ref,
        descricao=f"SAI CST 000 ICMS {sai} | ENT CST {cst_ent} ICMS {ent}",
        cst_entrada=cst_ent,
        cst_saida="000",
        icms_entrada=ent,
        icms_saida=sai,
        csosn_entrada=csosn,
        csosn_saida=csosn,
        fcp=fcp,
        mva=None,
    )


PE_ROWS = [
    _row("0000000033", 20.5, 20.5, "900", 0.0),
    _row("0000000001", 20.5, 20.5, None, None),
    _row("0000000044", 20.5, 20.5, "0", 0.0),
    _row("0000000046", 20.5, 17.0, "900", None),
    _row("0000000018", 7.0, 17.0, "900", None),
]


def _match(rows, ent=20.5, sai=20.5):
    return match_icms_by_entry_rate(
        rows, cst_entrada="000", icms_entrada=ent, icms_saida=sai
    )


def test_unique_match_by_measured_entry_rate():
    status, matches = _match(PE_ROWS)

    assert status == MATCH_UNIQUE
    assert matches[0].referencia == "0000000044"


def test_rows_without_declared_csosn_are_not_selected():
    status, matches = _match([_row("0000000001", 20.5, 20.5, None, None)])

    assert status == MATCH_NOT_FOUND
    assert matches[0].referencia == "0000000001"


def test_ambiguity_is_reported_not_guessed():
    rows = [_row("A", 20.5, 20.5, "0", 0.0), _row("B", 20.5, 20.5, "0", 0.0)]

    status, matches = _match(rows)

    assert status == MATCH_AMBIGUOUS
    assert len(matches) == 2


def test_different_rate_does_not_match():
    status, _ = _match(PE_ROWS, ent=17.0)

    assert status == MATCH_NOT_FOUND


def test_substituted_entry_table_is_never_returned():
    rows = [_row("0000000061", 0.0, 0.0, "0", 0.0, cst_ent="060")]

    status, matches = match_icms_by_entry_rate(
        rows, cst_entrada="060", icms_entrada=0.0, icms_saida=0.0
    )

    assert status == MATCH_NOT_FOUND
    assert matches == []


def test_basis_from_row_serializes_csosn_as_string():
    basis = basis_from_row(_row("0000000044", 20.5, 20.5, "0", 0.0))

    assert basis["dsCsosnEntrada"] == "0"
    assert basis["dsCsosnSaida"] == "0"
    assert basis["cstEntrada"] == "000"
    assert basis["percentualIcmsEntrada"] == 20.5
    assert basis["valorPercentualFcp"] == 0.0


def test_basis_from_row_refuses_undeclared_csosn():
    with pytest.raises(ValueError, match="nao declara CSOSN ou FCP"):
        basis_from_row(_row("0000000001", 20.5, 20.5, None, None))
