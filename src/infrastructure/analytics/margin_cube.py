from decimal import Decimal, getcontext
from typing import Iterable, Dict, Any
from difflib import SequenceMatcher

getcontext().prec = 28


def quantize4(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.0001"))


class MarginCube:
    """Compute real net margin and provide NCM similarity helpers."""

    def compute_margin(self, sales_iter: Iterable[Dict[str, Any]]) -> Dict[str, Decimal]:
        total_revenue = Decimal(0)
        total_cost = Decimal(0)
        total_tax = Decimal(0)
        total_card_fee = Decimal(0)
        total_operational = Decimal(0)

        for s in sales_iter:
            price = Decimal(s.get("price", "0"))
            qty = Decimal(s.get("quantity", 1))
            revenue = price * qty
            cost = Decimal(s.get("cost", "0")) * qty
            tax = Decimal(s.get("tax", "0")) * qty
            card = Decimal(s.get("card_fee", "0")) * qty
            op = Decimal(s.get("operational_cost", "0")) * qty

            total_revenue += revenue
            total_cost += cost
            total_tax += tax
            total_card_fee += card
            total_operational += op

        net = total_revenue - total_cost - total_tax - total_card_fee - total_operational
        margin_pct = (net / total_revenue * Decimal(100)) if total_revenue and total_revenue != 0 else Decimal(0)

        return {
            "revenue": quantize4(total_revenue),
            "cost": quantize4(total_cost),
            "tax": quantize4(total_tax),
            "card_fee": quantize4(total_card_fee),
            "operational": quantize4(total_operational),
            "net": quantize4(net),
            "margin_pct": quantize4(margin_pct),
        }

    def ncm_similarity(self, a: str, b: str) -> float:
        """Fuzzy similarity for NCM strings to detect typos."""
        return SequenceMatcher(None, a, b).ratio()
