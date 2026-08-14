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
    Garante presença de campos críticos: codigoExterno, utilizaCodigoBarras, Tributação Monofásica.
    """
    if template is None:
        template = get_default_bono_template()

    body = template.get("body", {}).copy()

    # Campos obrigatórios sempre presentes
    body["descricao"] = product.descricao
    body["descricaoResumida"] = product.descricao[:50]  # Resumida
    body["codigoBarras"] = product.ean
    body["codigoExterno"] = product.ean  # CRÍTICO: mesmo valor do EAN
    body["utilizaCodigoBarras"] = True  # CRÍTICO: sempre True para produtos com EAN
    body["Tributação Monofásica"] = 0  # CRÍTICO: campo obrigatório
    body["precoVenda"] = float(product.preco_venda)

    # Campos condicionais
    if product.grupo_api_codigo:
        body["grupoCodigo"] = product.grupo_api_codigo

    if product.centro_api_codigo:
        body["centroCustoCodigo"] = product.centro_api_codigo

    if product.ncm:
        body["codigoNcm"] = product.ncm

    if product.cest:
        body["codigoCest"] = product.cest

    # Tributação ICMS com validação de CSOSN
    if product.tributo_icms:
        icms = product.tributo_icms.copy()
        # Garantir que dsCsosnEntrada e dsCsosnSaida sejam strings "0" e não vazias
        if "dsCsosnEntrada" in icms and icms["dsCsosnEntrada"] in ("", None):
            icms["dsCsosnEntrada"] = "0"
        if "dsCsosnSaida" in icms and icms["dsCsosnSaida"] in ("", None):
            icms["dsCsosnSaida"] = "0"
        body["tributoIcms"] = icms

    if product.tributo_pis_cofins:
        body["tributoPisCofins"] = product.tributo_pis_cofins

    return body


def get_default_bono_template() -> dict[str, Any]:
    """
    Template BONO padrão baseado no artefato de sucesso definitivo.
    
    Fonte: ninth_legacy_icms_csosn_zero_probe_report.json
    Status: Comprovadamente aceito (HTTP 200, codProduto 2481160)
    """
    return {
        "body": {
            "descricao": "",
            "descricaoResumida": "",
            "tipoProduto": "P",
            "grupoCodigo": 55446,
            "codigoExterno": "",  # CRÍTICO: deve ser igual ao EAN
            "unidadeCompra": "UN",
            "unidadeVenda": "UN",
            "iat": "A",
            "ippt": "T",
            "precoCompra": 2.0,
            "precoCusto": 2.0,
            "precoVenda": 5.0,
            "centroCustoCodigo": 24886,
            "codigoBarras": "",
            "codigoNcm": "19053100",
            "codigoCest": "1705300",
            "ativo": True,
            "permiteVendaEstoqueNegativo": False,
            "produtoVendeFracionado": False,
            "utilizaCodigoBarras": True,  # CRÍTICO: sempre True
            "utilizaBalanca": False,
            "cdCfopEntrada": "1.102",
            "cdCfopSaida": "5.405",
            "Tributação Monofásica": 0,  # CRÍTICO: campo obrigatório
            "tributoIcms": {
                "percentualIcmsSaida": 0.0,
                "cstSaida": "060",
                "percentualIcmsEntrada": 0.0,
                "cstEntrada": "060",
                "dsCsosnEntrada": "0",  # CRÍTICO: string "0", não vazio
                "dsCsosnSaida": "0",    # CRÍTICO: string "0", não vazio
                "valorPercentualFcp": 0,
            },
            "tributoPisCofins": {
                "percentualCofinsEntrada": 3.0,
                "percentualBaseCalculoCofinsEntrada": 100,
                "cstCofinsEntrada": "50",
                "percentualCofinsSaida": 3.0,
                "percentualBaseCalculoCofinsSaida": 100,
                "cstCofinsSaida": "01",
                "percentualPisEntrada": 0.65,
                "percentualBaseCalculoPisEntrada": 100,
                "cstPisEntrada": "50",
                "percentualPisSaida": 0.65,
                "percentualBaseCalculoPisSaida": 100,
                "cstPisSaida": "01",
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
