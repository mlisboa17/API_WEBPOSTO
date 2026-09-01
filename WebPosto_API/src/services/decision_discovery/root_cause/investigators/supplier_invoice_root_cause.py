"""Supplier Invoice Root Cause Investigator."""

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


class SupplierInvoiceRootCause(BaseRootCauseInvestigator):
    """Investiga causa provável de NF de fornecedor sem histórico no baseline."""

    def __init__(self) -> None:
        super().__init__(investigator_name="SupplierInvoiceRootCause")

    async def investigate(self, decision: DecisionCandidate, **kwargs: Any) -> RootCauseAnalysis:
        try:
            evidence = decision.evidence or {}
            baseline = decision.baseline_used or {}
            investigations = [
                self._investigate_invoice(evidence, baseline),
                self._investigate_supplier(evidence),
                self._investigate_baseline_absence(evidence, baseline),
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

    def _investigate_invoice(self, evidence: Dict, baseline: Dict) -> Investigation:
        nf = evidence.get("nf_number") or "—"
        supplier = evidence.get("supplier") or "fornecedor"
        current = float(baseline.get("current_value") or 0)
        finding = (
            f"NF {nf} de {supplier}: R$ {current:,.2f} lançado sem despesa equivalente "
            f"no baseline de 30 dias"
        )
        return Investigation(
            aspect="Nota fiscal",
            finding=finding,
            evidence={"nf_number": nf, "supplier": supplier, "current_value": current},
            contribution_to_problem=0.85,
            confidence=0.9 if nf != "—" else 0.6,
        )

    def _investigate_supplier(self, evidence: Dict) -> Investigation:
        supplier = evidence.get("supplier")
        if not supplier:
            return Investigation(
                aspect="Fornecedor",
                finding="Fornecedor não identificado no lançamento",
                evidence={},
                contribution_to_problem=0.0,
                confidence=0.0,
            )
        return Investigation(
            aspect="Fornecedor",
            finding=f"Despesa concentrada no fornecedor {supplier} (primeira ocorrência no período)",
            evidence={"supplier": supplier},
            contribution_to_problem=0.75,
            confidence=0.88,
        )

    def _investigate_baseline_absence(self, evidence: Dict, baseline: Dict) -> Investigation:
        base_val = float(baseline.get("baseline_value") or 0)
        cur_n = int(evidence.get("current_count") or 0)
        finding = (
            f"{cur_n} lançamento(s) no período atual vs baseline R$ {base_val:,.2f} "
            f"(fornecedor sem histórico recente)"
        )
        return Investigation(
            aspect="Histórico",
            finding=finding,
            evidence={"baseline_value": base_val, "current_count": cur_n},
            contribution_to_problem=0.7 if base_val == 0 else 0.3,
            confidence=0.85,
        )

    def _analyze_causes(
        self,
        investigations: List[Investigation],
        evidence: Dict,
        baseline: Dict,
    ) -> List[CauseProbability]:
        supplier = evidence.get("supplier") or "fornecedor"
        nf = evidence.get("nf_number")
        causes: List[CauseProbability] = []
        causes.append(
            CauseProbability(
                cause_type=CauseType.OPERATIONAL,
                description=f"Nova compra/contrato com {supplier} (NF {nf or 'referenciada'})",
                probability=0.76,
                certainty=CauseCertainty.PROBABLE,
                supporting_evidence=[
                    f"NF {nf}" if nf else "Referência NF no plano de contas",
                    f"Baseline R$ {float(baseline.get('baseline_value') or 0):,.2f}",
                    f"Valor atual R$ {float(baseline.get('current_value') or 0):,.2f}",
                ],
                contradicting_evidence=["Pode ser reposição legítima não recorrente no baseline"],
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
        supplier = evidence.get("supplier") or "fornecedor"
        nf = evidence.get("nf_number") or "NF"
        return [
            Recommendation(
                action=f"Conferir NF {nf} e nota de entrada de {supplier} no ERP",
                estimated_time_minutes=15,
                expected_impact="Alto",
                priority=1,
                why="Lançamento sem histórico no baseline — validar pedido e recebimento",
            ),
            Recommendation(
                action=f"Comparar preço da NF {nf} com as 3 últimas compras de {supplier}",
                estimated_time_minutes=10,
                expected_impact="Médio",
                priority=2,
                why="Descartar aumento de custo antes de tratar como anomalia",
            ),
        ]

    def _calculate_analysis_confidence(
        self,
        investigations: List[Investigation],
        cause: CauseProbability | None,
    ) -> tuple[float, str]:
        if not cause:
            return 0.0, "Dados insuficientes para determinar causa provável"
        inv_confidence = sum(i.confidence for i in investigations) / len(investigations)
        overall = inv_confidence * 0.4 + cause.probability * 0.5 + 0.1
        if overall >= 0.80:
            explanation = "Confiança moderada-alta: NF rastreável sem histórico no baseline"
        else:
            explanation = "Confiança moderada: validar documentos antes de agir"
        return overall, explanation

    def _document_discarded_hypotheses(self, evidence: Dict) -> List[str]:
        discarded = ["Duplicidade confirmada descartada (sem par no mesmo período)"]
        if not evidence.get("nf_number"):
            discarded.append("Rastreio por número de NF limitado (referência incompleta)")
        return discarded
