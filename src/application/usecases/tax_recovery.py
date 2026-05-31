from __future__ import annotations
from decimal import Decimal
from typing import List, Dict, Protocol
import asyncio

from src.domain.tax_engine import compute_recoverable
from src.domain.adelaide_engine import AdelaideEngine, ProductAuditInput, TaxContext, TaxMatrix


class TaxMatrixRepository(Protocol):
    async def get_matrix(self, uf: str, cnae: str, ncm: str | None) -> TaxMatrix | None:
        ...


async def tax_recovery_report(sales: List[Dict], regime: str = 'presumed') -> Dict:
    """Compute recoverable tax totals and top offenders from a list of sales.

    sales: list of {sku, units, price, cost, sku_meta}
    """
    total_recoverable = Decimal('0')
    per_sku = {}

    async def _process(sale):
        nonlocal total_recoverable
        price = Decimal(str(sale.get('price', '0')))
        cost = Decimal(str(sale.get('cost', '0')))
        sku_meta = sale.get('sku_meta', {})
        recover = compute_recoverable(price, cost, sku_meta, regime)
        total_recoverable_local = recover * Decimal(sale.get('units', 1))
        total_recoverable += total_recoverable_local
        per_sku.setdefault(sale.get('sku'), Decimal('0'))
        per_sku[sale.get('sku')] += total_recoverable_local

    # process in parallel chunks
    await asyncio.gather(*[_process(s) for s in sales])

    # top offenders (sorted by recoverable desc)
    top = sorted(per_sku.items(), key=lambda x: x[1], reverse=True)[:20]
    return {'total_recoverable': str(total_recoverable.quantize(Decimal('0.0001'))), 'top_offenders': [(k, str(v.quantize(Decimal('0.0001')))) for k, v in top]}


async def run_adelaide_recovery(
    context_payload: Dict,
    products: List[Dict],
    matrix_repository: TaxMatrixRepository,
    engine: AdelaideEngine | None = None,
) -> Dict:
    """Run Adelaide tax recovery audit with injected repository dependency."""
    engine = engine or AdelaideEngine()
    context = TaxContext(**context_payload)

    findings = []
    total_credit = Decimal("0")
    grouped_credit: dict[str, Decimal] = {}

    async def _process(product_row: Dict) -> None:
        nonlocal total_credit
        product = ProductAuditInput(**product_row)
        matrix = await matrix_repository.get_matrix(context.uf, context.cnae, product.ncm)
        if matrix is None:
            matrix = TaxMatrix(ncm=product.ncm or "00000000", cst=product.cst or "000", monofasico=False)
        finding = engine.audit_product(context, product, matrix)
        findings.append(finding.model_dump())
        total_credit += finding.recoverable_credit
        group_key = product_row.get("grupo_produto", "SEM_GRUPO")
        grouped_credit.setdefault(group_key, Decimal("0"))
        grouped_credit[group_key] += finding.recoverable_credit

    await asyncio.gather(*[_process(product_row) for product_row in products])

    ranking = sorted(grouped_credit.items(), key=lambda item: item[1], reverse=True)
    return {
        "context": context.model_dump(),
        "total_credit": str(total_credit.quantize(Decimal("0.01"))),
        "groups": [{"group": key, "credit": str(value.quantize(Decimal("0.01")))} for key, value in ranking],
        "findings": findings,
    }
