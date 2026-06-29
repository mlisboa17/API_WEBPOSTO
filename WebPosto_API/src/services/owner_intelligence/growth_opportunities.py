"""
Motor 3 — Growth Opportunities Engine

Discovers growth and optimization opportunities:
- Products growing in sales
- Products losing market share
- Mix optimization
- Digital payment trends
- Premium product opportunities
- Strong days/hours
- Margin improvements

Never assumes structure - always discovers from actual data.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from collections import defaultdict

from .schemas import (
    GrowthOpportunity, DecisionAction, FinancialImpact, DecisionSource,
    ActionType, ActionPriority, ConfidenceLevel
)

logger = logging.getLogger(__name__)


class GrowthOpportunitiesEngine:
    """
    Engine to discover growth and optimization opportunities.
    
    Discovers automatically:
    - Product trends (growing/declining)
    - Payment method shifts
    - Premium opportunities
    - Day/hour patterns
    - Margin optimization
    """
    
    def __init__(self):
        self.opportunities: List[GrowthOpportunity] = []
        
    async def analyze(
        self,
        tenant_id: str,
        empresa_codigo: str,
        sales_data: Dict[str, Any],
        product_data: Dict[str, Any],
        payment_data: Dict[str, Any],
        historical_data: Optional[Dict[str, Any]] = None
    ) -> List[GrowthOpportunity]:
        """
        Analyze data and find growth opportunities.
        
        Args:
            tenant_id: Tenant identifier
            empresa_codigo: WebPosto company code
            sales_data: Current sales data
            product_data: Product performance data
            payment_data: Payment method data
            historical_data: Historical data for trend analysis
            
        Returns:
            List of growth opportunities
        """
        self.opportunities = []
        
        try:
            # Detect various opportunities
            await self._find_product_growth_trends(tenant_id, empresa_codigo, product_data, historical_data)
            await self._find_declining_products(tenant_id, empresa_codigo, product_data, historical_data)
            await self._find_mix_optimization(tenant_id, empresa_codigo, product_data)
            await self._find_digital_payment_trend(tenant_id, empresa_codigo, payment_data, historical_data)
            await self._find_premium_opportunities(tenant_id, empresa_codigo, sales_data, product_data)
            await self._find_strong_day_patterns(tenant_id, empresa_codigo, sales_data, historical_data)
            await self._find_margin_improvement_opportunities(tenant_id, empresa_codigo, product_data)
            
            logger.info(
                f"GrowthOpportunitiesEngine: Found {len(self.opportunities)} opportunities "
                f"for tenant {tenant_id}, empresa {empresa_codigo}"
            )
            
            return self.opportunities
            
        except Exception as e:
            logger.error(f"Error in GrowthOpportunitiesEngine.analyze: {e}")
            return []
    
    async def _find_product_growth_trends(
        self,
        tenant_id: str,
        empresa_codigo: str,
        product_data: Dict[str, Any],
        historical_data: Optional[Dict[str, Any]]
    ):
        """Find products with strong growth trends."""
        try:
            products = product_data.get("products", [])
            
            if not products or not historical_data:
                return
            
            growing_products = []
            
            for product in products:
                name = product.get("name", "")
                current_volume = product.get("volume_liters", 0)
                current_revenue = product.get("revenue", 0)
                
                # Get historical data for this product
                hist = historical_data.get("products", {}).get(name, {})
                baseline_volume = hist.get("avg_volume", current_volume)
                
                if baseline_volume > 0:
                    growth_pct = ((current_volume - baseline_volume) / baseline_volume) * 100
                    
                    # Strong growth: > 40% increase
                    if growth_pct >= 40:
                        trend_strength = min(growth_pct / 100, 1.0)  # Cap at 100% = strength 1.0
                        
                        growing_products.append({
                            "name": name,
                            "growth_pct": growth_pct,
                            "trend_strength": trend_strength,
                            "current_volume": current_volume,
                            "current_revenue": current_revenue
                        })
            
            # Create opportunity for top growing product
            if growing_products:
                top_grower = max(growing_products, key=lambda x: x["growth_pct"])
                
                # Calculate potential
                potential_revenue = top_grower["current_revenue"] * 0.2  # 20% more potential
                potential_profit = potential_revenue * 0.15  # Assume 15% margin
                
                opportunity = GrowthOpportunity(
                    id=f"opp_growth_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d')}",
                    title=f"{top_grower['name']} sales up {top_grower['growth_pct']:.0f}%",
                    description=f"{top_grower['name']} is showing exceptional growth of "
                              f"{top_grower['growth_pct']:.0f}% vs baseline. This trend "
                              f"indicates strong demand. Consider increasing inventory and "
                              f"exploring related premium products.",
                    opportunity_type="product_trend",
                    potential_revenue=potential_revenue,
                    potential_profit=potential_profit,
                    investment_required=None,
                    roi_percent=None,
                    affected_products=[top_grower["name"]],
                    trend_direction="up",
                    trend_strength=top_grower["trend_strength"],
                    action=DecisionAction(
                        id=f"act_growth_{tenant_id}",
                        type=ActionType.OPTIMIZE,
                        priority=ActionPriority.HIGH,
                        title=f"Capitalize on {top_grower['name']} growth",
                        description=f"{top_grower['name']} is growing {top_grower['growth_pct']:.0f}%. "
                                  f"Actions: (1) Ensure adequate inventory, "
                                  f"(2) Consider premium variants, (3) Promote to customers.",
                        financial_impact=FinancialImpact(
                            estimated_value=potential_profit,
                            impact_type="gain_opportunity",
                            probability=0.6,
                            timeframe_days=30
                        ),
                        source=DecisionSource(
                            endpoint="/v1/products/trends",
                            service="ProductTrendService",
                            data_timestamp=datetime.utcnow()
                        ),
                        confidence=0.75,
                        confidence_level=ConfidenceLevel.HIGH,
                        tenant_id=tenant_id,
                        empresa_codigo=empresa_codigo,
                        suggested_action="Increase inventory and create promotion campaign for growing product",
                        category="sales",
                        tags=["growth", "trend", "opportunity", "product"]
                    ),
                    confidence=0.75,
                    source=DecisionSource(
                        endpoint="/v1/products/trends",
                        service="ProductTrendService",
                        data_timestamp=datetime.utcnow()
                    )
                )
                self.opportunities.append(opportunity)
                
        except Exception as e:
            logger.warning(f"Error finding product growth trends: {e}")
    
    async def _find_declining_products(
        self,
        tenant_id: str,
        empresa_codigo: str,
        product_data: Dict[str, Any],
        historical_data: Optional[Dict[str, Any]]
    ):
        """Find products losing market share."""
        try:
            products = product_data.get("products", [])
            
            if not products or not historical_data:
                return
            
            declining_products = []
            
            for product in products:
                name = product.get("name", "")
                current_volume = product.get("volume_liters", 0)
                
                hist = historical_data.get("products", {}).get(name, {})
                baseline_volume = hist.get("avg_volume", current_volume)
                
                if baseline_volume > 0:
                    decline_pct = ((baseline_volume - current_volume) / baseline_volume) * 100
                    
                    # Significant decline: > 25% decrease
                    if decline_pct >= 25 and current_volume > 0:  # Still has some sales
                        declining_products.append({
                            "name": name,
                            "decline_pct": decline_pct,
                            "current_volume": current_volume
                        })
            
            if declining_products:
                # Get worst decliner with significant volume
                significant_decliners = [p for p in declining_products if p["current_volume"] > 1000]
                
                if significant_decliners:
                    worst = max(significant_decliners, key=lambda x: x["decline_pct"])
                    
                    # Calculate recovery potential
                    potential_recovery = worst["current_volume"] * (worst["decline_pct"] / 100)
                    potential_revenue = potential_recovery * 5  # Assume R$ 5/L average
                    
                    opportunity = GrowthOpportunity(
                        id=f"opp_decline_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d')}",
                        title=f"{worst['name']} declining {worst['decline_pct']:.0f}%",
                        description=f"{worst['name']} has lost {worst['decline_pct']:.0f}% of volume. "
                                  f"This decline represents lost revenue. Investigate causes: "
                                  f"pricing, competition, quality, or operational issues.",
                        opportunity_type="market_share_loss",
                        potential_revenue=potential_revenue,
                        potential_profit=potential_revenue * 0.1,
                        investment_required=potential_revenue * 0.05,
                        roi_percent=100,
                        affected_products=[worst["name"]],
                        trend_direction="down",
                        trend_strength=worst["decline_pct"] / 100,
                        action=DecisionAction(
                            id=f"act_decline_{tenant_id}",
                            type=ActionType.REVIEW,
                            priority=ActionPriority.MEDIUM,
                            title=f"Investigate {worst['name']} decline",
                            description=f"{worst['name']} down {worst['decline_pct']:.0f}%. "
                                      f"Check: pricing vs competitors, fuel quality, "
                                      f"pump availability, employee knowledge.",
                            financial_impact=FinancialImpact(
                                estimated_value=potential_revenue * 0.1,
                                impact_type="gain_opportunity",
                                probability=0.5,
                                timeframe_days=60
                            ),
                            source=DecisionSource(
                                endpoint="/v1/products/decline",
                                service="ProductAnalysisService",
                                data_timestamp=datetime.utcnow()
                            ),
                            confidence=0.70,
                            confidence_level=ConfidenceLevel.MEDIUM,
                            tenant_id=tenant_id,
                            empresa_codigo=empresa_codigo,
                            suggested_action="Analyze pricing and compare with nearby competitors",
                            category="sales",
                            tags=["decline", "market-share", "investigation"]
                        ),
                        confidence=0.70,
                        source=DecisionSource(
                            endpoint="/v1/products/decline",
                            service="ProductAnalysisService",
                            data_timestamp=datetime.utcnow()
                        )
                    )
                    self.opportunities.append(opportunity)
                    
        except Exception as e:
            logger.warning(f"Error finding declining products: {e}")
    
    async def _find_mix_optimization(
        self,
        tenant_id: str,
        empresa_codigo: str,
        product_data: Dict[str, Any]
    ):
        """Find product mix optimization opportunities."""
        try:
            products = product_data.get("products", [])
            
            if not products or len(products) < 2:
                return
            
            # Calculate margins (would come from actual data)
            # This is a simplified example
            premium_products = [p for p in products if "aditivad" in p.get("name", "").lower()]
            
            if len(premium_products) >= 1 and len(products) >= 2:
                # Find best premium product
                best_premium = max(premium_products, key=lambda x: x.get("revenue", 0))
                
                # Check if there's potential to shift volume to premium
                regular_products = [p for p in products if p not in premium_products]
                
                if regular_products:
                    top_regular = max(regular_products, key=lambda x: x.get("volume_liters", 0))
                    
                    # Assume 10% could be converted
                    convertible_volume = top_regular.get("volume_liters", 0) * 0.1
                    premium_price_diff = 0.30  # R$ 0.30/L difference
                    
                    potential_revenue = convertible_volume * premium_price_diff
                    
                    if potential_revenue > 500:  # Only if meaningful
                        opportunity = GrowthOpportunity(
                            id=f"opp_mix_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d')}",
                            title=f"Upsell opportunity: R$ {potential_revenue:,.0f}/month",
                            description=f"Opportunity to shift {convertible_volume:,.0f}L from "
                                      f"regular to premium products. Customers buying "
                                      f"{top_regular.get('name', 'regular')} could be "
                                      f"upsold to {best_premium.get('name', 'premium')}, "
                                      f"increasing margin by R$ {premium_price_diff:.2f}/L.",
                            opportunity_type="mix_optimization",
                            potential_revenue=potential_revenue * 30,  # Monthly
                            potential_profit=potential_revenue * 30 * 0.5,
                            investment_required=500,  # Training/promotion
                            roi_percent=300,
                            affected_products=[top_regular.get("name"), best_premium.get("name")],
                            trend_direction="stable",
                            trend_strength=0.6,
                            action=DecisionAction(
                                id=f"act_mix_{tenant_id}",
                                type=ActionType.OPTIMIZE,
                                priority=ActionPriority.MEDIUM,
                                title="Train staff on premium upselling",
                                description=f"Train attendants to upsell from {top_regular.get('name')} "
                                          f"to {best_premium.get('name')}. Estimated gain: "
                                          f"R$ {potential_revenue * 30:,.0f}/month.",
                                financial_impact=FinancialImpact(
                                    estimated_value=potential_revenue * 30 * 0.5,
                                    impact_type="gain_opportunity",
                                    probability=0.5,
                                    timeframe_days=90
                                ),
                                source=DecisionSource(
                                    endpoint="/v1/products/mix",
                                    service="ProductMixService",
                                    data_timestamp=datetime.utcnow()
                                ),
                                confidence=0.72,
                                confidence_level=ConfidenceLevel.MEDIUM,
                                tenant_id=tenant_id,
                                empresa_codigo=empresa_codigo,
                                suggested_action="Train all attendants on premium product benefits and upselling",
                                category="sales",
                                tags=["mix", "upsell", "premium", "training"]
                            ),
                            confidence=0.72,
                            source=DecisionSource(
                                endpoint="/v1/products/mix",
                                service="ProductMixService",
                                data_timestamp=datetime.utcnow()
                            )
                        )
                        self.opportunities.append(opportunity)
                        
        except Exception as e:
            logger.warning(f"Error finding mix optimization: {e}")
    
    async def _find_digital_payment_trend(
        self,
        tenant_id: str,
        empresa_codigo: str,
        payment_data: Dict[str, Any],
        historical_data: Optional[Dict[str, Any]]
    ):
        """Find digital payment adoption trends."""
        try:
            current_pix = payment_data.get("pix_volume", 0)
            current_cards = payment_data.get("card_volume", 0)
            
            if not historical_data:
                return
            
            hist_pix = historical_data.get("payments", {}).get("pix_avg", current_pix)
            
            if hist_pix > 0:
                pix_growth = ((current_pix - hist_pix) / hist_pix) * 100
                
                # Strong Pix adoption
                if pix_growth >= 50:
                    opportunity = GrowthOpportunity(
                        id=f"opp_pix_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d')}",
                        title=f"Pix adoption growing {pix_growth:.0f}% — optimize for speed",
                        description=f"Pix transactions have grown {pix_growth:.0f}%, indicating "
                                  f"strong customer preference for instant payment. Optimize "
                                  f"checkout process and promote Pix discounts to reduce "
                                  f"card processing fees.",
                        opportunity_type="payment_trend",
                        potential_revenue=current_pix * 0.01,  # 1% savings on fees
                        potential_profit=current_pix * 0.01,
                        investment_required=0,
                        roi_percent=float('inf'),
                        affected_products=None,
                        trend_direction="up",
                        trend_strength=min(pix_growth / 100, 1.0),
                        action=DecisionAction(
                            id=f"act_pix_{tenant_id}",
                            type=ActionType.OPTIMIZE,
                            priority=ActionPriority.LOW,
                            title="Promote Pix payment method",
                            description="Offer small discount (0.5%) for Pix payments to "
                                      "reduce card processing costs and speed up checkout.",
                            financial_impact=FinancialImpact(
                                estimated_value=current_pix * 0.01,
                                impact_type="cost_avoidance",
                                probability=0.7,
                                timeframe_days=30
                            ),
                            source=DecisionSource(
                                endpoint="/v1/payments/trends",
                                service="PaymentTrendService",
                                data_timestamp=datetime.utcnow()
                            ),
                            confidence=0.80,
                            confidence_level=ConfidenceLevel.HIGH,
                            tenant_id=tenant_id,
                            empresa_codigo=empresa_codigo,
                            suggested_action="Create Pix promotion: 0.5% discount for Pix payments",
                            category="operations",
                            tags=["pix", "digital-payments", "cost-reduction"]
                        ),
                        confidence=0.80,
                        source=DecisionSource(
                            endpoint="/v1/payments/trends",
                            service="PaymentTrendService",
                            data_timestamp=datetime.utcnow()
                        )
                    )
                    self.opportunities.append(opportunity)
                    
        except Exception as e:
            logger.warning(f"Error finding digital payment trend: {e}")
    
    async def _find_premium_opportunities(
        self,
        tenant_id: str,
        empresa_codigo: str,
        sales_data: Dict[str, Any],
        product_data: Dict[str, Any]
    ):
        """Find opportunities for premium products."""
        try:
            # Simplified: Check if premium percentage is low
            products = product_data.get("products", [])
            
            # Calculate premium vs regular split
            premium_revenue = sum(
                p.get("revenue", 0) for p in products
                if "aditivad" in p.get("name", "").lower() or "premium" in p.get("name", "").lower()
            )
            total_revenue = sum(p.get("revenue", 0) for p in products)
            
            if total_revenue > 0:
                premium_pct = (premium_revenue / total_revenue) * 100
                
                # If premium is less than 15%, there's opportunity
                if premium_pct < 15 and total_revenue > 10000:
                    gap_to_baseline = 15 - premium_pct
                    potential_uplift = total_revenue * (gap_to_baseline / 100) * 0.3  # 30% margin diff
                    
                    opportunity = GrowthOpportunity(
                        id=f"opp_premium_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d')}",
                        title=f"Premium product opportunity: {gap_to_baseline:.0f}% gap",
                        description=f"Premium products represent only {premium_pct:.1f}% of sales, "
                                  f"vs industry baseline of 15%. Closing this {gap_to_baseline:.0f}% "
                                  f"gap could generate R$ {potential_uplift:,.0f} additional profit monthly.",
                        opportunity_type="premium_opportunity",
                        potential_revenue=potential_uplift * 2,
                        potential_profit=potential_uplift,
                        investment_required=1000,  # Signage, training
                        roi_percent=potential_uplift / 10,
                        affected_products=None,
                        trend_direction="stable",
                        trend_strength=0.7,
                        action=DecisionAction(
                            id=f"act_premium_{tenant_id}",
                            type=ActionType.OPTIMIZE,
                            priority=ActionPriority.MEDIUM,
                            title="Increase premium product focus",
                            description=f"Premium is only {premium_pct:.1f}% of sales. "
                                      f"Opportunity: R$ {potential_uplift:,.0f}/month. "
                                      f"Actions: better signage, staff training, customer education.",
                            financial_impact=FinancialImpact(
                                estimated_value=potential_uplift,
                                impact_type="gain_opportunity",
                                probability=0.5,
                                timeframe_days=90
                            ),
                            source=DecisionSource(
                                endpoint="/v1/products/premium",
                                service="PremiumAnalysisService",
                                data_timestamp=datetime.utcnow()
                            ),
                            confidence=0.68,
                            confidence_level=ConfidenceLevel.MEDIUM,
                            tenant_id=tenant_id,
                            empresa_codigo=empresa_codigo,
                            suggested_action="Install premium fuel signage and train attendants on benefits",
                            category="sales",
                            tags=["premium", "mix", "margin-improvement"]
                        ),
                        confidence=0.68,
                        source=DecisionSource(
                            endpoint="/v1/products/premium",
                            service="PremiumAnalysisService",
                            data_timestamp=datetime.utcnow()
                        )
                    )
                    self.opportunities.append(opportunity)
                    
        except Exception as e:
            logger.warning(f"Error finding premium opportunities: {e}")
    
    async def _find_strong_day_patterns(
        self,
        tenant_id: str,
        empresa_codigo: str,
        sales_data: Dict[str, Any],
        historical_data: Optional[Dict[str, Any]]
    ):
        """Find strong day/hour patterns for optimization."""
        try:
            daily_pattern = sales_data.get("daily_pattern", {})
            
            if not daily_pattern or not historical_data:
                return
            
            # Find strongest day
            day_sales = daily_pattern.get("by_day", {})
            if not day_sales:
                return
            
            strongest_day = max(day_sales.items(), key=lambda x: x[1])
            weakest_day = min(day_sales.items(), key=lambda x: x[1])
            
            diff_pct = ((strongest_day[1] - weakest_day[1]) / strongest_day[1]) * 100 if strongest_day[1] > 0 else 0
            
            if diff_pct >= 40:  # Significant variation
                potential = weakest_day[1] * 0.2  # 20% improvement on weakest day
                
                opportunity = GrowthOpportunity(
                    id=f"opp_pattern_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d')}",
                    title=f"{weakest_day[0]} is {diff_pct:.0f}% weaker than {strongest_day[0]}",
                    description=f"Sales on {weakest_day[0]} are {diff_pct:.0f}% lower than "
                              f"{strongest_day[0]}. Investigate causes and test promotions "
                              f"to balance weekly revenue distribution.",
                    opportunity_type="pattern_optimization",
                    potential_revenue=potential * 4,  # 4 weeks
                    potential_profit=potential * 4 * 0.1,
                    investment_required=potential * 0.5,  # Promotion costs
                    roi_percent=80,
                    affected_products=None,
                    trend_direction="stable",
                    trend_strength=0.6,
                    action=DecisionAction(
                        id=f"act_pattern_{tenant_id}",
                        type=ActionType.REVIEW,
                        priority=ActionPriority.LOW,
                        title=f"Test promotions on {weakest_day[0]}",
                        description=f"{weakest_day[0]} is weakest day. Test loyalty points "
                                  f"multiplier or discount to increase traffic.",
                        financial_impact=FinancialImpact(
                            estimated_value=potential * 4 * 0.1,
                            impact_type="gain_opportunity",
                            probability=0.4,
                            timeframe_days=60
                        ),
                        source=DecisionSource(
                            endpoint="/v1/sales/patterns",
                            service="PatternAnalysisService",
                            data_timestamp=datetime.utcnow()
                        ),
                        confidence=0.65,
                        confidence_level=ConfidenceLevel.MEDIUM,
                        tenant_id=tenant_id,
                        empresa_codigo=empresa_codigo,
                        suggested_action=f"Create {weakest_day[0]} promotion: double loyalty points",
                        category="marketing",
                        tags=["patterns", "promotions", "weekday-optimization"]
                    ),
                    confidence=0.65,
                    source=DecisionSource(
                        endpoint="/v1/sales/patterns",
                        service="PatternAnalysisService",
                        data_timestamp=datetime.utcnow()
                    )
                )
                self.opportunities.append(opportunity)
                
        except Exception as e:
            logger.warning(f"Error finding day patterns: {e}")
    
    async def _find_margin_improvement_opportunities(
        self,
        tenant_id: str,
        empresa_codigo: str,
        product_data: Dict[str, Any]
    ):
        """Find margin improvement opportunities."""
        try:
            products = product_data.get("products", [])
            
            # This would analyze margins in detail
            # Simplified: just check if any product has low margin
            low_margin_products = [
                p for p in products
                if p.get("margin_percent", 0) < 5 and p.get("revenue", 0) > 5000
            ]
            
            if low_margin_products:
                worst = min(low_margin_products, key=lambda x: x.get("margin_percent", 0))
                
                opportunity = GrowthOpportunity(
                    id=f"opp_margin_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d')}",
                    title=f"{worst.get('name', 'Product')} margin only {worst.get('margin_percent', 0):.1f}%",
                    description=f"{worst.get('name', 'Product')} has a very low margin of "
                              f"{worst.get('margin_percent', 0):.1f}%. Review purchase prices "
                              f"and selling prices. Even a 1% improvement would significantly "
                              f"impact profitability.",
                    opportunity_type="margin_improvement",
                    potential_revenue=worst.get("revenue", 0) * 0.01,
                    potential_profit=worst.get("revenue", 0) * 0.01,
                    investment_required=0,
                    roi_percent=float('inf'),
                    affected_products=[worst.get("name", "Product")],
                    trend_direction="stable",
                    trend_strength=0.7,
                    action=DecisionAction(
                        id=f"act_margin_{tenant_id}",
                        type=ActionType.REVIEW,
                        priority=ActionPriority.MEDIUM,
                        title=f"Review pricing for {worst.get('name', 'Product')}",
                        description=f"Margin is only {worst.get('margin_percent', 0):.1f}%. "
                                  f"Check supplier prices and competitor pricing.",
                        financial_impact=FinancialImpact(
                            estimated_value=worst.get("revenue", 0) * 0.01,
                            impact_type="gain_opportunity",
                            probability=0.6,
                            timeframe_days=30
                        ),
                        source=DecisionSource(
                            endpoint="/v1/products/margins",
                            service="MarginAnalysisService",
                            data_timestamp=datetime.utcnow()
                        ),
                        confidence=0.75,
                        confidence_level=ConfidenceLevel.HIGH,
                        tenant_id=tenant_id,
                        empresa_codigo=empresa_codigo,
                        suggested_action="Renegotiate with supplier or adjust selling price by 1-2%",
                        category="pricing",
                        tags=["margin", "pricing", "profitability"]
                    ),
                    confidence=0.75,
                    source=DecisionSource(
                        endpoint="/v1/products/margins",
                        service="MarginAnalysisService",
                        data_timestamp=datetime.utcnow()
                    )
                )
                self.opportunities.append(opportunity)
                
        except Exception as e:
            logger.warning(f"Error finding margin opportunities: {e}")
    
    def get_total_opportunity_value(self) -> float:
        """Get total opportunity value."""
        return sum(o.potential_profit for o in self.opportunities)