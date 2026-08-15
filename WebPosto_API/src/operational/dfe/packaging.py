"""Resolvedor caixa vs unidade — nunca decide silenciosamente em ambiguidade."""

from __future__ import annotations

from typing import Any


PACKAGE_UNITS = {"CX", "DP", "PC", "PCT", "FD", "DZ", "CJ", "KIT", "BD", "SC"}
UNIT_UNITS = {"UN", "UND", "UNID", "KG", "G", "L", "ML", "MT", "M"}


def resolve_packaging(item: dict[str, Any]) -> dict[str, Any]:
    u_com = (item.get("u_com") or "").upper().strip()
    u_trib = (item.get("u_trib") or "").upper().strip()
    q_com = float(item.get("q_com") or 0)
    q_trib = float(item.get("q_trib") or 0)
    v_un = float(item.get("v_un_com") or 0)
    ean = item.get("c_ean")
    ean_trib = item.get("c_ean_trib")
    desc = (item.get("x_prod") or "").upper()

    factor: float | None = None
    status = "PACKAGING_AMBIGUITY"
    reasons: list[str] = []

    if q_com > 0 and q_trib > 0:
        ratio = q_trib / q_com
        if abs(ratio - round(ratio)) < 1e-6 and ratio >= 1:
            factor = float(round(ratio))
        elif abs(ratio - 1.0) < 1e-9:
            factor = 1.0

    if ean and ean_trib and ean == ean_trib and (factor in (None, 1.0)):
        status = "UNIT_CONFIRMED"
        factor = 1.0
        reasons.append("EAN comercial = EAN tributável")
    elif ean and ean_trib and ean != ean_trib:
        if factor and factor > 1:
            status = "CONVERSION_CONFIRMED"
            reasons.append("EAN distintos + fator qTrib/qCom")
        else:
            status = "PACKAGING_AMBIGUITY"
            reasons.append("EAN distintos sem fator inteiro claro")
    elif u_com in PACKAGE_UNITS and u_trib in UNIT_UNITS:
        if factor and factor > 1:
            status = "PACKAGE_CONFIRMED"
            reasons.append(f"uCom={u_com} → uTrib={u_trib}")
        else:
            status = "PACKAGING_AMBIGUITY"
            reasons.append("unidade de caixa sem fator confiável")
    elif u_com in UNIT_UNITS and (not u_trib or u_trib == u_com):
        status = "UNIT_CONFIRMED"
        factor = 1.0
        reasons.append("unidade comercial unitária")
    elif "CX" in desc or "COM " in desc:
        status = "PACKAGING_AMBIGUITY"
        reasons.append("descrição sugere embalagem — requer confirmação")

    if factor is not None and factor <= 0:
        status = "INVALID_CONVERSION"
        factor = None

    purchase_unit_cost = None
    sale_unit_cost_candidate = None
    if factor and factor > 0 and v_un:
        purchase_unit_cost = round(v_un / factor, 6)
        sale_unit_cost_candidate = purchase_unit_cost

    return {
        "packaging_status": status,
        "conversion_factor": factor,
        "purchase_unit_cost": purchase_unit_cost,
        "sale_unit_cost_candidate": sale_unit_cost_candidate,
        "reasons": reasons,
        "ambiguous": status == "PACKAGING_AMBIGUITY",
    }
