"""Validação e busca de EAN (string) — sem escrita."""

from __future__ import annotations

from typing import Any

from src.operational.price_update.value_normalizer import (
    _gtin_checksum_ok,
    normalize_ean,
)


def validate_ean_strict(value: Any) -> dict[str, Any]:
    """
    Gate estrito para cadastro:
    - só dígitos;
    - comprimento 8/12/13/14;
    - checksum GTIN obrigatório;
    - preserva zeros à esquerda.
    """
    ean, issues = normalize_ean(value)
    if "BLOCKED_EAN_SCIENTIFIC" in issues or "BLOCKED_EAN_FLOAT_ARTIFACT" in issues:
        return {
            "ok": False,
            "ean": None,
            "gate": "BLOCKED_INVALID_EAN",
            "issues": issues,
        }
    if "BLOCKED_EAN_INVALID" in issues or "BLOCKED_EAN_LENGTH" in issues:
        return {
            "ok": False,
            "ean": None,
            "gate": "BLOCKED_INVALID_EAN",
            "issues": issues,
        }
    if ean is None:
        return {
            "ok": False,
            "ean": None,
            "gate": "BLOCKED_INVALID_EAN",
            "issues": issues or ["BLOCKED_INVALID_EAN"],
        }
    if "WARNING_EAN_CHECKSUM" in issues or not _gtin_checksum_ok(ean):
        return {
            "ok": False,
            "ean": ean,
            "gate": "BLOCKED_INVALID_EAN",
            "issues": ["BLOCKED_INVALID_EAN", "CHECKSUM_FAILED"],
        }
    return {"ok": True, "ean": ean, "gate": "EAN_OK", "issues": []}


def find_ean_duplicates(
    ean: str,
    *,
    products_by_empresa: dict[int, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Lista ocorrências do EAN em todas as empresas do índice (somente leitura)."""
    hits: list[dict[str, Any]] = []
    target = str(ean)
    for emp, products in (products_by_empresa or {}).items():
        for p in products:
            eans = p.get("eans") or []
            if isinstance(eans, str):
                eans = [eans]
            barcodes = p.get("produtoCodigoBarra") or []
            for b in barcodes:
                if isinstance(b, dict):
                    code = str(b.get("codigoBarra") or b.get("codigo") or "")
                else:
                    code = str(b or "")
                if code:
                    eans = list(eans) + [code]
            if target in {str(x) for x in eans if x}:
                hits.append(
                    {
                        "empresaCodigo": int(emp),
                        "produtoCodigo": p.get("produtoCodigo") or p.get("codigo"),
                        "descricao": p.get("nome") or p.get("descricao"),
                        "referencia": p.get("referenciaCodigo") or p.get("referencia"),
                        "ean": target,
                    }
                )
    return hits
