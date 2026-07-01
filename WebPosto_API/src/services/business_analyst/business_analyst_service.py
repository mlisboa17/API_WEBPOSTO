"""
Business Analyst Service - Serviço Principal
Orquestra a geração de relatórios executivos e análises
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
import logging
from typing import Any

from src.services.business_analyst.business_health_score import BusinessHealthScoreCalculator
from src.services.business_analyst.schemas import (
    BusinessOpportunity,
    BusinessRisk,
    DailyExecutiveReport,
    RecommendedAction,
    WeeklyExecutiveReport,
)

LOGGER = logging.getLogger(__name__)


class BusinessAnalystService:
    """Serviço de Análise Executiva Autônoma"""
    
    def __init__(self, financial_service: Any = None, sales_service: Any = None):
        """
        Inicializa o serviço
        
        Args:
            financial_service: Serviço financeiro oficial
            sales_service: Serviço de vendas oficial
        """
        self.financial_service = financial_service
        self.sales_service = sales_service
        self.health_calculator = BusinessHealthScoreCalculator()
    
    async def generate_daily_report(
        self,
        tenant: str,
        report_date: date | None = None,
    ) -> DailyExecutiveReport:
        """
        Gera relatório executivo diário
        
        Args:
            tenant: Nome do tenant
            report_date: Data do relatório (padrão: hoje)
        
        Returns:
            Relatório diário completo
        """
        if report_date is None:
            report_date = date.today()
        
        yesterday = report_date - timedelta(days=1)
        
        # TODO: Integrar com services oficiais existentes
        # Por ora, estrutura básica para demonstração
        
        # Calcular Health Score
        health_data = await self._collect_health_data(tenant, report_date)
        health_score = self.health_calculator.calculate(
            tenant=tenant,
            period_start=report_date.isoformat(),
            period_end=report_date.isoformat(),
            data=health_data,
        )
        
        # Gerar resumo
        summary = self._generate_daily_summary(tenant, report_date, health_score, health_data)
        
        # Identificar riscos
        risks = self._identify_risks(health_data)
        
        # Identificar oportunidades
        opportunities = self._identify_opportunities(health_data)
        
        # Gerar ações recomendadas
        actions = self._generate_recommended_actions(risks, opportunities, health_score)
        
        return DailyExecutiveReport(
            tenant=tenant,
            period=report_date.isoformat(),
            generated_at=datetime.now().isoformat(),
            health_score=health_score,
            summary=summary,
            revenue_today=health_data.get("revenue", {}).get("revenue_today", Decimal("0")),
            revenue_vs_yesterday=health_data.get("revenue", {}).get("revenue_yesterday", Decimal("0")),
            expenses_today=health_data.get("cash_flow", {}).get("expenses", Decimal("0")),
            cash_flow_today=health_data.get("revenue", {}).get("revenue_today", Decimal("0")) - health_data.get("cash_flow", {}).get("expenses", Decimal("0")),
            critical_alerts=health_data.get("alerts", {}).get("critical", []),
            risks=risks,
            opportunities=opportunities,
            recommended_actions=actions,
        )
    
    async def _collect_health_data(self, tenant: str, report_date: date) -> dict[str, Any]:
        """Coleta dados para cálculo de health score"""
        # TODO: Integrar com services reais
        # Por ora, estrutura de exemplo
        return {
            "revenue": {
                "revenue_today": Decimal("15000.00"),
                "revenue_yesterday": Decimal("14500.00"),
                "revenue_target": Decimal("16000.00"),
            },
            "cash_flow": {
                "revenue": Decimal("15000.00"),
                "expenses": Decimal("9500.00"),
            },
            "inventory": {
                "stock_ok": True,
                "products_zero": 2,
                "total_products": 50,
            },
            "accounts": {
                "overdue_payable": Decimal("3000.00"),
                "total_payable": Decimal("25000.00"),
                "overdue_receivable": Decimal("2000.00"),
                "total_receivable": Decimal("18000.00"),
            },
            "growth": {
                "revenue_growth_pct": 3.45,
                "trend": "UP",
            },
            "alerts": {
                "critical_count": 1,
                "warning_count": 3,
                "critical": [
                    {
                        "alert_id": "ALT001",
                        "title": "Estoque crítico de Gasolina Comum",
                        "description": "Estoque abaixo de 20% da capacidade",
                        "detected_at": datetime.now().isoformat(),
                    }
                ],
            },
            "divergences": {
                "divergences_count": 2,
                "divergences_total": Decimal("450.00"),
            },
        }
    
    def _generate_daily_summary(
        self,
        tenant: str,
        report_date: date,
        health_score: Any,
        health_data: dict[str, Any],
    ) -> str:
        """Gera resumo executivo em texto"""
        classification = health_score.classification
        score = round(health_score.overall_score, 1)
        
        revenue = health_data.get("revenue", {}).get("revenue_today", Decimal("0"))
        expenses = health_data.get("cash_flow", {}).get("expenses", Decimal("0"))
        cash_flow = revenue - expenses
        
        summary_parts = [
            f"Status: {classification} ({score}/100).",
            f"Receita: R$ {revenue:,.2f}.",
            f"Despesas: R$ {expenses:,.2f}.",
            f"Fluxo de caixa: R$ {cash_flow:,.2f}.",
        ]
        
        critical_count = health_data.get("alerts", {}).get("critical_count", 0)
        if critical_count > 0:
            summary_parts.append(f"{critical_count} alerta(s) crítico(s) requer(em) atenção imediata.")
        
        return " ".join(summary_parts)
    
    def _identify_risks(self, health_data: dict[str, Any]) -> list[BusinessRisk]:
        """Identifica riscos baseado nos dados"""
        risks = []
        
        # Risco: Alertas críticos
        critical_alerts = health_data.get("alerts", {}).get("critical", [])
        for alert in critical_alerts[:3]:  # Top 3
            risks.append(
                BusinessRisk(
                    risk_id=f"RISK_{alert.get('alert_id', 'UNK')}",
                    title=alert.get("title", "Alerta crítico"),
                    description=alert.get("description", ""),
                    level="CRITICO",
                    impact="Operacional e financeiro",
                    recommended_action="Resolver imediatamente",
                    detected_at=alert.get("detected_at", datetime.now().isoformat()),
                )
            )
        
        # Risco: Inadimplência alta
        overdue_pct = 0.0
        accounts = health_data.get("accounts", {})
        total_payable = accounts.get("total_payable", Decimal("1"))
        overdue_payable = accounts.get("overdue_payable", Decimal("0"))
        if total_payable > 0:
            overdue_pct = float(overdue_payable / total_payable) * 100
        
        if overdue_pct > 30:
            risks.append(
                BusinessRisk(
                    risk_id="RISK_DELINQUENCY_HIGH",
                    title="Inadimplência elevada",
                    description=f"{overdue_pct:.1f}% das contas a pagar estão vencidas",
                    level="ALTO",
                    impact=f"R$ {overdue_payable:,.2f} em atraso pode afetar relacionamento com fornecedores",
                    recommended_action="Negociar pagamento de contas vencidas prioritariamente",
                    detected_at=datetime.now().isoformat(),
                )
            )
        
        return risks
    
    def _identify_opportunities(self, health_data: dict[str, Any]) -> list[BusinessOpportunity]:
        """Identifica oportunidades baseado nos dados"""
        opportunities = []
        
        # Oportunidade: Crescimento de receita
        growth_pct = health_data.get("growth", {}).get("revenue_growth_pct", 0.0)
        if growth_pct > 5:
            opportunities.append(
                BusinessOpportunity(
                    opportunity_id="OPP_GROWTH_MOMENTUM",
                    title="Momento de crescimento favorável",
                    description=f"Receita crescendo {growth_pct:.1f}% - oportunidade de expansão",
                    potential="ALTO",
                    estimated_impact="R$ 3.000-5.000/mês adicional",
                    recommended_action="Aumentar estoque de produtos de maior margem",
                    detected_at=datetime.now().isoformat(),
                )
            )
        
        # Oportunidade: Fluxo de caixa positivo
        revenue = health_data.get("revenue", {}).get("revenue_today", Decimal("0"))
        expenses = health_data.get("cash_flow", {}).get("expenses", Decimal("0"))
        if revenue > expenses * Decimal("1.3"):  # Margem > 30%
            opportunities.append(
                BusinessOpportunity(
                    opportunity_id="OPP_CASH_SURPLUS",
                    title="Fluxo de caixa saudável",
                    description="Margem operacional acima de 30% permite investimentos",
                    potential="MEDIO",
                    estimated_impact="Capacidade de investimento: R$ 2.000-4.000",
                    recommended_action="Considerar antecipação de compras com desconto",
                    detected_at=datetime.now().isoformat(),
                )
            )
        
        return opportunities
    
    def _generate_recommended_actions(
        self,
        risks: list[BusinessRisk],
        opportunities: list[BusinessOpportunity],
        health_score: Any,
    ) -> list[RecommendedAction]:
        """Gera ações recomendadas baseado em riscos e oportunidades"""
        actions = []
        
        # Ações para riscos críticos
        for risk in risks:
            if risk.level == "CRITICO":
                actions.append(
                    RecommendedAction(
                        action_id=f"ACT_{risk.risk_id}",
                        title=f"Resolver: {risk.title}",
                        description=risk.recommended_action,
                        priority="CRITICA",
                        category="OPERACIONAL",
                        estimated_effort="30 minutos",
                        expected_result="Eliminar risco crítico",
                    )
                )
        
        # Ações para oportunidades de alto potencial
        for opp in opportunities:
            if opp.potential == "ALTO":
                actions.append(
                    RecommendedAction(
                        action_id=f"ACT_{opp.opportunity_id}",
                        title=f"Aproveitar: {opp.title}",
                        description=opp.recommended_action,
                        priority="ALTA",
                        category="COMERCIAL",
                        estimated_effort="1-2 horas",
                        expected_result=opp.estimated_impact,
                    )
                )
        
        # Ação geral baseada no health score
        if health_score.overall_score < 60:
            actions.append(
                RecommendedAction(
                    action_id="ACT_HEALTH_RECOVERY",
                    title="Plano de recuperação de saúde financeira",
                    description="Revisar despesas, negociar prazos, aumentar vendas",
                    priority="ALTA",
                    category="FINANCEIRO",
                    estimated_effort="2-4 horas",
                    expected_result="Elevar Health Score para 70+",
                )
            )
        
        return actions
