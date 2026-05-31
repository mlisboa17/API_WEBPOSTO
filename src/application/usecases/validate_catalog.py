from __future__ import annotations
from decimal import Decimal
from typing import Dict, Any
import asyncio

from src.domain.entities.tax_rule import ProductTaxProfile


async def validate_catalog(local: Dict[str, Any], reference_fetcher) -> Dict:
    """Compare local product tax profile with a reference source.

    local: dict with product fields
    reference_fetcher: async callable(sku) -> reference dict or None
    """
    # validate local profile
    profile = ProductTaxProfile.model_validate(local)

    # fetch reference
    ref = await reference_fetcher(profile.sku)
    if not ref:
        return {'status': 'not_found', 'sku': profile.sku}

    ref_profile = ProductTaxProfile.model_validate(ref)

    diffs = {}
    for field in ('ncm', 'cest', 'cfop', 'cst'):
        if getattr(profile, field) != getattr(ref_profile, field):
            diffs[field] = {'local': getattr(profile, field), 'ref': getattr(ref_profile, field)}

    # compute tax impact sample for a unit price (if provided)
    impact = None
    if 'price' in local and local.get('price'):
        price = Decimal(str(local['price']))
        local_tax = (profile.aliquota_icms + profile.aliquota_pis + profile.aliquota_cofins) / Decimal('100') * price
        ref_tax = (ref_profile.aliquota_icms + ref_profile.aliquota_pis + ref_profile.aliquota_cofins) / Decimal('100') * price
        impact = str((local_tax - ref_tax).quantize(Decimal('0.0001')))

    return {'sku': profile.sku, 'status': ('ok' if not diffs else 'divergent'), 'diffs': diffs, 'impact_per_unit': impact}
