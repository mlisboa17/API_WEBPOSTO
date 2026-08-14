"""Carrega a planilha fiscal de produtos a cadastrar da empresa 118508.

A planilha e a unica fonte do lote. Nada e corrigido automaticamente: codigo que nao
passa no digito verificador e bloqueado, e CEST ausente permanece ausente.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import openpyxl

from .ean_service import validate_ean_strict

NCM_LENGTH = 8
CEST_LENGTH = 7


@dataclass
class SheetRow:
    """Linha da planilha depois da normalizacao."""

    line: int
    raw_code: str
    ean: str | None
    ean_valid: bool
    ean_issues: list[str]
    descricao: str
    preco_venda: float | None
    ncm: str | None
    cest: str | None
    ncm_padded: bool = False
    cest_padded: bool = False

    @property
    def has_price(self) -> bool:
        return self.preco_venda is not None and self.preco_venda > 0

    @property
    def has_cest(self) -> bool:
        return self.cest is not None


def _digits(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return "".join(c for c in str(value) if c.isdigit())


def normalize_code(value: Any) -> str:
    """Preserva zeros a esquerda: o codigo vem como texto ou numero na planilha."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def normalize_ncm(value: Any) -> tuple[str | None, bool]:
    """NCM com exatamente 8 digitos.

    Planilhas salvam NCM como numero e perdem o zero a esquerda: 9011110 e 09011110.
    O preenchimento a esquerda e registrado para auditoria.
    """
    digits = _digits(value)
    if not digits:
        return None, False
    if len(digits) > NCM_LENGTH:
        return digits[-NCM_LENGTH:], False
    return digits.zfill(NCM_LENGTH), len(digits) < NCM_LENGTH


def normalize_cest(value: Any) -> tuple[str | None, bool]:
    """CEST com exatamente 7 digitos, ou None quando vazio.

    Vazio permanece vazio: CEST ausente nao e CEST zero.
    """
    digits = _digits(value)
    if not digits:
        return None, False
    if len(digits) > CEST_LENGTH:
        return digits[-CEST_LENGTH:], False
    return digits.zfill(CEST_LENGTH), len(digits) < CEST_LENGTH


def normalize_price(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("R$", "").strip()
    text = text.replace(".", "").replace(",", ".") if "," in text else text
    try:
        return float(text)
    except ValueError:
        return None


def load_sheet(path: Path) -> list[SheetRow]:
    """Le a planilha preservando a linha de origem para rastreabilidade."""
    workbook = openpyxl.load_workbook(path, data_only=True)
    sheet = workbook.active
    rows: list[SheetRow] = []

    for line, values in enumerate(sheet.iter_rows(values_only=True), start=1):
        if line == 1 or not values or values[0] in (None, ""):
            continue

        raw_code = normalize_code(values[0])
        validation = validate_ean_strict(raw_code)
        ncm, ncm_padded = normalize_ncm(values[3] if len(values) > 3 else None)
        cest, cest_padded = normalize_cest(values[4] if len(values) > 4 else None)

        rows.append(
            SheetRow(
                line=line,
                raw_code=raw_code,
                ean=validation.get("ean") or (raw_code or None),
                ean_valid=bool(validation.get("ok")),
                ean_issues=list(validation.get("issues") or []),
                descricao=str(values[1] or "").strip(),
                preco_venda=normalize_price(values[2] if len(values) > 2 else None),
                ncm=ncm,
                cest=cest,
                ncm_padded=ncm_padded,
                cest_padded=cest_padded,
            )
        )
    return rows
