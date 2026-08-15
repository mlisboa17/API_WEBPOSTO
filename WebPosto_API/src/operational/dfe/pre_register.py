"""Pré-cadastro a partir de itens NF-e × modelos fiscais × catálogo (read-only)."""

from __future__ import annotations

from typing import Any


def analyze_item(
    item: dict[str, Any],
    *,
    company_code: int,
    existing_products: list[dict[str, Any]] | None = None,
    fiscal_models: list[dict[str, Any]] | None = None,
    document_status: str | None = None,
) -> dict[str, Any]:
    if document_status == "CANCELLED":
        return {
            "status": "CANCELLED_DOCUMENT",
            "suggestionNotConfirmation": True,
            "webpostoWrites": 0,
            "inheritedPurchasePrice": item.get("purchase_unit_cost") or item.get("v_un_com"),
            "note": "preço de compra vem da NF-e — não herdar tributação de entrada para saída",
        }

    pack = item.get("packaging_status") or (item.get("packaging") or {}).get("packaging_status")
    if pack == "PACKAGING_AMBIGUITY":
        return {
            "status": "PACKAGING_AMBIGUITY",
            "suggestionNotConfirmation": True,
            "webpostoWrites": 0,
            "reasons": (item.get("packaging") or {}).get("reasons") or [],
        }

    ean = item.get("c_ean")
    existing = existing_products or []
    matches = []
    for p in existing:
        pe = str(p.get("ean") or p.get("codigoBarras") or p.get("cEAN") or "")
        if ean and pe and pe == ean:
            matches.append(p)
        elif item.get("c_prod") and str(p.get("produtoCodigo") or p.get("codigo")) == str(item.get("c_prod")):
            matches.append(p)
    if len(matches) > 1:
        return {"status": "DUPLICATE", "matches": len(matches), "suggestionNotConfirmation": True, "webpostoWrites": 0}
    if len(matches) == 1:
        return {
            "status": "ALREADY_REGISTERED",
            "productCode": matches[0].get("produtoCodigo") or matches[0].get("codigo"),
            "suggestionNotConfirmation": True,
            "webpostoWrites": 0,
            "purchasePriceEvidence": item.get("purchase_unit_cost") or item.get("v_un_com"),
            "ncmCandidate": item.get("ncm"),
            "cestCandidate": item.get("cest"),
        }

    models = [m for m in (fiscal_models or []) if m.get("status") == "APPROVED"]
    # match by NCM/category tokens
    ncm = item.get("ncm")
    matched_model = None
    for m in models:
        if ncm and m.get("ncm") == ncm and int(m.get("company_code") or 0) == company_code:
            matched_model = m
            break

    if not matched_model:
        # try draft incomplete still blocks fiscal apply
        drafts = [
            m
            for m in (fiscal_models or [])
            if int(m.get("company_code") or 0) == company_code and ncm and m.get("ncm") == ncm
        ]
        if drafts:
            return {
                "status": "NO_FISCAL_MODEL",
                "reason": "modelo existe mas não APPROVED",
                "modeloId": drafts[0].get("id"),
                "modeloStatus": drafts[0].get("status"),
                "ncmCandidate": ncm,
                "cestCandidate": item.get("cest"),
                "purchasePriceEvidence": item.get("purchase_unit_cost") or item.get("v_un_com"),
                "suggestionNotConfirmation": True,
                "webpostoWrites": 0,
                "doNotCopyInboundTaxToOutbound": True,
            }
        return {
            "status": "NO_FISCAL_MODEL",
            "ncmCandidate": ncm,
            "cestCandidate": item.get("cest"),
            "purchasePriceEvidence": item.get("purchase_unit_cost") or item.get("v_un_com"),
            "suggestionNotConfirmation": True,
            "webpostoWrites": 0,
            "doNotCopyInboundTaxToOutbound": True,
        }

    # APPROVED model — suggest outbound fields; never copy inbound ICMS as confirmation
    suggested = {
        "codigoNcm": matched_model.get("ncm"),
        "codigoCest": matched_model.get("cest"),
        "grupoCodigo": matched_model.get("group_code"),
        "centroCustoCodigo": matched_model.get("cost_center_code"),
        "fromFiscalModelId": matched_model.get("id"),
        "outboundFields": {
            f.get("field_name"): f.get("value_json")
            for f in (matched_model.get("fields") or [])
            if f.get("field_status") != "MISSING"
        },
    }
    inbound_tax = {
        "icms_entrada": item.get("normalized_json", {}).get("icms") if isinstance(item.get("normalized_json"), dict) else None,
        "note": "evidência de entrada — não aplicar automaticamente na saída",
    }

    status = "PRE_REGISTER_READY"
    if pack and pack not in {"UNIT_CONFIRMED", "PACKAGE_CONFIRMED", "CONVERSION_CONFIRMED"}:
        status = "READY_FOR_REVIEW"

    return {
        "status": status,
        "suggested": suggested,
        "inboundTaxEvidence": inbound_tax,
        "purchasePriceEvidence": item.get("purchase_unit_cost") or item.get("v_un_com"),
        "identity": {
            "xProd": item.get("x_prod"),
            "cEAN": item.get("c_ean"),
            "cProd": item.get("c_prod"),
            "ncm": item.get("ncm"),
            "cest": item.get("cest"),
            "origem": item.get("origem"),
        },
        "suggestionNotConfirmation": True,
        "webpostoWrites": 0,
        "doNotCopyInboundTaxToOutbound": True,
    }


def analyze_document(
    document: dict[str, Any],
    items: list[dict[str, Any]],
    *,
    existing_products: list[dict[str, Any]] | None = None,
    fiscal_models: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    results = [
        analyze_item(
            it,
            company_code=int(document.get("company_code") or 0),
            existing_products=existing_products,
            fiscal_models=fiscal_models,
            document_status=document.get("status"),
        )
        for it in items
    ]
    summary = {}
    for r in results:
        summary[r["status"]] = summary.get(r["status"], 0) + 1
    return {
        "documentId": document.get("id"),
        "company_code": document.get("company_code"),
        "summary": summary,
        "items": results,
        "webpostoWrites": 0,
        "suggestionNotConfirmation": True,
    }
