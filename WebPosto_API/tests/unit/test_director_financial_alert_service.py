from src.domain.financial_reconciliation import CoverageStatus, FinancialCoverage, FinancialSource
from src.services.director_financial_alert_service import DirectorFinancialAlertService


def test_incomplete_coverage_creates_critical_blocker() -> None:
    alerts = DirectorFinancialAlertService().evaluate([
        FinancialCoverage(source=FinancialSource.ACCOUNT_MOVEMENT, complete=False,
                          records=200, strategy="COMPANY_DAY_CURSOR",
                          status=CoverageStatus.INCOMPLETE_COVERAGE)
    ], [])
    assert alerts[0].alert_type == "COBERTURA_INCOMPLETA"
    assert alerts[0].severity.value == "CRITICA"
    assert alerts[0].affects_dre is False


def test_department_exceptions_generate_separate_alerts() -> None:
    alerts = DirectorFinancialAlertService().evaluate([], [{
        "companyCode": 11495,
        "department": "combustiveis",
        "quarantined": 2,
        "duplicates": 1,
        "probableMatches": 3,
        "unmatched": 4,
    }])
    assert {alert.alert_type for alert in alerts} == {
        "CLASSIFICACAO_PENDENTE", "DUPLICIDADE_POTENCIAL",
        "CONCILIACAO_PROVAVEL", "SEM_CORRESPONDENCIA",
    }
    assert all(alert.affects_dre is False for alert in alerts)
