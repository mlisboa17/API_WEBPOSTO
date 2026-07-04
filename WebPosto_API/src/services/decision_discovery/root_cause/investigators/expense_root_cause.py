"""Expense Root Cause Investigator — VALUE-03."""

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


class ExpenseRootCause(BaseRootCauseInvestigator):
    """Investiga causa provável de anomalias em despesas operacionais."""

    def __init__(self) -> None:
        super().__init__(investigator_name="ExpenseRootCause")

    async def investigate(self, decision: DecisionCandidate, **kwargs: Any) -> RootCauseAnalysis:
        try:
            evidence = decision.evidence or {}
            baseline = decision.baseline_used or {}
            investigations = [
                self._investigate_category(evidence, baseline),
                self._investigate_supplier(evidence),
                self._investigate_frequency(evidence, baseline),
                self._investigate_anomaly_type(evidence),
            ]
            causes = self._analyze_causes(investigations, evidence, baseline)
            most_probable = max(causes, key=lambda c: c.probability) if causes else None
            alternatives = [c for c in causes if c != most_probable]
            recommendations = self._generate_recommendations(most_probable, evidence, decision)
            overall_confidence, confidence_explanation = self._calculate_analysis_confidence(
                investigations, most_probable
            )
            return RootCauseAnalysis(
                decision_id=decision.id,
                investigator_name=self.investigator_name,
                problem_summary=decision.title,
                financial_impact=decision.money_found.total_impact(),
                investigations=investigations,
                most_probable_cause=most_probable,
                alternative_causes=alternatives,
                discarded_hypotheses=self._document_discarded_hypotheses(evidence),
                recommendations=recommendations,
                overall_confidence=overall_confidence,
                confidence_explanation=confidence_explanation,
                data_sources_used=decision.source_endpoints,
                insufficient_data_message=None
                if most_probable
                else "Dados insuficientes para determinar causa provável com confidence >= 60%.",
            )
        except Exception as exc:
            return RootCauseAnalysis(
                decision_id=decision.id,
                investigator_name=self.investigator_name,
                problem_summary=decision.title,
                financial_impact=decision.money_found.total_impact(),
                investigations=[],
                most_probable_cause=None,
                alternative_causes=[],
                discarded_hypotheses=[],
                recommendations=[],
                overall_confidence=0.0,
                confidence_explanation="Erro na investigação",
                data_sources_used=decision.source_endpoints,
                insufficient_data_message=f"Erro ao investigar causa: {exc}",
            )

    def _investigate_category(self, evidence: Dict, baseline: Dict) -> Investigation:
        category = evidence.get("category") or evidence.get("label") or "categoria não informada"
        current = float(baseline.get("current_value") or 0)
        base = float(baseline.get("baseline_value") or 0)
        excess = max(0.0, current - base)
        finding = (
            f"{category}: R$ {current:,.2f} no período atual vs R$ {base:,.2f} no baseline "
            f"(excesso estimado R$ {excess:,.2f})"
        )
        contribution = min(1.0, excess / current) if current > 0 else 0.0
        return Investigation(
            aspect="Categoria",
            finding=finding,
            evidence={"category": category, "current": current, "baseline": base, "excess": excess},
            contribution_to_problem=contribution,
            confidence=0.9 if category != "categoria não informada" else 0.5,
        )

    def _investigate_supplier(self, evidence: Dict) -> Investigation:
        supplier = evidence.get("supplier")
        if not supplier:
            return Investigation(
                aspect="Fornecedor",
                finding="Fornecedor não identificado no lançamento principal",
                evidence={},
                contribution_to_problem=0.0,
                confidence=0.0,
            )
        return Investigation(
            aspect="Fornecedor",
            finding=f"Fornecedor {supplier} concentrou parte relevante do aumento sinalizado",
            evidence={"supplier": supplier},
            contribution_to_problem=0.7,
            confidence=0.85,
        )

    def _investigate_frequency(self, evidence: Dict, baseline: Dict) -> Investigation:
        cur_n = int(evidence.get("current_count") or 0)
        base_n = int(evidence.get("baseline_count") or 0)
        if cur_n or base_n:
            finding = f"{cur_n} lançamentos no período atual vs {base_n} no baseline"
            contribution = min(1.0, abs(cur_n - base_n) / max(base_n, 1))
        else:
            finding = "Frequência de lançamentos não disponível"
            contribution = 0.0
        return Investigation(
            aspect="Frequência",
            finding=finding,
            evidence={"current_count": cur_n, "baseline_count": base_n},
            contribution_to_problem=contribution,
            confidence=0.8 if cur_n or base_n else 0.3,
        )

    def _investigate_anomaly_type(self, evidence: Dict) -> Investigation:
        anomaly = evidence.get("anomaly_type") or "CATEGORY_SPIKE"
        if anomaly == "DUPLICATE_PAYMENT_SIGNAL":
            pairs = evidence.get("pairs", 0)
            finding = f"Sinal de possível duplicidade: {pairs} lançamentos com mesmo valor/categoria"
            contribution = 0.85
        elif anomaly == "SUPPLIER_SPIKE":
            finding = "Aumento concentrado em fornecedor específico"
            contribution = 0.75
        else:
            finding = "Aumento agregado por categoria acima do comportamento de referência"
            contribution = 0.65
        return Investigation(
            aspect="Tipo de anomalia",
            finding=finding,
            evidence={"anomaly_type": anomaly},
            contribution_to_problem=contribution,
            confidence=0.85,
        )

    def _analyze_causes(
        self,
        investigations: List[Investigation],
        evidence: Dict,
        baseline: Dict,
    ) -> List[CauseProbability]:
        causes: List[CauseProbability] = []
        anomaly = evidence.get("anomaly_type", "CATEGORY_SPIKE")
        category = evidence.get("category") or evidence.get("label")
        supplier = evidence.get("supplier")
        cur_n = int(evidence.get("current_count") or 0)
        base_n = int(evidence.get("baseline_count") or 0)

        if anomaly == "DUPLICATE_PAYMENT_SIGNAL":
            causes.append(
                CauseProbability(
                    cause_type=CauseType.UNKNOWN,
                    description="Possível duplicidade de lançamento (mesmo valor/categoria em datas próximas)",
                    probability=0.72,
                    certainty=CauseCertainty.POSSIBLE,
                    supporting_evidence=[
                        f"{evidence.get('pairs', 0)} ocorrências com valor R$ {evidence.get('valor', 0):,.2f}",
                        evidence.get("note", "Requer conferência documental"),
                    ],
                    contradicting_evidence=["Sem confirmação de nota fiscal duplicada"],
                )
            )
            return causes

        if supplier and anomaly == "SUPPLIER_SPIKE":
            causes.append(
                CauseProbability(
                    cause_type=CauseType.OPERATIONAL,
                    description=f"Concentração de gasto no fornecedor {supplier}",
                    probability=0.78,
                    certainty=CauseCertainty.PROBABLE,
                    supporting_evidence=[f"Fornecedor: {supplier}", "Aumento acima do baseline de 30 dias"],
                    contradicting_evidence=[],
                )
            )

        if category and cur_n > base_n * 1.5 and base_n > 0:
            share = (cur_n - base_n) / max(cur_n, 1)
            causes.append(
                CauseProbability(
                    cause_type=CauseType.OPERATIONAL,
                    description=f"Maior volume de lançamentos em {category}",
                    probability=min(0.82, 0.55 + share * 0.4),
                    certainty=CauseCertainty.PROBABLE,
                    supporting_evidence=[
                        f"{cur_n} lançamentos vs média histórica de {base_n}",
                        f"Categoria: {category}",
                    ],
                    contradicting_evidence=[],
                )
            )
        elif category:
            causes.append(
                CauseProbability(
                    cause_type=CauseType.OPERATIONAL,
                    description=f"Aumento de valor agregado em {category}",
                    probability=0.7,
                    certainty=CauseCertainty.PROBABLE,
                    supporting_evidence=[
                        f"Valor atual R$ {baseline.get('current_value', 0):,.2f}",
                        f"Baseline R$ {baseline.get('baseline_value', 0):,.2f}",
                    ],
                    contradicting_evidence=["Pode refletir contrato/sazonalidade legítima"],
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
        category = evidence.get("category") or evidence.get("label") or "categoria sinalizada"
        supplier = evidence.get("supplier")
        recs: List[Recommendation] = []

        if cause.cause_type == CauseType.UNKNOWN and evidence.get("anomaly_type") == "DUPLICATE_PAYMENT_SIGNAL":
            recs.append(
                Recommendation(
                    action=f"Conferir notas/documentos dos lançamentos duplicados em {category}",
                    estimated_time_minutes=20,
                    expected_impact="Alto",
                    priority=1,
                    why="Sinal de possível duplicidade — validação documental necessária",
                )
            )
        elif supplier:
            recs.append(
                Recommendation(
                    action=f"Revisar os 5 maiores títulos do fornecedor {supplier} no período",
                    estimated_time_minutes=15,
                    expected_impact="Alto",
                    priority=1,
                    why="Fornecedor concentrou aumento acima do baseline",
                )
            )
        else:
            recs.append(
                Recommendation(
                    action=f"Revisar os 5 maiores lançamentos de {category} ({decision.period_start} a {decision.period_end})",
                    estimated_time_minutes=15,
                    expected_impact="Alto",
                    priority=1,
                    why="Categoria respondeu pela maior parte do excesso estimado",
                )
            )
        recs.append(
            Recommendation(
                action="Validar se os serviços/produtos correspondem a ordens ou contratos ativos",
                estimated_time_minutes=10,
                expected_impact="Médio",
                priority=2,
                why="Descartar aumento legítimo antes de tratar como perda",
            )
        )
        return recs

    def _calculate_analysis_confidence(
        self,
        investigations: List[Investigation],
        cause: CauseProbability | None,
    ) -> tuple[float, str]:
        if not cause:
            return 0.0, "Dados insuficientes para determinar causa provável"
        inv_confidence = sum(i.confidence for i in investigations) / len(investigations)
        overall = inv_confidence * 0.4 + cause.probability * 0.5 + min(len(cause.supporting_evidence) / 4, 1.0) * 0.1
        if overall >= 0.85:
            explanation = "Alta confiança: evidências de despesa consistentes com baseline"
        elif overall >= 0.70:
            explanation = "Confiança moderada-alta: padrão de aumento identificado"
        else:
            explanation = "Confiança moderada: validar com documentos antes de agir"
        return overall, explanation

    def _document_discarded_hypotheses(self, evidence: Dict) -> List[str]:
        discarded = []
        if evidence.get("anomaly_type") != "DUPLICATE_PAYMENT_SIGNAL":
            discarded.append("Duplicidade confirmada descartada (apenas sinal, sem prova documental)")
        if not evidence.get("supplier"):
            discarded.append("Concentração por fornecedor descartada (dado não disponível no lançamento principal)")
        return discarded
