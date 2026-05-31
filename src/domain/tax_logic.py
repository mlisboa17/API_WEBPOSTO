"""
CLAUDE 3.7: Adelaide Tax Logic & Business Rules

Pure business logic for:
- CNPJ/CNAE/Regime validation
- Adelaide (ICMS) credit calculation
- Real net margin calculation
- Tax anomaly detection
- Period aggregation
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Tuple, List, Dict, Optional
from enum import Enum


class TaxRegime(str, Enum):
    """Brazilian tax regimes"""
    SIMPLES_NACIONAL = "SIMPLES_NACIONAL"
    LUCRO_REAL = "LUCRO_REAL"
    LUCRO_PRESUMIDO = "LUCRO_PRESUMIDO"


class AdelaideCalculator:
    """
    Calculate Adelaide (ICMS) credits based on:
    - CNPJ classification
    - CNAE activity code
    - Tax regime
    - Regional tax rates
    """
    
    # PE (Pernambuco) tax rates by regime
    PE_RATES = {
        TaxRegime.SIMPLES_NACIONAL: Decimal("8.0"),
        TaxRegime.LUCRO_REAL: Decimal("18.0"),
        TaxRegime.LUCRO_PRESUMIDO: Decimal("18.0"),
    }
    
    # Activity coefficients (from CNAE)
    CNAE_FUEL_COEFFICIENT = Decimal("1.0")  # Base rate
    CNAE_PRODUCTS_COEFFICIENT = Decimal("0.95")  # Products have different rate
    
    @staticmethod
    def validate_cnpj(cnpj: str) -> bool:
        """Validate Brazilian CNPJ format"""
        cnpj_clean = cnpj.replace(".", "").replace("/", "").replace("-", "")
        
        if len(cnpj_clean) != 14 or not cnpj_clean.isdigit():
            return False
        
        # Check first 8 digits (base number)
        if cnpj_clean == cnpj_clean[0] * 14:
            return False
        
        return True
    
    @staticmethod
    def validate_cnae(cnae_code: str) -> bool:
        """Validate CNAE format (XXXX-X/YY)"""
        if not isinstance(cnae_code, str):
            return False
        
        parts = cnae_code.split("/")
        if len(parts) != 2:
            return False
        
        main_parts = parts[0].split("-")
        if len(main_parts) != 2:
            return False
        
        try:
            int(main_parts[0])
            int(main_parts[1])
            int(parts[1])
            return True
        except ValueError:
            return False
    
    @classmethod
    def calculate_adelaide_credit(
        cls,
        regime: TaxRegime,
        revenue: Decimal,
        product_type: str = "FUEL",  # FUEL or PRODUCTS
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate Adelaide (ICMS) credit
        
        Returns: (credit_percentage, credit_amount)
        """
        
        # Get base rate for regime
        base_rate = cls.PE_RATES.get(regime, Decimal("18.0"))
        
        # Apply CNAE coefficient
        coefficient = (
            cls.CNAE_FUEL_COEFFICIENT if product_type == "FUEL"
            else cls.CNAE_PRODUCTS_COEFFICIENT
        )
        
        effective_rate = base_rate * coefficient
        credit_amount = (revenue * effective_rate) / Decimal(100)
        
        return effective_rate, credit_amount
    
    @classmethod
    def calculate_monthly_adelaide(
        cls,
        cnpj: str,
        regime: TaxRegime,
        fuel_revenue: Decimal,
        products_revenue: Decimal,
        services_revenue: Decimal = Decimal(0),
    ) -> Dict[str, Decimal]:
        """Calculate total Adelaide credits for a month"""
        
        if not cls.validate_cnpj(cnpj):
            raise ValueError(f"Invalid CNPJ: {cnpj}")
        
        _, fuel_credit = cls.calculate_adelaide_credit(regime, fuel_revenue, "FUEL")
        _, products_credit = cls.calculate_adelaide_credit(regime, products_revenue, "PRODUCTS")
        
        return {
            "fuel_credit": fuel_credit,
            "products_credit": products_credit,
            "total_adelaide": fuel_credit + products_credit,
        }


class MarginCalculator:
    """Calculate real net margin with all deductions"""
    
    @staticmethod
    def calculate_real_margin(
        revenue: Decimal,
        cost_of_goods: Decimal,
        adelaide_tax: Decimal,
        card_fees: Decimal,
        fixed_costs: Decimal,
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate real net margin
        
        Net Margin = Revenue - COGS - Adelaide Tax - Card Fees - Fixed Costs
        Margin % = (Net Margin / Revenue) * 100
        
        Returns: (margin_amount, margin_percentage)
        """
        
        total_deductions = cost_of_goods + adelaide_tax + card_fees + fixed_costs
        margin_amount = revenue - total_deductions
        
        if revenue == 0:
            return Decimal(0), Decimal(0)
        
        margin_percentage = (margin_amount / revenue) * Decimal(100)
        
        return margin_amount, margin_percentage
    
    @staticmethod
    def calculate_breakeven_point(
        fixed_costs: Decimal,
        contribution_margin_ratio: Decimal,  # % of revenue after COGS
    ) -> Decimal:
        """
        Calculate break-even revenue needed
        
        Break-Even = Fixed Costs / Contribution Margin Ratio
        """
        if contribution_margin_ratio == 0:
            return Decimal(0)
        
        return fixed_costs / contribution_margin_ratio


class ExpenseAnomalyDetector:
    """Detect anomalies in cash flow and expenses"""
    
    @staticmethod
    def detect_closure_anomalies(
        expected_closing: Decimal,
        actual_closing: Decimal,
        threshold_percent: Decimal = Decimal("5"),  # 5% variance
    ) -> List[str]:
        """
        Detect discrepancies in cash closure
        
        Returns list of anomalies found
        """
        anomalies = []
        
        if actual_closing == 0:
            return anomalies
        
        variance_pct = abs(expected_closing - actual_closing) / actual_closing * Decimal(100)
        
        if variance_pct > threshold_percent:
            anomalies.append(
                f"CASH_VARIANCE: Expected R$ {expected_closing:.2f}, "
                f"Found R$ {actual_closing:.2f} ({variance_pct:.1f}% difference)"
            )
        
        return anomalies
    
    @staticmethod
    def detect_expense_spikes(
        current_day_expenses: Decimal,
        average_daily_expenses: Decimal,
        spike_multiplier: Decimal = Decimal("2.5"),  # 250% of average
    ) -> List[str]:
        """Detect unusual expense spikes"""
        anomalies = []
        
        if average_daily_expenses == 0:
            return anomalies
        
        if current_day_expenses > average_daily_expenses * spike_multiplier:
            ratio = current_day_expenses / average_daily_expenses
            anomalies.append(
                f"EXPENSE_SPIKE: Current expenses are {ratio:.1f}x the daily average"
            )
        
        return anomalies
    
    @staticmethod
    def detect_margin_degradation(
        current_margin_pct: Decimal,
        baseline_margin_pct: Decimal,
        degradation_threshold: Decimal = Decimal("5"),  # 5% absolute change
    ) -> List[str]:
        """Detect margin degradation"""
        anomalies = []
        
        change = baseline_margin_pct - current_margin_pct
        
        if change > degradation_threshold:
            anomalies.append(
                f"MARGIN_DEGRADATION: Margin dropped {change:.1f}pp "
                f"({baseline_margin_pct:.1f}% → {current_margin_pct:.1f}%)"
            )
        
        return anomalies


class PeriodAggregator:
    """Aggregate financial data by period"""
    
    PERIODS = {
        "today": 0,
        "7d": 7,
        "30d": 30,
        "90d": 90,
    }
    
    @staticmethod
    def get_period_dates(period: str) -> Tuple[datetime, datetime]:
        """Get start and end dates for period"""
        end_date = datetime.now()
        
        days_back = PeriodAggregator.PERIODS.get(period, 30)
        start_date = end_date - timedelta(days=days_back)
        
        return start_date.replace(hour=0, minute=0, second=0), end_date
    
    @staticmethod
    def calculate_period_stats(
        transactions: List[Dict],
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Decimal]:
        """
        Calculate aggregated stats for period
        
        Expects transactions with: amount, timestamp, category
        """
        
        filtered = [
            t for t in transactions
            if start_date <= datetime.fromisoformat(t.get("timestamp", "")) <= end_date
        ]
        
        return {
            "total_revenue": sum(Decimal(str(t["amount"])) for t in filtered if t.get("category") == "REVENUE"),
            "total_expenses": sum(Decimal(str(t["amount"])) for t in filtered if t.get("category") == "EXPENSE"),
            "transaction_count": len(filtered),
        }


# =============================================================================
# Business Rules
# =============================================================================

def validate_fuel_station_constraints(
    regime: TaxRegime,
    cnpj: str,
    cnae: str,
) -> Tuple[bool, List[str]]:
    """
    Validate business constraints for fuel station
    
    Returns: (is_valid, list_of_errors)
    """
    errors = []
    
    if not AdelaideCalculator.validate_cnpj(cnpj):
        errors.append(f"Invalid CNPJ: {cnpj}")
    
    if not AdelaideCalculator.validate_cnae(cnae):
        errors.append(f"Invalid CNAE: {cnae}")
    
    # Fuel stations must be LUCRO_REAL or LUCRO_PRESUMIDO in PE
    if regime == TaxRegime.SIMPLES_NACIONAL:
        errors.append("Fuel stations in PE cannot use SIMPLES_NACIONAL regime")
    
    return len(errors) == 0, errors
