"""Alertas determinísticos da conciliação, sem inferência de fraude."""

from src.domain.financial_reconciliation import (
    ExecutiveAlertSeverity,
    ExecutiveFinancialAlert,
    FinancialCoverage,
)


class DirectorFinancialAlertService:
    def evaluate(
        self,
        coverage: list[FinancialCoverage],
        executive_summary: list[dict],
    ) -> list[ExecutiveFinancialAlert]:
        alerts: list[ExecutiveFinancialAlert] = []
        incomplete = [item for item in coverage if not item.complete]
        if incomplete:
            alerts.append(ExecutiveFinancialAlert(
                alert_id="coverage:blocked",
                alert_type="COBERTURA_INCOMPLETA",
                severity=ExecutiveAlertSeverity.CRITICAL,
                occurrences=len(incomplete),
                explanation="Uma ou mais fontes não possuem cobertura integral comprovada.",
                recommended_action="Reprocessar as partições antes de liberar totais executivos.",
            ))
        for row in executive_summary:
            company = int(row["companyCode"])
            department = str(row["department"])
            rules = (
                ("quarantined", "CLASSIFICACAO_PENDENTE", ExecutiveAlertSeverity.HIGH,
                 "Registros aguardam classificação departamental.",
                 "Revisar plano de contas e centro de custo no WebPosto."),
                ("duplicates", "DUPLICIDADE_POTENCIAL", ExecutiveAlertSeverity.HIGH,
                 "Registros com a mesma evidência foram isolados como duplicidade.",
                 "Validar o documento de origem antes de qualquer contabilização."),
                ("probableMatches", "CONCILIACAO_PROVAVEL", ExecutiveAlertSeverity.MEDIUM,
                 "Correspondências possuem valor e data, mas faltam referências suficientes.",
                 "Anexar documento ou confirmar plano de contas para elevar a confiança."),
                ("unmatched", "SEM_CORRESPONDENCIA", ExecutiveAlertSeverity.MEDIUM,
                 "Fatos financeiros não possuem vínculo suficiente com outra fonte.",
                 "Investigar origem, documento e evento de pagamento."),
            )
            for field, alert_type, severity, explanation, action in rules:
                count = int(row.get(field) or 0)
                if count <= 0:
                    continue
                alerts.append(ExecutiveFinancialAlert(
                    alert_id=f"{alert_type}:{company}:{department}",
                    alert_type=alert_type,
                    severity=severity,
                    company_code=company,
                    department=department,
                    occurrences=count,
                    explanation=explanation,
                    recommended_action=action,
                ))
        return alerts
