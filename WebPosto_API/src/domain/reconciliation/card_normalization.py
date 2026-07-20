"""D02 — Normalização de cartões (bandeira/adquirente/origem)."""
from __future__ import annotations

from typing import Any

from src.domain.reconciliation.models import CaptureOrigin, CardBreakdown
from src.domain.reconciliation.payment_normalization import (
    infer_acquirer,
    infer_capture_origin,
    infer_card_brand,
    infer_card_method,
)


def normalize_card_row(row: dict[str, Any]) -> CardBreakdown:
    label = str(row.get("nomeFormaPagamento") or row.get("formaPagamento") or row.get("descricao") or "CARTAO")
    origin = infer_capture_origin(label, row.get("tipoFormaPagamento"))
    fee = row.get("taxaPercentual")
    gross = float(row.get("valorPagamento") or row.get("valor") or 0)
    fee_rate = float(fee) if fee not in (None, "", 0) else None
    expected_net = round(gross * (1 - fee_rate / 100), 2) if fee_rate is not None else None
    return CardBreakdown(
        rawPaymentLabel=label,
        normalizedBrand=infer_card_brand(label),
        normalizedMethod=infer_card_method(label),
        normalizedAcquirer=infer_acquirer(label, row.get("administradoraCodigo")),
        captureOrigin=origin,
        grossAmount=round(gross, 2),
        feeRate=fee_rate,
        expectedNet=expected_net,
        settlementDate=str(row.get("vencimento") or "")[:10] or None,
        destinationAccount=None,
    )


def aggregate_card_breakdown(rows: list[dict[str, Any]]) -> list[CardBreakdown]:
    buckets: dict[tuple, CardBreakdown] = {}
    for row in rows:
        card = normalize_card_row(row)
        key = (
            card.rawPaymentLabel,
            card.normalizedBrand,
            card.normalizedMethod,
            card.normalizedAcquirer,
            card.captureOrigin.value,
        )
        if key not in buckets:
            buckets[key] = card
        else:
            prev = buckets[key]
            prev.grossAmount = round(prev.grossAmount + card.grossAmount, 2)
            if prev.expectedNet is not None and card.expectedNet is not None:
                prev.expectedNet = round(prev.expectedNet + card.expectedNet, 2)
    return sorted(buckets.values(), key=lambda c: c.grossAmount, reverse=True)


def card_rows_from_vfp(vfp_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in vfp_rows:
        label = str(row.get("nomeFormaPagamento") or row.get("tipoFormaPagamento") or "").upper()
        if any(x in label for x in ("CARTAO", "CARTÃO", "CREDITO", "CRÉDITO", "DEBITO", "DÉBITO", "VISA", "MASTER", "ELO", "MAESTRO")):
            out.append(row)
        elif row.get("tipoFormaPagamento") and "CART" in str(row.get("tipoFormaPagamento")).upper():
            out.append(row)
    return out
