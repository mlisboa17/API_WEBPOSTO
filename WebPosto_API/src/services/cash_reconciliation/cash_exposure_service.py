"""CASH-01 — Divergência de fechamento de caixa (thin orchestration).

Replica a semântica nativa do WebPosto / Prestação de Contas:

  APRESENTADO  → valorApresentado (D02)
  APURADO      → valorApurado (D02)
  DIFERENÇA    → item.diferenca (= apresentado − apurado quando campo nativo ausente)

NÃO usa expected_realized / cardBreakdown.expectedNet (recebível adquirente).
NÃO afirma perda, fraude, liquidação bancária ou EDI.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, computed_field

from src.domain.reconciliation.models import PaymentNatureCode, ReconciliationItem
from src.services.cash_operations_service import _round2
from src.services.cash_reconciliation.cash_reconciliation_service import (
    CashReconciliationService,
)
from src.services.cash_reconciliation.pre_reconciliation_engine import (
    PreReconciliationEngine,
)

# Lanes prioritários na UI CASH-01 (rótulos = domínio WebPosto, não "PIX").
_BREAKDOWN_ORDER: tuple[PaymentNatureCode, ...] = (
    PaymentNatureCode.DINHEIRO,
    PaymentNatureCode.CARTAO,
    PaymentNatureCode.TRANSFERENCIA_CREDITO,
    PaymentNatureCode.PRE_PAGO,
)

_LANE_LABEL: dict[PaymentNatureCode, str] = {
    PaymentNatureCode.DINHEIRO: "DINHEIRO",
    PaymentNatureCode.CARTAO: "CARTAO",
    PaymentNatureCode.TRANSFERENCIA_CREDITO: "TRANSFERENCIA_CREDITO",
    PaymentNatureCode.PRE_PAGO: "PRE_PAGO",
}

DATA_SCOPE_TOTAL = "CASH_CLOSING"
DISCLAIMER = (
    "Divergência de fechamento de caixa (CASH_CLOSING): "
    "Apresentado × Apurado do WebPosto. "
    "Não significa perda confirmada, liquidação bancária/adquirente nem fraude."
)


class CashExposureLaneDTO(BaseModel):
    payment_method: str
    presented_amount: float = 0.0
    calculated_amount: float = 0.0
    difference_amount: float = 0.0
    sangria_amount: float | None = None
    data_scope: str = DATA_SCOPE_TOTAL
    status: str = "OK"  # OK | UNKNOWN | OPEN

    # Aliases compatíveis com payload CASH-01 anterior (semântica nova: ver sources).
    @computed_field  # type: ignore[prop-decorator]
    @property
    def expected_amount(self) -> float:
        return self.calculated_amount

    @computed_field  # type: ignore[prop-decorator]
    @property
    def identified_amount(self) -> float:
        return self.presented_amount

    @computed_field  # type: ignore[prop-decorator]
    @property
    def exposure_amount(self) -> float:
        return self.difference_amount


class CashClosingExposureDTO(BaseModel):
    company_id: int | str | None = None
    period_start: str
    period_end: str
    presented_amount: float = 0.0
    calculated_amount: float = 0.0
    difference_amount: float = 0.0
    breakdown: list[CashExposureLaneDTO] = Field(default_factory=list)
    data_scope: str = DATA_SCOPE_TOTAL
    has_data: bool = False
    closing_status: str = "UNKNOWN"  # CLOSED | OPEN | MIXED | UNKNOWN
    open_caixa_count: int = 0
    reliable_for_closing_audit: bool = False
    disclaimer: str = DISCLAIMER
    sources: dict[str, str] = Field(default_factory=dict)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def expected_amount(self) -> float:
        return self.calculated_amount

    @computed_field  # type: ignore[prop-decorator]
    @property
    def identified_amount(self) -> float:
        return self.presented_amount

    @computed_field  # type: ignore[prop-decorator]
    @property
    def exposure_amount(self) -> float:
        return self.difference_amount


def _item_difference(item: ReconciliationItem) -> float:
    """Convenção WebPosto: diferença = apresentado − apurado (campo nativo se presente)."""
    if item.diferenca is not None:
        return float(item.diferenca)
    return _round2(float(item.valorApresentado or 0) - float(item.valorApurado or 0))


def _closing_status_from_items(items: list[ReconciliationItem]) -> tuple[str, int]:
    """Deriva status agregado a partir de consolidationStatus D02 + situacao de caixa."""
    open_n = 0
    closed_n = 0
    for item in items:
        status = (item.consolidationStatus or "").upper()
        # Evidência de caixa ainda aberto (quando presente no payload CAIXA)
        # consolidationStatus NOT_CONSOLIDATED ≠ necessariamente aberto, mas sinaliza.
        if status == "NOT_CONSOLIDATED":
            open_n += 1
        elif status == "CONSOLIDATED":
            closed_n += 1
    if open_n and closed_n:
        return "MIXED", open_n
    if open_n and not closed_n:
        return "OPEN", open_n
    if closed_n:
        return "CLOSED", 0
    return "UNKNOWN", 0


def compute_cash_closing_exposure(
    items: list[ReconciliationItem],
    *,
    period_start: str,
    period_end: str,
    company_id: int | str | None = None,
) -> CashClosingExposureDTO:
    """Agrega Apresentado / Apurado / Diferença a partir dos itens D02.

    Totais: todas as naturezas com movimento (fecha com Prestação de Contas).
    Breakdown UI: DINHEIRO, CARTAO, TRANSFERENCIA_CREDITO, PRE_PAGO.
    """
    if not items:
        return CashClosingExposureDTO(
            company_id=company_id,
            period_start=period_start,
            period_end=period_end,
            has_data=False,
            sources=_sources(),
        )

    presented_total = _round2(sum(float(i.valorApresentado or 0) for i in items))
    calculated_total = _round2(sum(float(i.valorApurado or 0) for i in items))
    difference_total = _round2(sum(_item_difference(i) for i in items))

    by_nature: dict[PaymentNatureCode, list[ReconciliationItem]] = {}
    for item in items:
        by_nature.setdefault(item.paymentNature, []).append(item)

    breakdown: list[CashExposureLaneDTO] = []
    for nature in _BREAKDOWN_ORDER:
        group = by_nature.get(nature) or []
        label = _LANE_LABEL[nature]
        if not group:
            breakdown.append(
                CashExposureLaneDTO(
                    payment_method=label,
                    status="UNKNOWN",
                    data_scope=DATA_SCOPE_TOTAL,
                )
            )
            continue
        presented = _round2(sum(float(i.valorApresentado or 0) for i in group))
        calculated = _round2(sum(float(i.valorApurado or 0) for i in group))
        difference = _round2(sum(_item_difference(i) for i in group))
        sangria_vals = [float(i.sangria) for i in group if i.sangria is not None]
        sangria = _round2(sum(sangria_vals)) if sangria_vals else None
        lane_open = any(
            (i.consolidationStatus or "").upper() == "NOT_CONSOLIDATED" for i in group
        )
        breakdown.append(
            CashExposureLaneDTO(
                payment_method=label,
                presented_amount=presented,
                calculated_amount=calculated,
                difference_amount=difference,
                sangria_amount=sangria,
                data_scope=DATA_SCOPE_TOTAL,
                status="OPEN" if lane_open else "OK",
            )
        )

    # Maior |divergência| primeiro entre lanes com dados
    breakdown.sort(
        key=lambda x: (0 if x.status != "UNKNOWN" else 1, -abs(x.difference_amount))
    )

    closing_status, open_count = _closing_status_from_items(items)
    # Caixa aberto / não consolidado: números existem, mas não equivalem a fechamento concluído.
    reliable = closing_status == "CLOSED" and open_count == 0

    return CashClosingExposureDTO(
        company_id=company_id,
        period_start=period_start,
        period_end=period_end,
        presented_amount=presented_total,
        calculated_amount=calculated_total,
        difference_amount=difference_total,
        breakdown=breakdown,
        data_scope=DATA_SCOPE_TOTAL,
        has_data=True,
        closing_status=closing_status,
        open_caixa_count=open_count,
        reliable_for_closing_audit=reliable,
        sources=_sources(),
    )


def _sources() -> dict[str, str]:
    return {
        "presented": "ReconciliationItem.valorApresentado ← CAIXA_APRESENTADO (*Apresentado)",
        "calculated": "ReconciliationItem.valorApurado ← CAIXA_APRESENTADO (*Apurado)",
        "difference": "ReconciliationItem.diferenca ← *Diferenca | apresentado − apurado",
        "sangria": "item.sangria (quando D02 popular) | meta.sangriaTotal separado — não entra na fórmula da diferença",
        "breakdown": "DINHEIRO/CARTAO/TRANSFERENCIA_CREDITO/PRE_PAGO (PaymentNatureCode D02)",
        "not_used": "expected_realized / cardBreakdown.expectedNet (fora do escopo CASH-01 V1)",
        "engine": "CashReconciliationService.build_items (+ PreEngine só para estado/justificativas)",
        "aliases": "expected_amount=calculated; identified_amount=presented; exposure_amount=difference (sinal WebPosto)",
    }


class CashExposureService:
    """Orquestra leitura D02 → divergência de fechamento CASH-01 (read-only)."""

    def __init__(self, recon: CashReconciliationService | None = None) -> None:
        self._recon = recon or CashReconciliationService()
        self._pre = PreReconciliationEngine()

    async def build(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: str | int | None = None,
    ) -> CashClosingExposureDTO:
        items, _meta = await self._recon.build_items(
            data_inicial, data_final, empresa_codigo
        )
        state_key = self._recon._state.state_key(empresa_codigo, data_inicial, data_final)
        persisted = self._recon._state.load(state_key).get("items") or {}
        for item in items:
            item.justifications = self._recon._state.list_justifications(
                state_key, item.id
            )
        # PreEngine ainda roda para status/justificativas; CASH-01 NÃO usa valorEsperado/expected_realized.
        items, _pre = self._pre.run(items, persisted)
        return compute_cash_closing_exposure(
            items,
            period_start=data_inicial,
            period_end=data_final,
            company_id=empresa_codigo,
        )
