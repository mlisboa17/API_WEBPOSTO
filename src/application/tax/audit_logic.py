from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from src.domain.entities import NCMModel, SaleRecord, TaxResult


# Minimal NCM reference (stub for 2026 base). In production use official dataset.
_NCM_FIXES = {
    "01010100": "01010100",
    "00000000": "01010100",
}


def validate_ncm(code: str) -> bool:
    try:
        NCMModel(code=code)
        return True
    except Exception:
        return False


def suggest_ncm(code: str) -> Optional[str]:
    # naive suggestion: fallback to mapped value
    return _NCM_FIXES.get(code)


def compute_recovery(sales: List[SaleRecord], window_days: int = 90) -> TaxResult:
    cutoff = datetime.utcnow() - timedelta(days=window_days)
    total_recoverable = Decimal(0)

    for s in sales:
        if s.sold_at < cutoff:
            continue
        try:
            gross = Decimal(str(s.gross))
            # Monofásico PIS/COFINS example rate: 2.5% (stub)
            rate = Decimal('0.025')
            recoverable = gross * rate
            total_recoverable += recoverable
        except (InvalidOperation, TypeError):
            continue

    return TaxResult(pis_cofins_recoverable=float(total_recoverable), validated=True)


def compute_real_margin(sale: SaleRecord) -> dict:
    try:
        gross = Decimal(str(sale.gross))
        cost = Decimal(str(sale.cost))
        card_fee = Decimal(str(sale.card_fee_pct)) / Decimal(100)

        if gross == 0:
            return {"margin_pct": 0.0, "valid": False}

        net = gross - cost - (gross * card_fee)
        margin_pct = (net / gross) * Decimal(100)
        return {"margin_pct": float(margin_pct), "valid": True}
    except Exception:
        return {"margin_pct": 0.0, "valid": False}
