"""Adaptador temporario e deprecated. Nao herda BONO.

Use RegistrationBodyBuilder. Este modulo existe so para imports antigos.
"""

from __future__ import annotations

import warnings
from typing import Any

from .engine_schemas import ProductRegistrationRequest, RiskAuthorization
from .registration_body import RegistrationBodyBuilder
from .schemas import ProductAnalysis, RegistrationRequest

_DEPRECATED = (
    "body_builder esta deprecated e nao herda BONO; use RegistrationBodyBuilder "
    "com proveniencia explicita de fiscal, custo e grupo"
)


def _analysis_to_request(product: ProductAnalysis) -> ProductRegistrationRequest:
    return ProductRegistrationRequest(
        empresa=int(getattr(product, "empresa_codigo", 0) or 118508),
        centro=int(product.centro_api_codigo or 0),
        ean=product.ean,
        descricao=product.descricao,
        preco_venda=float(product.preco_venda),
        ncm=str(product.ncm or ""),
        cest=product.cest,
        grupo_codigo=product.grupo_api_codigo,
        custo=None,
        cost_source=None,
        perfil_fiscal={
            "tributo_icms": product.tributo_icms,
            "tributo_pis_cofins": product.tributo_pis_cofins,
            "cfop_entrada": None,
            "cfop_saida": None,
            "tributacao_monofasica": 0,
        },
        authorization=RiskAuthorization(),
    )


def build_registration_body(
    product: ProductAnalysis,
    template: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Monta body so com campos do produto. Template e ignorado."""
    warnings.warn(_DEPRECATED, DeprecationWarning, stacklevel=2)
    if template:
        warnings.warn(
            "template ignorado: nenhum campo fiscal, custo ou grupo e herdado",
            DeprecationWarning,
            stacklevel=2,
        )
    return RegistrationBodyBuilder().build(_analysis_to_request(product))


def get_default_bono_template() -> dict[str, Any]:
    """Deprecated. Nao devolve campos fiscais, custo ou grupo."""
    warnings.warn(_DEPRECATED, DeprecationWarning, stacklevel=2)
    return {"body": {}, "meta": {"deprecated": True, "inherits_bono": False}}


def calculate_body_hash(body: dict[str, Any]) -> str:
    return RegistrationBodyBuilder().hash(body)


def create_registration_request(
    product: ProductAnalysis,
    template: dict[str, Any] | None = None,
) -> RegistrationRequest:
    body = build_registration_body(product, template)
    return RegistrationRequest(body_hash=calculate_body_hash(body), body=body)
