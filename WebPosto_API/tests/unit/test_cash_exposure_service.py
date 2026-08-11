"""CASH-01 — divergência de fechamento (Apresentado × Apurado × Diferença)."""
from __future__ import annotations

from src.domain.reconciliation.models import (
    CaptureOrigin,
    CardBreakdown,
    PaymentNatureCode,
    ReconciliationItem,
)
from src.services.cash_reconciliation.cash_exposure_service import (
    compute_cash_closing_exposure,
)


def _item(
    nature: PaymentNatureCode,
    *,
    apurado: float,
    apresentado: float,
    sangria: float | None = None,
    item_id: str = "t",
    card_breakdown: list | None = None,
    consolidation_status: str = "UNKNOWN",
    caixa_fechado: bool | None = None,
    caixa_codigo: int = 1,
) -> ReconciliationItem:
    return ReconciliationItem(
        id=item_id,
        filial=74014,
        caixaCodigo=caixa_codigo,
        periodoInicio="2026-08-06",
        periodoFim="2026-08-06",
        paymentNature=nature,
        valorApurado=apurado,
        valorApresentado=apresentado,
        sangria=sangria,
        diferenca=round(apresentado - apurado, 2),
        cardBreakdown=card_breakdown or [],
        consolidationStatus=consolidation_status,
        caixaFechado=caixa_fechado,
    )


def test_golden_prestacao_fechamento_semantica():
    """Caso conceitual Prestação de Contas — 1º turno (sem identificação de posto)."""
    items = [
        _item(
            PaymentNatureCode.DINHEIRO,
            apresentado=12_204.45,
            apurado=12_130.39,
            sangria=12_204.45,
            item_id="d",
        ),
        _item(
            PaymentNatureCode.CARTAO,
            apresentado=21_476.14,
            apurado=21_476.14,
            item_id="c",
        ),
        _item(
            PaymentNatureCode.TRANSFERENCIA_CREDITO,
            apresentado=13_917.26,
            apurado=13_917.26,
            item_id="t",
        ),
        # Outras naturezas do total WebPosto (fecha o TOTAL da prestação)
        _item(PaymentNatureCode.DESPESA, apresentado=3_500.00, apurado=3_500.00, item_id="x"),
        _item(PaymentNatureCode.NOTAS, apresentado=1_160.97, apurado=1_160.97, item_id="n"),
    ]
    # Total reportado: Apresentado 52258.82 / Apurado 52184.76 / Diff 74.06
    assert round(sum(i.valorApresentado for i in items), 2) == 52_258.82
    assert round(sum(i.valorApurado for i in items), 2) == 52_184.76

    dto = compute_cash_closing_exposure(
        items, period_start="2026-08-06", period_end="2026-08-06", company_id=74014
    )
    assert dto.presented_amount == 52_258.82
    assert dto.calculated_amount == 52_184.76
    assert dto.difference_amount == 74.06
    # Aliases apontam para o domínio nativo
    assert dto.identified_amount == dto.presented_amount
    assert dto.expected_amount == dto.calculated_amount
    assert dto.exposure_amount == dto.difference_amount

    by_m = {b.payment_method: b for b in dto.breakdown if b.status == "OK"}
    assert by_m["DINHEIRO"].presented_amount == 12_204.45
    assert by_m["DINHEIRO"].calculated_amount == 12_130.39
    assert by_m["DINHEIRO"].difference_amount == 74.06
    assert by_m["CARTAO"].difference_amount == 0.0
    assert by_m["TRANSFERENCIA_CREDITO"].difference_amount == 0.0
    assert "PIX" not in by_m


def test_cartao_ignores_expected_net_card_breakdown():
    """Bug: expectedNet agregado NÃO pode influenciar diferença de cartão."""
    fake_net = [
        CardBreakdown(
            rawPaymentLabel="VISA CREDITO TEF",
            normalizedBrand="VISA",
            normalizedMethod="CREDIT",
            normalizedAcquirer="UNKNOWN",
            captureOrigin=CaptureOrigin.TEF,
            grossAmount=21_476.14,
            expectedNet=1_318.99,
        )
    ]
    items = [
        _item(
            PaymentNatureCode.CARTAO,
            apresentado=1_446.46,
            apurado=1_446.46,
            item_id="c1",
            card_breakdown=fake_net,
        ),
        _item(
            PaymentNatureCode.CARTAO,
            apresentado=15_580.23,
            apurado=15_580.23,
            item_id="c2",
            card_breakdown=fake_net,  # mesmo breakdown colado nos 2 turnos
        ),
    ]
    dto = compute_cash_closing_exposure(
        items, period_start="2026-08-10", period_end="2026-08-10"
    )
    cartao = next(b for b in dto.breakdown if b.payment_method == "CARTAO")
    assert cartao.presented_amount == 17_026.69
    assert cartao.calculated_amount == 17_026.69
    assert cartao.difference_amount == 0.0
    # Não reproduz o falso gap −14.388,71
    assert abs(cartao.difference_amount) < 0.01


def test_difference_sign_matches_webposto():
    """diferença = apresentado − apurado (não apurado − apresentado)."""
    items = [
        _item(
            PaymentNatureCode.DINHEIRO,
            apresentado=12_204.45,
            apurado=12_130.39,
            item_id="d",
        )
    ]
    dto = compute_cash_closing_exposure(
        items, period_start="2026-08-06", period_end="2026-08-06"
    )
    assert dto.difference_amount == 74.06
    assert dto.difference_amount > 0


def test_zero_when_matched():
    items = [
        _item(PaymentNatureCode.DINHEIRO, apurado=40_000, apresentado=40_000, item_id="d"),
        _item(PaymentNatureCode.CARTAO, apurado=60_000, apresentado=60_000, item_id="c"),
    ]
    dto = compute_cash_closing_exposure(
        items, period_start="2026-08-10", period_end="2026-08-10", company_id=74014
    )
    assert dto.difference_amount == 0
    assert dto.has_data is True


def test_no_data():
    dto = compute_cash_closing_exposure(
        [], period_start="2026-08-10", period_end="2026-08-10"
    )
    assert dto.has_data is False
    assert dto.difference_amount == 0


def test_idempotent():
    items = [
        _item(PaymentNatureCode.CARTAO, apurado=184_820, apresentado=181_338, item_id="c"),
    ]
    a = compute_cash_closing_exposure(
        items, period_start="2026-08-10", period_end="2026-08-10"
    )
    b = compute_cash_closing_exposure(
        items, period_start="2026-08-10", period_end="2026-08-10"
    )
    assert a.model_dump() == b.model_dump()
    assert a.difference_amount == -3_482.0  # apresentado < apurado


def test_despesa_enters_total_not_primary_false_pix_label():
    items = [
        _item(PaymentNatureCode.DESPESA, apurado=500, apresentado=500, item_id="x"),
        _item(PaymentNatureCode.CARTAO, apurado=1_000, apresentado=900, item_id="c"),
        _item(
            PaymentNatureCode.TRANSFERENCIA_CREDITO,
            apurado=100,
            apresentado=100,
            item_id="t",
        ),
    ]
    dto = compute_cash_closing_exposure(
        items, period_start="2026-08-10", period_end="2026-08-10"
    )
    assert dto.presented_amount == 1_500
    assert dto.calculated_amount == 1_600
    assert dto.difference_amount == -100
    methods = {b.payment_method for b in dto.breakdown if b.status == "OK"}
    assert "TRANSFERENCIA_CREDITO" in methods
    assert "PIX" not in methods


def test_cash01s_fechado_true_consolidado_false_is_auditable():
    """Case 1: fechado=true, consolidado=false → CLOSED + auditável."""
    items = [
        _item(
            PaymentNatureCode.DINHEIRO,
            apurado=100,
            apresentado=90,
            item_id="d",
            caixa_fechado=True,
            consolidation_status="NOT_CONSOLIDATED",
        )
    ]
    dto = compute_cash_closing_exposure(
        items, period_start="2026-08-08", period_end="2026-08-08"
    )
    assert dto.closing_status == "CLOSED"
    assert dto.is_consolidated == "false"
    assert dto.reliable_for_closing_audit is True
    assert dto.difference_amount == -10


def test_cash01s_fechado_false_not_auditable():
    """Case 2: fechado=false → OPEN, não auditável."""
    items = [
        _item(
            PaymentNatureCode.DINHEIRO,
            apurado=100,
            apresentado=0,
            item_id="d",
            caixa_fechado=False,
            consolidation_status="NOT_CONSOLIDATED",
        )
    ]
    dto = compute_cash_closing_exposure(
        items, period_start="2026-08-11", period_end="2026-08-11"
    )
    assert dto.closing_status == "OPEN"
    assert dto.reliable_for_closing_audit is False


def test_cash01s_fechado_and_consolidado_true():
    """Case 3: fechado=true, consolidado=true → CLOSED + auditável."""
    items = [
        _item(
            PaymentNatureCode.CARTAO,
            apurado=50,
            apresentado=50,
            item_id="c",
            caixa_fechado=True,
            consolidation_status="CONSOLIDATED",
        )
    ]
    dto = compute_cash_closing_exposure(
        items, period_start="2026-08-06", period_end="2026-08-06"
    )
    assert dto.closing_status == "CLOSED"
    assert dto.is_consolidated == "true"
    assert dto.reliable_for_closing_audit is True


def test_cash01s_fechado_absent_does_not_invent_closed():
    """Case 4: campo fechado ausente → UNKNOWN, não inventa CLOSED."""
    items = [
        _item(
            PaymentNatureCode.DINHEIRO,
            apurado=100,
            apresentado=100,
            item_id="d",
            caixa_fechado=None,
            consolidation_status="CONSOLIDATED",
        )
    ]
    dto = compute_cash_closing_exposure(
        items, period_start="2026-08-06", period_end="2026-08-06"
    )
    assert dto.closing_status == "UNKNOWN"
    assert dto.reliable_for_closing_audit is False
    assert dto.is_consolidated == "true"
