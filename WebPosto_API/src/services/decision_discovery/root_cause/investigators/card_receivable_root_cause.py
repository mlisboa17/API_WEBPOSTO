"""Card Receivable Root Cause — VALUE-04."""

from __future__ import annotations

from typing import Any, Dict, List

from src.services.decision_discovery.models import DecisionCandidate
from src.services.decision_discovery.root_cause.base_investigator import BaseRootCauseInvestigator
from src.services.decision_discovery.root_cause.models import (
    CauseCertainty,
    CauseProbability,
    CauseType,
    Investigation,
    Recommendation,
    RootCauseAnalysis,
)


class CardReceivableRootCause(BaseRootCauseInvestigator):
    def __init__(self) -> None:
        super().__init__(investigator_name="CardReceivableRootCause")

    async def investigate(self, decision: DecisionCandidate, **kwargs: Any) -> RootCauseAnalysis:
        evidence = decision.evidence or {}
        baseline = decision.baseline_used or {}
        investigations = [
            self._investigate_gap(evidence, baseline),
            self._investigate_concentration(evidence),
            self._investigate_overdue(evidence),
            self._investigate_reconciliation_level(evidence),
        ]
        causes = self._analyze_causes(investigations, evidence)
        most_probable = max(causes, key=lambda c: c.probability) if causes else None
        recommendations = self._generate_recommendations(most_probable, evidence, decision)
        overall, explanation = self._calc_confidence(investigations, most_probable)
        return RootCauseAnalysis(
            decision_id=decision.id,
            investigator_name=self.investigator_name,
            problem_summary=decision.title,
            financial_impact=decision.money_found.total_impact(),
            investigations=investigations,
            most_probable_cause=most_probable,
            alternative_causes=[c for c in causes if c != most_probable],
            discarded_hypotheses=[
                "Gap de cartão TEF descartado (sem NSU/bandeira/adquirente)",
                "Movimento bancário isolado descartado como prova titulo a titulo",
            ],
            recommendations=recommendations,
            overall_confidence=overall,
            confidence_explanation=explanation,
            data_sources_used=decision.source_endpoints,
            insufficient_data_message=None if most_probable else "Dados insuficientes para causa provável.",
        )

    def _investigate_gap(self, evidence: Dict, baseline: Dict) -> Investigation:
        expected = float(baseline.get("expected_value") or evidence.get("expected_value") or 0)
        settled = float(baseline.get("settled_value") or evidence.get("settled_value") or 0)
        gap = float(baseline.get("gap_value") or evidence.get("gap_value") or 0)
        finding = (
            f"Esperado (pendente) R$ {expected:,.2f}; liquidação registrada R$ {settled:,.2f}; "
            f"gap estimado R$ {gap:,.2f}"
        )
        return Investigation(
            aspect="Gap financeiro",
            finding=finding,
            evidence={"expected": expected, "settled": settled, "gap": gap},
            contribution_to_problem=min(1.0, gap / expected) if expected > 0 else 0.5,
            confidence=0.88,
        )

    def _investigate_concentration(self, evidence: Dict) -> Investigation:
        share = float(evidence.get("top_client_share") or 0)
        if share > 0.5:
            finding = f"{share:.0%} do valor vencido concentrado no maior cliente"
        else:
            finding = "Valor vencido distribuído entre múltiplos clientes"
        return Investigation(
            aspect="Concentração",
            finding=finding,
            evidence={"top_client_share": share},
            contribution_to_problem=share,
            confidence=0.82,
        )

    def _investigate_overdue(self, evidence: Dict) -> Investigation:
        count = int(evidence.get("overdue_count") or 0)
        days = float(evidence.get("avg_overdue_days") or 0)
        finding = f"{count} recebível(is) vencido(s); atraso médio {days:.0f} dia(s)"
        return Investigation(
            aspect="Vencimento",
            finding=finding,
            evidence={"count": count, "avg_days": days},
            contribution_to_problem=min(1.0, days / 30.0),
            confidence=0.9,
        )

    def _investigate_reconciliation_level(self, evidence: Dict) -> Investigation:
        level = evidence.get("reconciliation_level", 1)
        finding = f"Reconciliation LEVEL {level} — comparação agregada, sem vínculo transacional TEF"
        return Investigation(
            aspect="Nível de prova",
            finding=finding,
            evidence={"level": level, "limitation": evidence.get("limitation")},
            contribution_to_problem=0.4,
            confidence=0.95,
        )

    def _analyze_causes(self, investigations: List[Investigation], evidence: Dict) -> List[CauseProbability]:
        share = float(evidence.get("top_client_share") or 0)
        count = int(evidence.get("overdue_count") or 0)
        causes: List[CauseProbability] = []
        if share >= 0.5:
            causes.append(
                CauseProbability(
                    cause_type=CauseType.OPERATIONAL,
                    description="Concentração de recebíveis vencidos em poucos clientes/contratos prazo",
                    probability=min(0.82, 0.55 + share * 0.3),
                    certainty=CauseCertainty.PROBABLE,
                    supporting_evidence=[f"Concentração {share:.0%}", f"{count} títulos vencidos"],
                    contradicting_evidence=["Pode ser prazo comercial normal"],
                )
            )
        causes.append(
            CauseProbability(
                cause_type=CauseType.OPERATIONAL,
                description="Ausência de baixa contábil em títulos já vencidos",
                probability=0.78,
                certainty=CauseCertainty.PROBABLE,
                supporting_evidence=[str(evidence.get("limitation", "")), f"Atraso médio {evidence.get('avg_overdue_days', 0)} dias"],
                contradicting_evidence=["Baixa pode estar pendente de lançamento no ERP"],
            )
        )
        return causes

    def _generate_recommendations(
        self,
        cause: CauseProbability | None,
        evidence: Dict,
        decision: DecisionCandidate,
    ) -> List[Recommendation]:
        if not cause:
            return []
        count = int(evidence.get("overdue_count") or 10)
        return [
            Recommendation(
                action=f"Revisar os {min(count, 10)} maiores títulos vencidos sem baixa ({decision.period_start} a {decision.period_end})",
                estimated_time_minutes=20,
                expected_impact="Alto",
                priority=1,
                why="Gap estimado baseado em títulos vencidos com pendente=true",
            ),
            Recommendation(
                action="Conferir documentos/duplicatas dos clientes concentrados no extrato ERP",
                estimated_time_minutes=15,
                expected_impact="Médio",
                priority=2,
                why="Validar se prazo/contrato justifica pendência ou se falta baixa",
            ),
        ]

    def _calc_confidence(
        self,
        investigations: List[Investigation],
        cause: CauseProbability | None,
    ) -> tuple[float, str]:
        if not cause:
            return 0.0, "Dados insuficientes"
        inv_avg = sum(i.confidence for i in investigations) / len(investigations)
        overall = inv_avg * 0.4 + cause.probability * 0.5
        return overall, "Confiança moderada — LEVEL 1 agregado, validar baixas no ERP"
