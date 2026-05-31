import asyncio
from decimal import Decimal
from datetime import datetime, timedelta

from src.application.tax.recovery_engine import compute_recovery, SaleRecord


class DummyAPI:
    async def fetch_ncm_and_rate(self, sku: str):
        # return a different rate to trigger recovery
        return {"ncm": "22021000", "rate": Decimal("10.0000")}


def make_sale(sku: str, days_ago: int = 10):
    return SaleRecord(
        sku=sku,
        ncm="22021001",
        tax_rate=Decimal("8.0000"),
        price=Decimal("10.0000"),
        quantity=10,
        sold_at=datetime.utcnow() - timedelta(days=days_ago),
    )


def test_compute_recovery():
    sales = [make_sale("SKU01", 5), make_sale("SKU02", 40)]
    results = asyncio.run(compute_recovery(sales, DummyAPI(), window_days=90))
    assert len(results) == 2
    total = sum([r.discrepancy_amount for r in results])
    assert total > 0
