"""Adaptadores para scripts das ondas 1-5. Nao quebra imports antigos."""

from __future__ import annotations

from .company_credentials import (  # noqa: F401
    HttpProductReader,
    company_guard,
    resolve_credential,
)
from .dfe_cost_resolver import build_authorized_index, cost_from_index  # noqa: F401
from .duplicate_checker import (  # noqa: F401
    find_description_duplicates,
    looks_fabricated_gtin,
)
from .ean_service import gtin_prefix_length_conflict, validate_ean_strict  # noqa: F401
from .final_wave import classify_final_duplicate, pick_icms_row  # noqa: F401
from .fiscal_profiles import payload_id, payload_key, special_category  # noqa: F401
from .policies.cost_policy import CostPolicy
from .service import ProductRegistrationService as LegacyProductRegistrationService  # noqa: F401


def validate_cost(cost, cost_info, *, allow_pending_dfe_cost: bool, accept_negative_margin: bool = False):
    """Ponte para scripts que ainda chamam validate_cost local."""
    decision = CostPolicy().evaluate(
        cost=cost,
        cost_source=(cost_info or {}).get("source"),
        cost_status=(cost_info or {}).get("cost_status"),
        sale_price=None,
        allow_pending_dfe_cost=allow_pending_dfe_cost,
        accept_negative_margin=accept_negative_margin,
    )
    return decision.allowed, decision.decision
