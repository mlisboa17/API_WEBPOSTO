"""Validacao de GTIN: nunca corrige, completa ou substitui codigo."""

from __future__ import annotations

from .duplicate_checker import looks_fabricated_gtin
from .ean_service import gtin_prefix_length_conflict, validate_ean_strict


class GtinValidationService:
    """Checksum, comprimento, prefixo GS1, inventado e truncado."""

    def validate(self, ean: str) -> dict[str, object]:
        strict = validate_ean_strict(ean)
        issues = list(strict.get("issues") or [])
        fabricated = looks_fabricated_gtin(str(strict.get("ean") or ean))
        truncated = gtin_prefix_length_conflict(str(strict.get("ean") or ean))
        if fabricated:
            issues.append(f"GTIN_COM_APARENCIA_DE_INVENTADO:{fabricated}")
        if truncated:
            issues.append(f"GTIN_TRUNCADO:{truncated}")
        ok = bool(strict.get("ok")) and not fabricated and not truncated
        return {
            "ok": ok,
            "ean": strict.get("ean"),
            "corrected": False,
            "issues": issues,
            "fabricated": fabricated,
            "truncated": truncated,
        }
