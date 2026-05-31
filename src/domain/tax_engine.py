from __future__ import annotations

from typing import List, Dict
from decimal import Decimal, InvalidOperation, getcontext
from datetime import datetime, timedelta

from src.domain.entities import NCMModel


getcontext().prec = 18


class TaxEngine:
    """Engine para identificar produtos monofásicos, validar NCM e calcular recuperação."""

    def __init__(self, ncm_reference: Dict[str, str] | None = None):
        # ncm_reference: mapping of invalid->correct suggestion
        self.ncm_reference = ncm_reference or {}

    def validate_ncm(self, code: str) -> bool:
        try:
            NCMModel(code=code)
            return True
        except Exception:
            return False

    def suggest_ncm(self, code: str) -> str | None:
        return self.ncm_reference.get(code)

    def identify_monofasicos(self, products: List[Dict]) -> List[Dict]:
        # naive rule: if product has tag 'monofasico' or specific ncm
        out = []
        for p in products:
            monofasico = p.get("monofasico", False) or p.get("ncm", "").startswith("01")
            if monofasico:
                out.append(p)
        return out

    def compute_recovery(self, products: List[Dict], window_days: int = 90) -> Decimal:
        cutoff = datetime.utcnow() - timedelta(days=window_days)
        total = Decimal(0)
        for p in products:
            sold_at = p.get("sold_at")
            if isinstance(sold_at, str):
                try:
                    sold_at = datetime.fromisoformat(sold_at)
                except Exception:
                    continue
            if sold_at and sold_at < cutoff:
                continue
            try:
                gross = Decimal(str(p.get("gross", 0)))
                rate = Decimal("0.025")
                total += gross * rate
            except (InvalidOperation, TypeError):
                continue
        return total

    def compute_real_margin(self, product: Dict) -> Decimal:
        try:
            gross = Decimal(str(product.get("gross", 0)))
            cost = Decimal(str(product.get("cost", 0)))
            tax = Decimal(str(product.get("tax", 0)))
            card_fee_pct = Decimal(str(product.get("card_fee_pct", 0))) / Decimal(100)
            cc = Decimal(str(product.get("centro_custo", 0)))
            if gross == 0:
                return Decimal(0)
            net = gross - cost - tax - (gross * card_fee_pct) - cc
            margin_pct = (net / gross) * Decimal(100)
            return margin_pct
        except Exception:
            return Decimal(0)


class TaxCalculator:
    def compute(self, price: Decimal, cost: Decimal, sku_meta: Dict) -> Dict[str, Decimal]:
        raise NotImplementedError()


class MonofasicoCalculator(TaxCalculator):
    def compute(self, price: Decimal, cost: Decimal, sku_meta: Dict) -> Dict[str, Decimal]:
        pis = (Decimal(sku_meta.get("aliquota_pis", "0")) / Decimal("100")) * price
        cofins = (Decimal(sku_meta.get("aliquota_cofins", "0")) / Decimal("100")) * price
        icms = (Decimal(sku_meta.get("aliquota_icms", "0")) / Decimal("100")) * price
        return {
            "pis": pis.quantize(Decimal("0.0001")),
            "cofins": cofins.quantize(Decimal("0.0001")),
            "icms": icms.quantize(Decimal("0.0001")),
        }


class PresumedCalculator(TaxCalculator):
    def compute(self, price: Decimal, cost: Decimal, sku_meta: Dict) -> Dict[str, Decimal]:
        pis = (Decimal("1.65") / Decimal("100")) * price
        cofins = (Decimal("7.60") / Decimal("100")) * price
        icms = (Decimal(sku_meta.get("aliquota_icms", "0")) / Decimal("100")) * price
        return {
            "pis": pis.quantize(Decimal("0.0001")),
            "cofins": cofins.quantize(Decimal("0.0001")),
            "icms": icms.quantize(Decimal("0.0001")),
        }


def get_calculator_for_regime(regime: str) -> TaxCalculator:
    if regime == "monofasico":
        return MonofasicoCalculator()
    return PresumedCalculator()


def compute_recoverable(price: Decimal, cost: Decimal, sku_meta: Dict, regime: str = "presumed") -> Decimal:
    calc = get_calculator_for_regime(regime)
    taxes = calc.compute(price, cost, sku_meta)
    paid = taxes["pis"] + taxes["cofins"]
    expected = taxes["pis"] + taxes["cofins"]
    return (paid - expected).quantize(Decimal("0.0001"))
