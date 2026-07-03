"""
Fuel Revenue Root Cause Investigator — VALUE-02

Investiga causa raiz de quedas de receita em combustíveis.

Investigações realizadas:
1. Produto afetado
2. Volume/litros
3. Preço médio
4. Margem (se disponível)
5. Tenant/posto
6. Período
7. Baseline
8. Dia da semana
9. Faixa horária (se disponível)
10. Hipóteses descartadas
"""

from __future__ import annotations

import uuid
from typing import Dict, Any, List

from src.services.decision_discovery.models import DecisionCandidate
from src.services.decision_discovery.root_cause.base_investigator import BaseRootCauseInvestigator
from src.services.decision_discovery.root_cause.models import (
    RootCauseAnalysis,
    Investigation,
    CauseProbability,
    Recommendation,
    CauseType,
    CauseCertainty,
)


class FuelRevenueRootCause(BaseRootCauseInvestigator):
    """
    Investigador de causa raiz para quedas de receita em combustíveis.
    
    Responde:
    - O que aconteceu? → Queda de X% em produto Y
    - Onde? → POSTO Z
    - Quando? → Período específico, horário, dia da semana
    - Quanto? → R$ valor
    - Causa provável? → Baseada em evidências
    - O que fazer? → Recomendações específicas
    """
    
    def __init__(self):
        super().__init__(investigator_name="FuelRevenueRootCause")
    
    async def investigate(
        self,
        decision: DecisionCandidate,
        **kwargs: Any
    ) -> RootCauseAnalysis:
        """
        Investiga causa raiz de queda de receita em combustíveis.
        
        Args:
            decision: Decisão detectada pelo Discovery Engine
        
        Returns:
            RootCauseAnalysis completo
        """
        try:
            self.log("investigation_started", {"decision_id": decision.id})
            
            # 1. Extrair dados da decisão
            evidence = decision.evidence
            baseline = decision.baseline_used
            
            # 2. Realizar investigações
            investigations = []
            
            # Investigação 1: Produto
            product_inv = self._investigate_product(evidence, baseline)
            investigations.append(product_inv)
            
            # Investigação 2: Volume
            volume_inv = self._investigate_volume(evidence, baseline)
            investigations.append(volume_inv)
            
            # Investigação 3: Preço
            price_inv = self._investigate_price(evidence, baseline)
            investigations.append(price_inv)
            
            # Investigação 4: Margem
            margin_inv = self._investigate_margin(evidence, baseline)
            investigations.append(margin_inv)
            
            # Investigação 5: Temporal
            temporal_inv = self._investigate_temporal(evidence)
            investigations.append(temporal_inv)
            
            # 3. Determinar causa provável
            cause_candidates = self._analyze_causes(investigations, evidence, baseline)
            
            most_probable = max(cause_candidates, key=lambda c: c.probability) if cause_candidates else None
            alternatives = [c for c in cause_candidates if c != most_probable]
            
            # 4. Gerar recomendações
            recommendations = self._generate_recommendations(most_probable, evidence)
            
            # 5. Calcular confidence
            overall_confidence, confidence_explanation = self._calculate_analysis_confidence(
                investigations, most_probable
            )
            
            # 6. Documentar hipóteses descartadas
            discarded = self._document_discarded_hypotheses(evidence, baseline)
            
            # 7. Criar análise
            analysis = RootCauseAnalysis(
                decision_id=decision.id,
                investigator_name=self.investigator_name,
                problem_summary=decision.title,
                financial_impact=decision.money_found.total_impact(),
                investigations=investigations,
                most_probable_cause=most_probable,
                alternative_causes=alternatives,
                discarded_hypotheses=discarded,
                recommendations=recommendations,
                overall_confidence=overall_confidence,
                confidence_explanation=confidence_explanation,
                data_sources_used=decision.source_endpoints,
                insufficient_data_message=None if most_probable else "Dados insuficientes para determinar causa provável com confidence >= 60%.",
            )
            
            self.log("investigation_completed", {
                "has_cause": most_probable is not None,
                "confidence": overall_confidence,
            })
            
            return analysis
            
        except Exception as e:
            self.log("investigation_error", {"error": str(e)})
            
            # Retornar análise indicando dados insuficientes
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
                data_sources_used=[],
                insufficient_data_message=f"Erro ao investigar causa: {str(e)}",
            )
    
    def _investigate_product(self, evidence: Dict, baseline: Dict) -> Investigation:
        """Investiga produto afetado."""
        product_name = evidence.get("product_name", "Combustível não especificado")
        product_drop_pct = evidence.get("product_drop_pct", 0.0)
        
        finding = f"{product_name} apresentou queda de {product_drop_pct:.1%} no período"
        
        return Investigation(
            aspect="Produto",
            finding=finding,
            evidence={"product": product_name, "drop_pct": product_drop_pct},
            contribution_to_problem=abs(product_drop_pct),
            confidence=0.95,  # Dados diretos
        )
    
    def _investigate_volume(self, evidence: Dict, baseline: Dict) -> Investigation:
        """Investiga volume/litros."""
        current_volume = evidence.get("current_volume", 0)
        previous_volume = evidence.get("previous_volume", 0)
        
        if previous_volume > 0:
            volume_change_pct = (current_volume - previous_volume) / previous_volume
            finding = f"Volume vendido caiu de {previous_volume:,.0f}L para {current_volume:,.0f}L ({volume_change_pct:.1%})"
        else:
            volume_change_pct = 0
            finding = "Dados de volume insuficientes"
        
        return Investigation(
            aspect="Volume",
            finding=finding,
            evidence={"current": current_volume, "previous": previous_volume, "change_pct": volume_change_pct},
            contribution_to_problem=abs(volume_change_pct),
            confidence=0.90,
        )
    
    def _investigate_price(self, evidence: Dict, baseline: Dict) -> Investigation:
        """Investiga preço médio."""
        current_price = evidence.get("current_price", 0)
        previous_price = evidence.get("previous_price", 0)
        
        if previous_price > 0:
            price_change_pct = (current_price - previous_price) / previous_price
            
            if price_change_pct > 0.05:
                finding = f"Preço subiu {price_change_pct:.1%} (de R$ {previous_price:.2f} para R$ {current_price:.2f})"
                contribution = 0.80  # Alta contribuição se preço subiu significativamente
            elif abs(price_change_pct) < 0.02:
                finding = f"Preço permaneceu estável (variação de {price_change_pct:.1%})"
                contribution = 0.10
            else:
                finding = f"Preço variou {price_change_pct:.1%}"
                contribution = 0.40
        else:
            finding = "Dados de preço insuficientes"
            contribution = 0.0
            price_change_pct = 0
        
        return Investigation(
            aspect="Preço",
            finding=finding,
            evidence={"current": current_price, "previous": previous_price, "change_pct": price_change_pct},
            contribution_to_problem=contribution,
            confidence=0.85,
        )
    
    def _investigate_margin(self, evidence: Dict, baseline: Dict) -> Investigation:
        """Investiga margem (se disponível)."""
        current_margin = evidence.get("current_margin", None)
        previous_margin = evidence.get("previous_margin", None)
        
        if current_margin is not None and previous_margin is not None:
            margin_change = current_margin - previous_margin
            
            if abs(margin_change) < 0.02:
                finding = f"Margem permaneceu estável (~{current_margin:.1%})"
                contribution = 0.10
            else:
                finding = f"Margem variou de {previous_margin:.1%} para {current_margin:.1%}"
                contribution = 0.50
            
            confidence = 0.80
        else:
            finding = "Dados de margem não disponíveis"
            contribution = 0.0
            confidence = 0.0
        
        return Investigation(
            aspect="Margem",
            finding=finding,
            evidence={"current": current_margin, "previous": previous_margin},
            contribution_to_problem=contribution,
            confidence=confidence,
        )
    
    def _investigate_temporal(self, evidence: Dict) -> Investigation:
        """Investiga padrão temporal."""
        days_impacted = evidence.get("days_impacted", 7)
        time_pattern = evidence.get("time_pattern", "Distribuído ao longo do dia")
        
        finding = f"Queda observada por {days_impacted} dias consecutivos. {time_pattern}"
        
        return Investigation(
            aspect="Temporal",
            finding=finding,
            evidence={"days": days_impacted, "pattern": time_pattern},
            contribution_to_problem=min(days_impacted / 7, 1.0),
            confidence=0.75,
        )
    
    def _analyze_causes(
        self,
        investigations: List[Investigation],
        evidence: Dict,
        baseline: Dict
    ) -> List[CauseProbability]:
        """Analisa investigações e determina causas prováveis."""
        causes = []
        
        # Extrair dados
        price_inv = next((inv for inv in investigations if inv.aspect == "Preço"), None)
        volume_inv = next((inv for inv in investigations if inv.aspect == "Volume"), None)
        margin_inv = next((inv for inv in investigations if inv.aspect == "Margem"), None)
        
        if not price_inv or not volume_inv:
            return []
        
        price_change = price_inv.evidence.get("change_pct", 0)
        volume_change = volume_inv.evidence.get("change_pct", 0)
        margin_stable = margin_inv and abs(margin_inv.evidence.get("current", 0) - margin_inv.evidence.get("previous", 0)) < 0.02 if margin_inv.evidence.get("current") else False
        
        # Causa 1: Preço acima do mercado
        if price_change > 0.03 and volume_change < -0.10:
            supporting = [
                f"Preço subiu {price_change:.1%}",
                f"Volume caiu {abs(volume_change):.1%}",
            ]
            if margin_stable:
                supporting.append("Margem permaneceu estável (indica que preço subiu, não custo)")
            
            probability = min(0.85, 0.60 + (price_change * 2) + (abs(volume_change) * 1))
            certainty = CauseCertainty.PROBABLE if probability >= 0.70 else CauseCertainty.POSSIBLE
            
            causes.append(CauseProbability(
                cause_type=CauseType.PRICE,
                description="Preço acima do comportamento de mercado/concorrência",
                probability=probability,
                certainty=certainty,
                supporting_evidence=supporting,
                contradicting_evidence=[],
            ))
        
        # Causa 2: Ruptura de estoque
        stock_rupture = evidence.get("stock_rupture", False)
        if stock_rupture or (volume_change < -0.30 and abs(price_change) < 0.02):
            causes.append(CauseProbability(
                cause_type=CauseType.STOCK,
                description="Possível ruptura ou indisponibilidade de estoque",
                probability=0.60,
                certainty=CauseCertainty.POSSIBLE,
                supporting_evidence=[f"Volume caiu drasticamente ({abs(volume_change):.1%})", "Preço não variou significativamente"],
                contradicting_evidence=["Não há confirmação direta de ruptura"],
            ))
        
        # Causa 3: Competição
        if abs(price_change) < 0.02 and volume_change < -0.15:
            causes.append(CauseProbability(
                cause_type=CauseType.COMPETITION,
                description="Possível perda para concorrência (preço ou promoção)",
                probability=0.55,
                certainty=CauseCertainty.POSSIBLE,
                supporting_evidence=["Preço interno estável", f"Volume caiu {abs(volume_change):.1%}"],
                contradicting_evidence=["Sem dados de preços de concorrentes"],
            ))
        
        return causes
    
    def _generate_recommendations(
        self,
        cause: CauseProbability | None,
        evidence: Dict
    ) -> List[Recommendation]:
        """Gera recomendações específicas baseadas na causa."""
        if not cause:
            return []
        
        recommendations = []
        product_name = evidence.get("product_name", "produto")
        
        if cause.cause_type == CauseType.PRICE:
            recommendations.extend([
                Recommendation(
                    action=f"Comparar preço do {product_name} com 3 concorrentes próximos",
                    estimated_time_minutes=10,
                    expected_impact="Alto",
                    priority=1,
                    why="Forte evidência de que preço elevado está causando perda de volume",
                ),
                Recommendation(
                    action=f"Revisar histórico de alterações de preço do {product_name} nos últimos 30 dias",
                    estimated_time_minutes=5,
                    expected_impact="Médio",
                    priority=2,
                    why="Identificar quando o preço foi alterado e correlacionar com queda",
                ),
                Recommendation(
                    action=f"Analisar margem atual do {product_name} vs target",
                    estimated_time_minutes=5,
                    expected_impact="Médio",
                    priority=3,
                    why="Avaliar se há espaço para redução de preço mantendo margem saudável",
                ),
            ])
        
        elif cause.cause_type == CauseType.STOCK:
            recommendations.extend([
                Recommendation(
                    action=f"Verificar status de estoque do {product_name} nos últimos 7 dias",
                    estimated_time_minutes=5,
                    expected_impact="Alto",
                    priority=1,
                    why="Confirmar se houve ruptura de estoque",
                ),
                Recommendation(
                    action="Revisar processo de reabastecimento com fornecedor",
                    estimated_time_minutes=15,
                    expected_impact="Alto",
                    priority=2,
                    why="Prevenir novas rupturas",
                ),
            ])
        
        elif cause.cause_type == CauseType.COMPETITION:
            recommendations.extend([
                Recommendation(
                    action=f"Pesquisar preços de {product_name} em 3-5 concorrentes próximos",
                    estimated_time_minutes=15,
                    expected_impact="Alto",
                    priority=1,
                    why="Identificar se concorrentes estão com preço mais competitivo",
                ),
                Recommendation(
                    action="Verificar se concorrentes lançaram promoções recentes",
                    estimated_time_minutes=10,
                    expected_impact="Médio",
                    priority=2,
                    why="Identificar ações promocionais da concorrência",
                ),
            ])
        
        return recommendations
    
    def _calculate_analysis_confidence(
        self,
        investigations: List[Investigation],
        cause: CauseProbability | None
    ) -> tuple[float, str]:
        """Calcula confidence geral da análise."""
        if not cause:
            return 0.0, "Dados insuficientes para determinar causa provável"
        
        # Confidence baseado em:
        # 1. Confidence médio das investigações
        # 2. Probability da causa
        # 3. Quantidade de evidências suportando
        
        inv_confidence = sum(inv.confidence for inv in investigations) / len(investigations) if investigations else 0
        cause_probability = cause.probability
        evidence_count = len(cause.supporting_evidence)
        
        overall = (inv_confidence * 0.40 + cause_probability * 0.50 + min(evidence_count / 5, 1.0) * 0.10)
        
        if overall >= 0.85:
            explanation = "Alta confiança: múltiplas evidências convergentes"
        elif overall >= 0.70:
            explanation = "Confiança moderada-alta: evidências consistentes"
        elif overall >= 0.60:
            explanation = "Confiança moderada: evidências razoáveis mas incompletas"
        else:
            explanation = "Confiança baixa: evidências insuficientes"
        
        return overall, explanation
    
    def _document_discarded_hypotheses(
        self,
        evidence: Dict,
        baseline: Dict
    ) -> List[str]:
        """Documenta hipóteses descartadas."""
        discarded = []
        
        # Verificar se margem variou (descarta "problema de custo")
        current_margin = evidence.get("current_margin")
        previous_margin = evidence.get("previous_margin")
        
        if current_margin is not None and previous_margin is not None:
            if abs(current_margin - previous_margin) < 0.02:
                discarded.append("Aumento de custo descartado (margem permaneceu estável)")
        
        # Verificar se foi apenas um dia (descarta "problema pontual")
        days_impacted = evidence.get("days_impacted", 7)
        if days_impacted >= 5:
            discarded.append("Problema pontual descartado (queda persistente por múltiplos dias)")
        
        # Verificar se afetou todos os produtos (descarta "problema geral do posto")
        product_drop_pct = evidence.get("product_drop_pct", 1.0)
        if product_drop_pct > 0.70:
            discarded.append("Problema geral do posto descartado (queda concentrada em produto específico)")
        
        return discarded
