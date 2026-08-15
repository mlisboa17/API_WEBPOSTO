"""Motor permanente de cadastro de produtos WebPosto.

A fachada publica e `ProductRegistrationService`. O orquestrador antigo das
FASES 3-10 permanece em `service.py` como `LegacyProductRegistrationService`.
"""

from __future__ import annotations

from .engine_schemas import ProductRegistrationRequest, ProductRegistrationResult, RiskAuthorization
from .registration_engine import ProductRegistrationService
from .service import ProductRegistrationService as LegacyProductRegistrationService
from .versions import ENGINE_VERSION

__all__ = [
    "ENGINE_VERSION",
    "LegacyProductRegistrationService",
    "ProductRegistrationRequest",
    "ProductRegistrationResult",
    "ProductRegistrationService",
    "RiskAuthorization",
]
