"""Montar request JSON conforme template BONO — FASE 7."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .schemas import ProductAnalysis, RegistrationRequest


def build_registration_body(
    product: ProductAnalysis,
    template: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Monta body para POST /INTEGRACAO/INCLUIR_PRODUTO.
    
    Usa template BONO como base e ajusta campos necessários.
    """
    if template is None:
        template = get_default_bono_template()

    body = template.get("body", {}).copy()

    # Ajustar campos obrigatórios
    body["descricao"] = product.descricao
    body["descricaoResumida"] = product.descricao[:50]  # Resumida
    body["codigoBarras"] = product.ean
    body["precoVenda"] = float(product.preco_venda)

    if product.grupo_api_codigo:
        body["grupoCodigo"] = product.grupo_api_codigo

    if product.centro_api_codigo:
        body["centroCustoCodigo"] = product.centro_api_codigo

    if product.ncm:
        body["codigoNcm"] = product.ncm

    if product.cest:
        body["codigoCest"] = product.cest

    if product.tributo_icms:
        body["tributoIcms"] = product.tributo_icms

    if product.tributo_pis_cofins:
        body["tributoPisCofins"] = product.tributo_pis_cofins

    return body


def get_default_bono_template() -> dict[str, Any]:
    """Template BONO padrão (BISCOITO RECHEADO)."""
    return {
        "body": {
            "descricao": "",
            "descricaoResumida": "",
            "tipoProduto": "P",
            "grupoCodigo": 55446,
            "unidadeCompra": "UN",
            "unidadeVenda": "UN",
            "iat": "A",
            "ippt": "T",
            "precoCompra": 2.0,
            "precoCusto": 2.0,
            "precoVenda": 5.0,
            "centroCustoCodigo": 24886,
            "ativo": True,
            "codigoBarras": "",
            "codigoNcm": "19053100",
            "codigoCest": "1705300",
            "permiteVendaEstoqueNegativo": False,
            "produtoVendeFracionado": False,
            "utilizaBalanca": False,
            "codigoBarrasPrincipal": True,
            "enviarGtin": True,
            "venderSemCodigoBarras": "N",
            "cdCfopEntrada": "1.102",
            "cdCfopSaida": "5.405",
            "naturezaReceitaCodigo": "001",
            "tributoIcms": {
                "cstEntrada": "060",
                "cstSaida": "060",
                "percentualIcmsEntrada": 0.0,
                "percentualIcmsSaida": 0.0,
                "valorPercentualFcp": 0,
                "dsCsosnEntrada": "0",
                "dsCsosnSaida": "0",
            },
            "tributoPisCofins": {
                "cstPisEntrada": "50",
                "cstPisSaida": "01",
                "percentualPisEntrada": 0.65,
                "percentualPisSaida": 0.65,
                "percentualBaseCalculoPisEntrada": 100,
                "percentualBaseCalculoPisSaida": 100,
                "cstCofinsEntrada": "50",
                "cstCofinsSaida": "01",
                "percentualCofinsEntrada": 3.0,
                "percentualCofinsSaida": 3.0,
                "percentualBaseCalculoCofinsEntrada": 100,
                "percentualBaseCalculoCofinsEntrada": 100,
            },
        },
        "meta": {
            "endpoint": "POST /INTEGRACAO/INCLUIR_PRODUTO",
            "company": 118508,
            "companyName": "CONVENIENCIA 24 HORAS",
        },
    }


def calculate_body_hash(body: dict[str, Any]) -> str:
    """Calcula SHA-256 do body JSON (determinístico)."""
    body_json = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body_json.encode()).hexdigest()


def create_registration_request(
    product: ProductAnalysis,
    template: dict[str, Any] | None = None,
) -> RegistrationRequest:
    """Cria RegistrationRequest com body e hash."""
    body = build_registration_body(product, template)
    body_hash = calculate_body_hash(body)

    return RegistrationRequest(
        body_hash=body_hash,
        body=body,
    )
