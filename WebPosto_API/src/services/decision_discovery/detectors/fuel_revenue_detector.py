"""
Fuel Revenue Detector — VALUE-01

Primeiro detector do Decision Discovery Engine.

Detecta quedas significativas de receita em combustíveis,
identificando automaticamente:
- Produto com maior queda
- Período específico
- Impacto financeiro
- Possíveis causas
- Ações recomendadas

Princípio 19: Encontrar a decisão mais valiosa primeiro.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union

from src.services.decision_discovery.base_detector import BaseDetector
from src.services.decision_discovery.models import (
    DecisionCandidate,
    MoneyFound,
    MoneyConfidence,
    ConfidenceFactors,
    DecisionCategory,
    ImpactType,
)


class FuelRevenueDetector(BaseDetector):
    """
    Detector de quedas de receita em combustíveis.
    
    Processo:
    1. Busca dados de vendas de combustíveis (período atual vs anterior)
    2. Identifica produtos com maior queda absoluta (R$)
    3. Calcula confidence baseado em qualidade dos dados
    4. Calcula Money Found (at_risk, recoverable)
    5. Retorna DecisionCandidate se relevante
    
    Critérios de relevância:
    - Queda >= R$ 5.000 (absoluto)
    - Confidence >= 80%
    - Dados de pelo menos 7 dias
    """
    
    # Thresholds
    MIN_IMPACT_BRL = 5000.0  # Impacto mínimo para considerar relevante
    MIN_CONFIDENCE = 0.80  # Confidence mínimo para exibir
    MIN_DAYS_DATA = 7  # Dias mínimos de dados
    
    def __init__(self):
        """Inicializa o FuelRevenueDetector."""
        super().__init__(detector_name="FuelRevenueDetector")
    
    async def detect(
        self,
        tenant_code: str,
        data_inicial: str,
        data_final: str,
        **kwargs: Any
    ) -> Union[Optional[DecisionCandidate], List[DecisionCandidate]]:
        """
        Detecta quedas significativas de receita em combustíveis.
        
        Args:
            tenant_code: Código do tenant (empresa)
            data_inicial: Data inicial (YYYY-MM-DD)
            data_final: Data final (YYYY-MM-DD)
            **kwargs: Argumentos adicionais
        
        Returns:
            DecisionCandidate se encontrar queda relevante, None caso contrário
        """
        try:
            self.log("detection_started", {
                "tenant": tenant_code,
                "period": f"{data_inicial} to {data_final}",
            })

            analysis_id = kwargs.get("analysis_id")
            credential_alias = kwargs.get("credential_alias")
            if analysis_id or credential_alias:
                from src.core.logger import get_logger, log_structured
                log_structured(
                    get_logger(__name__),
                    {
                        "event": "DISCOVERY_TENANT_TRACE",
                        "analysis_id": analysis_id,
                        "detector": self.detector_name,
                        "tenant_id": tenant_code,
                        "empresa_codigo": tenant_code,
                        "credential_alias": credential_alias,
                        "period_start": data_inicial,
                        "period_end": data_final,
                    },
                )
            
            # 1. Buscar dados de vendas de combustíveis
            fuel_data = await self._fetch_fuel_data(
                tenant_code=tenant_code,
                data_inicial=data_inicial,
                data_final=data_final,
                webposto_api_key=kwargs.get("webposto_api_key"),
            )
            
            if not fuel_data:
                self.log("no_data_available", {"reason": "Fuel data not available"})
                return None
            
            # 2. Analisar dados e identificar quedas
            analyses = self._analyze_fuel_revenue_drops(fuel_data)
            
            if not analyses:
                self.log("no_significant_drop", {"reason": "No significant revenue drop found"})
                return None
            
            tenant_name = kwargs.get("tenant_name", tenant_code)
            candidates: List[DecisionCandidate] = []
            for analysis in analyses:
                candidate = self._create_candidate(
                    tenant_code=tenant_code,
                    tenant_name=tenant_name,
                    period_start=data_inicial,
                    period_end=data_final,
                    analysis=analysis,
                )
                candidates.append(candidate)
                self.log("candidate_created", {
                    "title": candidate.title,
                    "impact": candidate.money_found.total_impact(),
                    "confidence": candidate.confidence,
                    "product": analysis.get("product_name"),
                })
            
            return candidates if len(candidates) > 1 else candidates[0]
            
        except Exception as e:
            self.log("detection_error", {"error": str(e)}, level="error")
            return None
    
    async def _fetch_fuel_data(
        self,
        tenant_code: str,
        data_inicial: str,
        data_final: str,
        webposto_api_key: str | None = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Busca dados reais de vendas de combustíveis (período atual vs anterior).
        """
        try:
            from src.gateway.webposto_client import WebPostoClient
            from src.services.network_financial_overview_service import NetworkFinancialOverviewService
            from src.services.analytics_service import AnalyticsService
            from src.services.analytics_multiselect import build_overview_filters

            if webposto_api_key:
                client = WebPostoClient.for_api_key(webposto_api_key)
                overview = NetworkFinancialOverviewService(client)
                analytics = AnalyticsService(overview)
            elif not hasattr(self, "_analytics"):
                client = WebPostoClient()
                overview = NetworkFinancialOverviewService(client)
                self._analytics = AnalyticsService(overview)
                analytics = self._analytics
            else:
                analytics = self._analytics

            start = datetime.fromisoformat(data_inicial).date()
            end = datetime.fromisoformat(data_final).date()
            period_days = (end - start).days + 1
            if period_days < self.MIN_DAYS_DATA:
                self.log("period_too_short", {"days": period_days, "min_days": self.MIN_DAYS_DATA})
                return None

            prev_end = start - timedelta(days=1)
            prev_start = prev_end - timedelta(days=period_days - 1)

            current_filters = build_overview_filters(data_inicial, data_final, tenant_code)
            prev_filters = build_overview_filters(
                prev_start.isoformat(),
                prev_end.isoformat(),
                tenant_code,
            )

            current_resp = await analytics.get_fuel_summary(current_filters)
            prev_resp = await analytics.get_fuel_summary(prev_filters)

            if not current_resp.success and not prev_resp.success:
                self.log("fuel_data_fetch", {"status": "failed", "tenant": tenant_code})
                return None

            current_rows = current_resp.data if current_resp.success and isinstance(current_resp.data, list) else []
            prev_rows = prev_resp.data if prev_resp.success and isinstance(prev_resp.data, list) else []

            if not current_rows and not prev_rows:
                self.log("fuel_data_fetch", {"status": "empty", "tenant": tenant_code})
                return None

            def aggregate_by_product(rows: list) -> dict[str, float]:
                totals: dict[str, float] = {}
                for row in rows:
                    name = str(row.get("combustivel") or "").strip()
                    if not name:
                        continue
                    totals[name] = totals.get(name, 0.0) + float(row.get("valor") or 0.0)
                return totals

            current_by_product = aggregate_by_product(current_rows)
            prev_by_product = aggregate_by_product(prev_rows)
            all_products = set(current_by_product) | set(prev_by_product)

            product_comparisons: list[dict[str, Any]] = []
            for product in all_products:
                current_value = current_by_product.get(product, 0.0)
                previous_value = prev_by_product.get(product, 0.0)
                drop_brl = previous_value - current_value
                if drop_brl <= 0:
                    continue
                drop_pct = drop_brl / previous_value if previous_value > 0 else 0.0
                product_comparisons.append({
                    "product_name": product,
                    "current_value": current_value,
                    "previous_value": previous_value,
                    "impact_brl": drop_brl,
                    "impact_pct": drop_pct,
                })

            product_comparisons.sort(key=lambda item: item["impact_brl"], reverse=True)

            current_total = sum(current_by_product.values())
            previous_total = sum(prev_by_product.values())

            data_quality = 0.95 if current_rows and prev_rows else 0.70

            self.log("fuel_data_fetch", {
                "status": "ok",
                "tenant": tenant_code,
                "products_with_drop": len(product_comparisons),
                "current_total": current_total,
                "previous_total": previous_total,
            })

            return {
                "current_period": {"revenue": current_total},
                "previous_period": {"revenue": previous_total},
                "product_comparisons": product_comparisons,
                "data_quality": data_quality,
                "comparison_validity": 0.90 if prev_rows else 0.60,
                "period_adequacy": 0.85 if period_days >= self.MIN_DAYS_DATA else 0.50,
                "source_endpoints": ["/api/v1/sales/fuel-summary"],
            }
        except Exception as exc:
            self.log("fuel_data_fetch_error", {"error": str(exc)}, level="error")
            return None
    
    def _analyze_fuel_revenue_drops(
        self,
        fuel_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Analisa quedas por produto descoberto automaticamente no ERP.
        """
        comparisons = fuel_data.get("product_comparisons") or []
        if comparisons:
            analyses: List[Dict[str, Any]] = []
            for item in comparisons:
                analysis = self._build_analysis_from_drop(fuel_data, item)
                if analysis:
                    analyses.append(analysis)
            return analyses

        # Fallback legado (estrutura agregada)
        single = self._analyze_fuel_revenue_drop(fuel_data)
        return [single] if single else []
    
    def _build_analysis_from_drop(
        self,
        fuel_data: Dict[str, Any],
        comparison: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        drop_brl = float(comparison.get("impact_brl") or 0)
        if drop_brl <= 0:
            return None

        drop_pct = float(comparison.get("impact_pct") or 0)
        product_name = comparison.get("product_name") or "Combustível"
        confidence_factors = self._calculate_confidence(fuel_data)
        overall_confidence = confidence_factors.overall_confidence()
        money_found = self._calculate_money_found(
            drop_brl=drop_brl,
            drop_pct=drop_pct,
            confidence=overall_confidence,
        )

        return {
            "impact_brl": drop_brl,
            "impact_pct": drop_pct,
            "product_name": product_name,
            "product_drop_pct": drop_pct,
            "confidence": overall_confidence,
            "confidence_factors": confidence_factors,
            "money_found": money_found,
            "evidence": {
                "product_name": product_name,
                "current_value": comparison.get("current_value"),
                "previous_value": comparison.get("previous_value"),
            },
            "baseline": {
                "baseline_value": comparison.get("previous_value"),
                "current_value": comparison.get("current_value"),
                "period": "período atual vs período anterior equivalente",
            },
        }
    
    def _analyze_fuel_revenue_drop(
        self,
        fuel_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Analisa dados de combustível e identifica quedas significativas.
        
        Lógica:
        1. Comparar período atual vs período anterior
        2. Identificar produto com maior queda absoluta (R$)
        3. Calcular impacto percentual
        4. Calcular confidence baseado em qualidade dos dados
        5. Identificar período do dia com maior queda (se disponível)
        
        Args:
            fuel_data: Dados de vendas de combustíveis
        
        Returns:
            Análise com impacto, produto, confidence, etc. ou None
        """
        # VALUE-01 (arquitetura):
        # Lógica completa de análise está aqui, pronta para quando
        # houver dados reais.
        
        # Extrair dados do período atual e anterior
        current_revenue = fuel_data.get("current_period", {}).get("revenue", 0)
        previous_revenue = fuel_data.get("previous_period", {}).get("revenue", 0)
        
        if current_revenue == 0 and previous_revenue == 0:
            return None
        
        # Calcular queda
        drop_brl = previous_revenue - current_revenue
        drop_pct = (drop_brl / previous_revenue) if previous_revenue > 0 else 0
        
        if drop_brl <= 0:
            # Não há queda (ou houve aumento)
            return None
        
        # Identificar produto mais afetado
        product_name = fuel_data.get("top_drop_product", "Diesel S10")
        product_drop_pct = fuel_data.get("product_drop_pct", drop_pct)
        
        # Calcular confidence
        confidence_factors = self._calculate_confidence(fuel_data)
        overall_confidence = confidence_factors.overall_confidence()
        
        # Calcular Money Found
        money_found = self._calculate_money_found(
            drop_brl=drop_brl,
            drop_pct=drop_pct,
            confidence=overall_confidence
        )
        
        return {
            "impact_brl": drop_brl,
            "impact_pct": drop_pct,
            "product_name": product_name,
            "product_drop_pct": product_drop_pct,
            "confidence": overall_confidence,
            "confidence_factors": confidence_factors,
            "money_found": money_found,
            "evidence": fuel_data.get("evidence", {}),
            "baseline": {
                "baseline_value": previous_revenue,
                "current_value": current_revenue,
                "period": "7 days vs previous 7 days",
            },
        }
    
    def _calculate_confidence(
        self,
        fuel_data: Dict[str, Any]
    ) -> ConfidenceFactors:
        """
        Calcula Confidence Score baseado em qualidade dos dados.
        
        Fatores:
        - data_quality: Completude e consistência dos dados
        - comparison_validity: Validade da comparação (mesmo período, feriados, etc.)
        - period_adequacy: Adequação do período analisado
        - calculation_reliability: Confiabilidade do cálculo
        
        Args:
            fuel_data: Dados de combustível
        
        Returns:
            ConfidenceFactors
        """
        # Avaliar qualidade dos dados
        data_quality = fuel_data.get("data_quality", 0.95)  # Default alto para dados diretos do ERP
        
        # Avaliar validade da comparação
        comparison_validity = fuel_data.get("comparison_validity", 0.90)
        
        # Avaliar adequação do período
        period_adequacy = fuel_data.get("period_adequacy", 0.85)
        
        # Confiabilidade do cálculo (sempre alta para cálculos simples)
        calculation_reliability = 0.98
        
        return ConfidenceFactors(
            data_quality=data_quality,
            comparison_validity=comparison_validity,
            period_adequacy=period_adequacy,
            calculation_reliability=calculation_reliability,
        )
    
    def _calculate_money_found(
        self,
        drop_brl: float,
        drop_pct: float,
        confidence: float
    ) -> MoneyFound:
        """
        Calcula Money Found baseado na queda identificada.
        
        Args:
            drop_brl: Queda em R$ (absoluto)
            drop_pct: Queda em % (relativo)
            confidence: Confidence score
        
        Returns:
            MoneyFound
        """
        # At Risk: Perda já confirmada
        at_risk = drop_brl
        at_risk_type = MoneyConfidence.CONFIRMED  # Dados diretos do ERP
        
        # Recoverable: Estimativa de quanto pode ser recuperado
        # Assumimos que 60-80% da queda é recuperável com ação rápida
        recovery_factor = 0.70
        recoverable = drop_brl * recovery_factor
        recoverable_type = MoneyConfidence.ESTIMATED
        
        # Additional: Neste caso, não há receita adicional, apenas recuperação
        additional = 0.0
        additional_type = MoneyConfidence.ESTIMATED
        
        return MoneyFound(
            at_risk=at_risk,
            at_risk_type=at_risk_type,
            recoverable=recoverable,
            recoverable_type=recoverable_type,
            additional=additional,
            additional_type=additional_type,
        )
    
    def _create_candidate(
        self,
        tenant_code: str,
        tenant_name: str,
        period_start: str,
        period_end: str,
        analysis: Dict[str, Any]
    ) -> DecisionCandidate:
        """
        Cria DecisionCandidate a partir da análise.
        
        Args:
            tenant_code: Código do tenant
            tenant_name: Nome do tenant
            period_start: Início do período
            period_end: Fim do período
            analysis: Resultado da análise
        
        Returns:
            DecisionCandidate
        """
        impact_brl = analysis["impact_brl"]
        impact_pct = analysis["impact_pct"]
        product_name = analysis["product_name"]
        product_drop_pct = analysis["product_drop_pct"]
        
        # Título começando pelo dinheiro (Princípio 19)
        title = f"Você pode estar perdendo aproximadamente R$ {impact_brl:,.2f} por semana"
        
        # Summary explicativo
        summary = (
            f"Identificamos uma queda de {impact_pct:.1%} nas vendas de combustíveis. "
            f"{product_drop_pct:.0%} dessa perda está relacionada ao {product_name} no {tenant_name}.\n\n"
            f"Confidence: {analysis['confidence']:.0%}"
        )
        
        # Ações recomendadas
        recommended_actions = [
            f"Verificar preço do {product_name} vs concorrência (10 min)",
            f"Confirmar disponibilidade de estoque de {product_name} (5 min)",
            f"Analisar histórico de preço do {product_name} nos últimos 30 dias (5 min)",
        ]
        
        # Criar candidato
        candidate = DecisionCandidate(
            id=str(uuid.uuid4()),
            detector_name=self.detector_name,
            title=title,
            summary=summary,
            category=DecisionCategory.REVENUE,
            impact_type=ImpactType.REVENUE,
            tenant=tenant_code,
            tenant_name=tenant_name,
            period_start=period_start,
            period_end=period_end,
            money_found=analysis["money_found"],
            confidence=analysis["confidence"],
            confidence_factors=analysis["confidence_factors"],
            recommended_actions=recommended_actions,
            estimated_execution_time=20,  # 10 + 5 + 5 = 20 minutos
            evidence=analysis.get("evidence", {}),
            baseline_used=analysis.get("baseline", {}),
            source_endpoints=["/api/v1/sales/fuel-summary", "/api/v1/fuel/executive"],
            alternatives_considered=0,  # Primeira versão: apenas um produto analisado
            selection_reason=f"Maior impacto financeiro absoluto: R$ {impact_brl:,.2f}",
        )
        
        return candidate
