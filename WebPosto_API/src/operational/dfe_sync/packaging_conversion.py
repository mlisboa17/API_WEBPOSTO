"""Conversao de embalagem com fator explicito. Sem inventar CX/DP."""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

from src.operational.cost_update.decimal_utils import to_decimal
from src.operational.product_registration.dfe_cost_resolver import (
    is_atomic_unit,
)

UNIT_IN_NAME = re.compile(r"^(?:CX|FD|DP|PCT|PC|DZ)(\d{1,3})$", re.IGNORECASE)
DESC_COUNT = re.compile(r"(?:C/|COM\s+|CX\s*)(\d{1,3})\b", re.IGNORECASE)


class PackagingConversionResolver:
    def __init__(self, manual_table: list[dict[str, Any]] | None = None) -> None:
        self.manual_table = list(manual_table or [])

    @classmethod
    def from_path(cls, path: Path | None) -> PackagingConversionResolver:
        if path is None or not path.is_file():
            return cls()
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(payload.get("conversions") or [])

    def resolve(
        self,
        item: dict[str, Any],
        *,
        supplier_cnpj: str | None = None,
        catalog_factor: Decimal | None = None,
    ) -> dict[str, Any]:
        u_com = str(item.get("u_com") or "").strip()
        u_trib = str(item.get("u_trib") or "").strip()
        q_com = to_decimal(item.get("q_com"))
        q_trib = to_decimal(item.get("q_trib"))
        desc = str(item.get("x_prod") or "")
        evidences: list[str] = []
        factor: Decimal | None = None
        confidence = "NONE"
        status = "REVIEW_REQUIRED"

        if is_atomic_unit(u_trib) and q_trib > 0 and q_com > 0:
            if is_atomic_unit(u_com):
                factor = Decimal(1)
                confidence = "HIGH"
                status = "CONFIRMED"
                evidences.append("qTrib em UNI com uCom atomica")
            else:
                ratio = (q_trib / q_com) if q_com else Decimal(0)
                if ratio == ratio.to_integral_value() and ratio >= 1:
                    factor = ratio
                    confidence = "HIGH"
                    status = "CONFIRMED"
                    evidences.append("qTrib em UNI / qCom inteiro")

        if factor is None and q_com > 0 and q_trib > 0:
            ratio = q_trib / q_com
            if ratio == ratio.to_integral_value() and ratio >= 1 and u_com.upper() != u_trib.upper():
                factor = ratio
                confidence = "HIGH"
                status = "CONFIRMED"
                evidences.append("relacao matematica explicita qTrib/qCom")

        named = UNIT_IN_NAME.match(u_com.replace(" ", ""))
        if named:
            named_factor = Decimal(named.group(1))
            if factor is None:
                factor = named_factor
                confidence = "HIGH"
                status = "CONFIRMED"
                evidences.append(f"unidade {u_com} declara fator {named_factor}")
            elif factor != named_factor:
                return self._review(u_com, q_com, u_trib, q_trib, desc, "conflito unidade vs qTrib")

        manual = self._manual(item, supplier_cnpj)
        if manual:
            manual_factor = to_decimal(manual["units_per_package"])
            if factor and factor != manual_factor:
                return self._review(u_com, q_com, u_trib, q_trib, desc, "conflito com tabela manual")
            factor = manual_factor
            confidence = "HIGH"
            status = "CONFIRMED"
            evidences.append("tabela manual versionada")

        if catalog_factor and catalog_factor > 0:
            if factor and factor != catalog_factor:
                return self._review(u_com, q_com, u_trib, q_trib, desc, "conflito com fator do cadastro")
            factor = catalog_factor
            confidence = "HIGH"
            status = "CONFIRMED"
            evidences.append("fator explicito no cadastro/planilha")

        suggested = None
        match = DESC_COUNT.search(desc)
        if match:
            suggested = Decimal(match.group(1))
            if factor is None:
                evidences.append("descricao sugere fator, sem coerencia matematica")
            elif suggested == factor:
                evidences.append("descricao coerente com o fator")

        if factor is None:
            if u_com.upper() in {"KG", "G"} or u_trib.upper() in {"KG", "G"}:
                return self._review(u_com, q_com, u_trib, q_trib, desc, "KG sem peso unitario confiavel", suggested)
            return self._review(u_com, q_com, u_trib, q_trib, desc, "embalagem sem quantidade explicita", suggested)

        return {
            "ok": True,
            "status": status,
            "factor": factor,
            "suggested_factor": suggested,
            "confidence": confidence,
            "evidences": evidences,
            "u_com": u_com,
            "q_com": q_com,
            "u_trib": u_trib,
            "q_trib": q_trib,
            "calculo": f"qCom={q_com} uCom={u_com} qTrib={q_trib} uTrib={u_trib} fator={factor}",
        }

    def _manual(self, item: dict[str, Any], supplier_cnpj: str | None) -> dict[str, Any] | None:
        ean = str(item.get("c_ean") or "")
        code = str(item.get("c_prod") or "")
        supplier = "".join(ch for ch in str(supplier_cnpj or "") if ch.isdigit())
        for row in self.manual_table:
            if str(row.get("ean")) != ean:
                continue
            if str(row.get("supplier_item_code") or "") != code:
                continue
            if "".join(ch for ch in str(row.get("supplier_cnpj") or "") if ch.isdigit()) != supplier:
                continue
            return row
        return None

    def _review(
        self,
        u_com: str,
        q_com: Decimal,
        u_trib: str,
        q_trib: Decimal,
        desc: str,
        reason: str,
        suggested: Decimal | None = None,
    ) -> dict[str, Any]:
        return {
            "ok": False,
            "status": "REVIEW_REQUIRED",
            "factor": None,
            "suggested_factor": suggested,
            "confidence": "LOW" if suggested else "NONE",
            "evidences": [reason],
            "u_com": u_com,
            "q_com": q_com,
            "u_trib": u_trib,
            "q_trib": q_trib,
            "calculo": reason,
            "descricao": desc,
        }
