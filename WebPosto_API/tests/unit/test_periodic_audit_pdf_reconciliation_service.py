from src.services.periodic_audit_pdf_reconciliation_service import (
    PeriodicAuditPdfReconciliationService,
)


TEXT = """
Prestação de Contas AP CASA CAIADA
Data Inicial: 01/07/2026
Data Final: 15/07/2026
Meios de Pagamento Apresentado (R$) Sangria (R$) Apurado (R$) Diferença (R$)
Total 254.965,73 15.499,76 255.426,64 -460,91
"""


def test_extracts_verified_totals_from_real_layout():
    result = PeriodicAuditPdfReconciliationService.extract_text(TEXT, 6)
    assert result["period"] == {"start": "01/07/2026", "end": "15/07/2026"}
    assert result["paymentSummary"]["presented"] == "254965.73"
    assert result["paymentSummary"]["withdrawals"] == "15499.76"
    assert result["paymentSummary"]["difference"] == "-460.91"


def test_reconciliation_is_conservative_when_api_fields_are_missing():
    service = PeriodicAuditPdfReconciliationService()
    pdf = service.extract_text(TEXT, 6)
    result = service.reconcile(
        pdf,
        {"sangriaIntelligence": {"fluxo": {"SANGRIA": {"valor": 15499.76}}}},
    )
    assert result["status"] == "MATCH"
    assert result["automaticApprovalAllowed"] is False
    assert result["comparisons"][0]["status"] == "MATCH"
    assert result["comparisons"][1]["status"] == "API_VALUE_UNAVAILABLE"
