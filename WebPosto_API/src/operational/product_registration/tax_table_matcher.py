"""Normaliza as tabelas ICMS e PIS/COFINS do WebPosto e casa com o modelo comprovado.

As planilhas fornecidas pelo usuario ficam em data/product_registration/tax_tables_input/
e nunca sao alteradas. A selecao e feita por comparacao campo a campo, nunca por
descricao: a descricao serve apenas para desempatar CSOSN, que nao tem coluna propria.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import openpyxl

MATCH_UNIQUE = "UNIQUE"
MATCH_AMBIGUOUS = "AMBIGUOUS"
MATCH_NOT_FOUND = "NOT_FOUND"


@dataclass(frozen=True)
class IcmsRow:
    referencia: str
    descricao: str
    cst_entrada: str
    cst_saida: str
    icms_entrada: float
    icms_saida: float
    csosn_entrada: str | None
    csosn_saida: str | None
    fcp: float | None
    mva: float | None


@dataclass(frozen=True)
class PisCofinsRow:
    referencia: str
    descricao: str
    cst_pis_entrada: str
    cst_pis_saida: str
    pis_entrada: float
    pis_saida: float
    cst_cofins_entrada: str
    cst_cofins_saida: str
    cofins_entrada: float
    cofins_saida: float


def _number(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return float(str(value).replace(".", "").replace(",", ".")) if "," in str(value) else float(value)


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _parse_csosn(description: str, side: str) -> str | None:
    """Extrai CSOSN da descricao. `side` e SAI ou ENT.

    A planilha nao tem coluna de CSOSN; a descricao gerada pelo WebPosto e a unica
    fonte. Campo vazio na descricao significa CSOSN zerado, que e o que o endpoint
    legado aceitou como "0".
    """
    match = re.search(rf"{side} CSOSN(\s+\d+)?(?=\s*\||$)", description)
    if not match:
        return None
    captured = (match.group(1) or "").strip()
    return captured or "0"


def _parse_fcp(description: str) -> float | None:
    match = re.search(r"FCP\s+([\d.,]+)", description)
    return _number(match.group(1)) if match else None


def load_icms_table(path: Path) -> list[IcmsRow]:
    workbook = openpyxl.load_workbook(path, data_only=True)
    sheet = workbook.active
    rows: list[IcmsRow] = []
    for index, values in enumerate(sheet.iter_rows(values_only=True), start=1):
        if index == 1 or not values or not values[0]:
            continue
        descricao = _text(values[1])
        rows.append(
            IcmsRow(
                referencia=_text(values[0]),
                descricao=descricao,
                icms_entrada=_number(values[2]),
                icms_saida=_number(values[3]),
                cst_entrada=_text(values[4]),
                cst_saida=_text(values[5]),
                csosn_entrada=_parse_csosn(descricao, "ENT"),
                csosn_saida=_parse_csosn(descricao, "SAI"),
                fcp=_parse_fcp(descricao),
                mva=None,
            )
        )
    return rows


def load_pis_cofins_table(path: Path) -> list[PisCofinsRow]:
    workbook = openpyxl.load_workbook(path, data_only=True)
    sheet = workbook.active
    rows: list[PisCofinsRow] = []
    for index, values in enumerate(sheet.iter_rows(values_only=True), start=1):
        if index == 1 or not values or not values[0]:
            continue
        rows.append(
            PisCofinsRow(
                referencia=_text(values[0]),
                descricao=_text(values[1]),
                cst_pis_entrada=_text(values[2]),
                pis_entrada=_number(values[3]),
                cst_pis_saida=_text(values[4]),
                pis_saida=_number(values[5]),
                cst_cofins_entrada=_text(values[6]),
                cofins_entrada=_number(values[7]),
                cst_cofins_saida=_text(values[8]),
                cofins_saida=_number(values[9]),
            )
        )
    return rows


def match_icms(
    rows: list[IcmsRow],
    *,
    cst_entrada: str,
    cst_saida: str,
    icms_entrada: float,
    icms_saida: float,
    csosn_entrada: str,
    csosn_saida: str,
    fcp: float,
) -> tuple[str, list[IcmsRow]]:
    """Casa por todos os campos fiscais, incluindo CSOSN e FCP."""
    base = [
        row
        for row in rows
        if row.cst_entrada == cst_entrada
        and row.cst_saida == cst_saida
        and row.icms_entrada == icms_entrada
        and row.icms_saida == icms_saida
    ]
    # CSOSN e FCP nao declarados na descricao sao desconhecidos, nao zero. Tratar
    # ausencia como zero reintroduziria o erro que gerou o RET=3 (vazio != "0").
    exact = [
        row
        for row in base
        if row.csosn_entrada == csosn_entrada
        and row.csosn_saida == csosn_saida
        and row.fcp == fcp
    ]
    if len(exact) == 1:
        return MATCH_UNIQUE, exact
    if exact:
        return MATCH_AMBIGUOUS, exact
    return MATCH_NOT_FOUND, base


def match_icms_by_entry_rate(
    rows: list[IcmsRow],
    *,
    cst_entrada: str,
    icms_entrada: float,
    icms_saida: float,
    csosn_entrada: str = "0",
    csosn_saida: str = "0",
    fcp: float = 0.0,
) -> tuple[str, list[IcmsRow]]:
    """Casa a tabela pela aliquota de ICMS efetivamente destacada na NF-e de entrada.

    Usado quando a mercadoria entrou tributada: a aliquota vem medida do documento
    fiscal, nao de suposicao. O CSOSN continua tendo de ser declarado na tabela, e
    tabelas de entrada substituida sao recusadas explicitamente.
    """
    candidates = [
        row
        for row in rows
        if row.cst_entrada == cst_entrada
        and row.icms_entrada == icms_entrada
        and row.icms_saida == icms_saida
        and row.cst_entrada not in ("060", "60")
    ]
    exact = [
        row
        for row in candidates
        if row.csosn_entrada == csosn_entrada
        and row.csosn_saida == csosn_saida
        and row.fcp == fcp
    ]
    if len(exact) == 1:
        return MATCH_UNIQUE, exact
    if exact:
        return MATCH_AMBIGUOUS, exact
    return MATCH_NOT_FOUND, candidates


def basis_from_row(row: IcmsRow) -> dict[str, Any]:
    """Converte a linha da tabela no objeto tributoIcms aceito pelo endpoint."""
    if row.csosn_entrada is None or row.csosn_saida is None or row.fcp is None:
        raise ValueError(
            f"Tabela {row.referencia} nao declara CSOSN ou FCP: campo ausente nao pode "
            f"ser assumido como zero"
        )
    return {
        "percentualIcmsEntrada": row.icms_entrada,
        "cstEntrada": row.cst_entrada,
        "percentualIcmsSaida": row.icms_saida,
        "cstSaida": row.cst_saida,
        "dsCsosnEntrada": str(row.csosn_entrada),
        "dsCsosnSaida": str(row.csosn_saida),
        "valorPercentualFcp": row.fcp,
    }


def match_pis_cofins(
    rows: list[PisCofinsRow],
    *,
    cst_pis_entrada: str,
    cst_pis_saida: str,
    pis_entrada: float,
    pis_saida: float,
    cst_cofins_entrada: str,
    cst_cofins_saida: str,
    cofins_entrada: float,
    cofins_saida: float,
) -> tuple[str, list[PisCofinsRow]]:
    exact = [
        row
        for row in rows
        if row.cst_pis_entrada == cst_pis_entrada
        and row.cst_pis_saida == cst_pis_saida
        and row.pis_entrada == pis_entrada
        and row.pis_saida == pis_saida
        and row.cst_cofins_entrada == cst_cofins_entrada
        and row.cst_cofins_saida == cst_cofins_saida
        and row.cofins_entrada == cofins_entrada
        and row.cofins_saida == cofins_saida
    ]
    if len(exact) == 1:
        return MATCH_UNIQUE, exact
    if exact:
        return MATCH_AMBIGUOUS, exact
    return MATCH_NOT_FOUND, []
