from __future__ import annotations
from typing import List, Dict
from decimal import Decimal
from pydantic import BaseModel, Field, ValidationError, model_validator
from src.domain.entities.product_margin import ProductMargin


class MarginFilter(BaseModel):
    tenant_id: str
    date_from: int
    date_to: int

    @model_validator(mode='before')
    def check_dates(cls, v):
        if v['date_to'] <= v['date_from']:
            raise ValueError('date_to must be greater than date_from')
        return v


async def get_margin_report(filters: dict, repository) -> Dict:
    """Return margin report grouped by SKU, with ABC curve and alerts.

    repository: should implement `fetch_sales(tenant_id, from_ts, to_ts)` returning list of dicts with keys sku, units, price, cost, variable_cost
    """
    try:
        validated = MarginFilter.model_validate(filters)
    except ValidationError as e:
        raise ValueError(str(e))

    raw = await repository.fetch_sales(validated.tenant_id, validated.date_from, validated.date_to)
    products = [ProductMargin.model_validate(r) for r in raw]

    # compute per SKU aggregates
    by_sku = {}
    for p in products:
        key = p.sku
        if key not in by_sku:
            by_sku[key] = {'units': 0, 'revenue': Decimal('0'), 'profit': Decimal('0')}
        by_sku[key]['units'] += p.units
        by_sku[key]['revenue'] += p.revenue()
        by_sku[key]['profit'] += p.profit_contribution()

    # ABC curve: sort SKUs by profit desc
    items = sorted(([k, v['profit']] for k, v in by_sku.items()), key=lambda x: x[1], reverse=True)
    total_profit = sum((it[1] for it in items), Decimal('0'))

    cumulative = Decimal('0')
    abc = []
    for sku, profit in items:
        cumulative += profit
        abc.append({'sku': sku, 'profit': str(profit), 'cumulative_pct': str((cumulative / total_profit * Decimal('100')) if total_profit else Decimal('0'))})

    # alerts: sold below cost
    alerts = [sku for sku, v in by_sku.items() if v['profit'] < 0]

    return {'summary': {'total_profit': str(total_profit)}, 'abc': abc, 'alerts': alerts}
