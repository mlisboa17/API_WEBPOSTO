"""
Business Health Score Calculator
Calcula o score de saúde do negócio baseado em múltiplos indicadores
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from src.services.business_analyst.schemas import BusinessHealthScore, ScoreClassification


class BusinessHealthScoreCalculator:
    """Calculador de Business Health Score"""
    
    # Pesos para cada componente (total = 1.0)
    WEIGHTS = {
        "revenue": 0.25,
        "cash_flow": 0.20,
        "inventory": 0.10,
        "delinquency": 0.15,
        "growth": 0.15,
        "alerts": 0.10,
        "divergence": 0.05,
    }
    
    @staticmethod
    def _classify_score(score: float) -> ScoreClassification:
        """Classifica o score"""
        if score >= 95:
            return "EXCELENTE"
        elif score >= 80:
            return "SAUDAVEL"
        elif score >= 60:
            return "ATENCAO"
        elif score >= 40:
            return "RISCO"
        else:
            return "CRITICO"
    
    @staticmethod
    def _revenue_score(revenue_data: dict[str, Any]) -> float:
        """
        Calcula score de receita (0-100)
        
        Considera:
        - Receita total vs meta
        - Receita vs período anterior
        - Variação
        """
        revenue_today = Decimal(str(revenue_data.get("revenue_today", 0)))
        revenue_yesterday = Decimal(str(revenue_data.get("revenue_yesterday", 0)))
        revenue_target = Decimal(str(revenue_data.get("revenue_target", 0)))
        
        score = 50.0  # Base
        
        # Se atingiu meta: +30 pontos
        if revenue_target > 0:
            achievement = float(revenue_today / revenue_target) * 100
            if achievement >= 100:
                score += 30
            elif achievement >= 80:
                score += 20
            elif achievement >= 60:
                score += 10
        
        # Se cresceu vs ontem: +20 pontos
        if revenue_yesterday > 0 and revenue_today > revenue_yesterday:
            growth = float((revenue_today - revenue_yesterday) / revenue_yesterday)
            if growth >= 0.10:  # +10% ou mais
                score += 20
            elif growth >= 0.05:  # +5% ou mais
                score += 15
            elif growth > 0:
                score += 10
        elif revenue_today < revenue_yesterday:
            # Penalidade por queda
            score -= 10
        
        return min(100.0, max(0.0, score))
    
    @staticmethod
    def _cash_flow_score(cash_data: dict[str, Any]) -> float:
        """
        Calcula score de fluxo de caixa (0-100)
        
        Considera:
        - Saldo positivo ou negativo
        - Receita vs despesa
        """
        revenue = Decimal(str(cash_data.get("revenue", 0)))
        expenses = Decimal(str(cash_data.get("expenses", 0)))
        cash_flow = revenue - expenses
        
        score = 50.0
        
        # Fluxo positivo
        if cash_flow > 0:
            score += 30
            # Margem boa (despesas < 70% da receita)
            if revenue > 0:
                margin = float(expenses / revenue)
                if margin < 0.5:  # Despesas < 50%
                    score += 20
                elif margin < 0.7:  # Despesas < 70%
                    score += 10
        else:
            # Fluxo negativo: penalidade
            score -= 30
        
        return min(100.0, max(0.0, score))
    
    @staticmethod
    def _inventory_score(inventory_data: dict[str, Any]) -> float:
        """
        Calcula score de estoque (0-100)
        
        Considera:
        - Estoque vs vendas
        - Produtos zerados
        """
        stock_ok = inventory_data.get("stock_ok", True)
        products_zero = inventory_data.get("products_zero", 0)
        total_products = inventory_data.get("total_products", 1)
        
        score = 70.0 if stock_ok else 30.0
        
        # Penalidade por produtos zerados
        if total_products > 0:
            zero_pct = products_zero / total_products
            if zero_pct > 0.3:  # >30% zerados
                score -= 30
            elif zero_pct > 0.1:  # >10% zerados
                score -= 15
        
        return min(100.0, max(0.0, score))
    
    @staticmethod
    def _delinquency_score(accounts_data: dict[str, Any]) -> float:
        """
        Calcula score de inadimplência (0-100)
        
        Considera:
        - Contas a pagar vencidas
        - Contas a receber vencidas
        """
        overdue_payable = Decimal(str(accounts_data.get("overdue_payable", 0)))
        overdue_receivable = Decimal(str(accounts_data.get("overdue_receivable", 0)))
        total_payable = Decimal(str(accounts_data.get("total_payable", 1)))
        total_receivable = Decimal(str(accounts_data.get("total_receivable", 1)))
        
        score = 100.0
        
        # Penalidade por atraso em pagamentos
        if total_payable > 0:
            overdue_pct = float(overdue_payable / total_payable)
            if overdue_pct > 0.5:  # >50% atrasado
                score -= 50
            elif overdue_pct > 0.3:  # >30% atrasado
                score -= 30
            elif overdue_pct > 0.1:  # >10% atrasado
                score -= 15
        
        # Penalidade por inadimplência de clientes
        if total_receivable > 0:
            overdue_pct = float(overdue_receivable / total_receivable)
            if overdue_pct > 0.3:
                score -= 20
            elif overdue_pct > 0.1:
                score -= 10
        
        return min(100.0, max(0.0, score))
    
    @staticmethod
    def _growth_score(growth_data: dict[str, Any]) -> float:
        """
        Calcula score de crescimento (0-100)
        
        Considera:
        - Crescimento de receita
        - Crescimento de clientes
        - Tendência
        """
        revenue_growth = growth_data.get("revenue_growth_pct", 0.0)
        trend = growth_data.get("trend", "STABLE")  # UP, DOWN, STABLE
        
        score = 50.0
        
        # Score por crescimento
        if revenue_growth >= 10:
            score += 40
        elif revenue_growth >= 5:
            score += 30
        elif revenue_growth > 0:
            score += 20
        elif revenue_growth < -5:
            score -= 20
        elif revenue_growth < 0:
            score -= 10
        
        # Ajuste por tendência
        if trend == "UP":
            score += 10
        elif trend == "DOWN":
            score -= 10
        
        return min(100.0, max(0.0, score))
    
    @staticmethod
    def _alerts_score(alerts_data: dict[str, Any]) -> float:
        """
        Calcula score baseado em alertas (0-100)
        
        Considera:
        - Alertas críticos
        - Alertas de atenção
        """
        critical_alerts = alerts_data.get("critical_count", 0)
        warning_alerts = alerts_data.get("warning_count", 0)
        
        score = 100.0
        
        # Penalidade por alertas
        score -= critical_alerts * 15  # Cada crítico: -15
        score -= warning_alerts * 5    # Cada warning: -5
        
        return min(100.0, max(0.0, score))
    
    @staticmethod
    def _divergence_score(divergence_data: dict[str, Any]) -> float:
        """
        Calcula score de divergências financeiras (0-100)
        
        Considera:
        - Divergências em fechamento de caixa
        - Divergências em apuração vs apresentado
        """
        divergences_count = divergence_data.get("divergences_count", 0)
        divergences_total = Decimal(str(divergence_data.get("divergences_total", 0)))
        
        score = 100.0
        
        # Penalidade por número de divergências
        score -= divergences_count * 10
        
        # Penalidade por valor total de divergências
        if divergences_total > 1000:
            score -= 20
        elif divergences_total > 500:
            score -= 10
        elif divergences_total > 100:
            score -= 5
        
        return min(100.0, max(0.0, score))
    
    @classmethod
    def calculate(
        cls,
        tenant: str,
        period_start: str,
        period_end: str,
        data: dict[str, Any],
    ) -> BusinessHealthScore:
        """
        Calcula o Business Health Score completo
        
        Args:
            tenant: Nome do tenant
            period_start: Data inicial do período
            period_end: Data final do período
            data: Dados para cálculo (revenue, cash_flow, inventory, etc.)
        
        Returns:
            BusinessHealthScore calculado
        """
        # Calcular cada componente
        revenue_score = cls._revenue_score(data.get("revenue", {}))
        cash_flow_score = cls._cash_flow_score(data.get("cash_flow", {}))
        inventory_score = cls._inventory_score(data.get("inventory", {}))
        delinquency_score = cls._delinquency_score(data.get("accounts", {}))
        growth_score = cls._growth_score(data.get("growth", {}))
        alerts_score = cls._alerts_score(data.get("alerts", {}))
        divergence_score = cls._divergence_score(data.get("divergences", {}))
        
        # Calcular score geral (média ponderada)
        overall = (
            revenue_score * cls.WEIGHTS["revenue"]
            + cash_flow_score * cls.WEIGHTS["cash_flow"]
            + inventory_score * cls.WEIGHTS["inventory"]
            + delinquency_score * cls.WEIGHTS["delinquency"]
            + growth_score * cls.WEIGHTS["growth"]
            + alerts_score * cls.WEIGHTS["alerts"]
            + divergence_score * cls.WEIGHTS["divergence"]
        )
        
        classification = cls._classify_score(overall)
        
        return BusinessHealthScore(
            overall_score=overall,
            classification=classification,
            revenue_score=revenue_score,
            cash_flow_score=cash_flow_score,
            inventory_score=inventory_score,
            delinquency_score=delinquency_score,
            growth_score=growth_score,
            alerts_score=alerts_score,
            divergence_score=divergence_score,
            tenant=tenant,
            period_start=period_start,
            period_end=period_end,
            calculated_at=datetime.now().isoformat(),
        )
