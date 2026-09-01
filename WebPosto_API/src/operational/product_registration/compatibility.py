"""Adaptadores para scripts das ondas 1-5. Nao quebra imports antigos.

Toda execucao de escrita termina em ProductRegistrationService.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .body_builder import (  # noqa: F401
    build_registration_body,
    calculate_body_hash,
    create_registration_request,
    get_default_bono_template,
)
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
from .registration_engine import ProductRegistrationService
from .service import ProductRegistrationService as LegacyProductRegistrationService  # noqa: F401
from .stores import interpret_lock  # noqa: F401


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


def post_product(
    client: Any,
    reader: Any,
    key: str,
    body: dict[str, Any],
    *,
    ean: str,
    from_code: int = 0,
    checkpoint_path: Path | str | None = None,
    **_legacy: Any,
):
    """Adapta argumentos antigos e delega a unica fachada de escrita."""
    service = ProductRegistrationService(Path(checkpoint_path or "."))
    return service.post_product(client, reader, key, body, ean=ean, from_code=from_code)
