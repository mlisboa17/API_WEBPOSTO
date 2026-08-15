"""Monta o body do endpoint legado sem herdar BONO ou NEGRESCO."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .engine_schemas import ProductRegistrationRequest
from .fiscal_sheet_loader import normalize_cest, normalize_ncm


class RegistrationBodyBuilder:
    """Payload completo e hash deterministico. Campo ausente permanece ausente."""

    def build(self, request: ProductRegistrationRequest) -> dict[str, Any]:
        ncm, _ = normalize_ncm(request.ncm)
        cest, _ = normalize_cest(request.cest)
        if not ncm:
            raise ValueError("NCM invalido")
        cost = float(request.custo or 0)
        profile = request.perfil_fiscal
        body: dict[str, Any] = {
            "descricao": request.descricao,
            "descricaoResumida": request.descricao[:32].strip(),
            "tipoProduto": "P",
            "grupoCodigo": request.grupo_codigo,
            "codigoExterno": request.ean,
            "unidadeCompra": request.unidade,
            "unidadeVenda": request.unidade,
            "iat": "A",
            "ippt": "T",
            "precoCompra": cost,
            "precoCusto": cost,
            "precoVenda": request.preco_venda,
            "centroCustoCodigo": request.centro,
            "codigoBarras": request.ean,
            "codigoNcm": ncm,
            "ativo": True,
            "permiteVendaEstoqueNegativo": False,
            "produtoVendeFracionado": False,
            "utilizaCodigoBarras": True,
            "utilizaBalanca": False,
            "cdCfopEntrada": profile.get("cfop_entrada"),
            "cdCfopSaida": profile.get("cfop_saida"),
            "Tributação Monofásica": profile.get("tributacao_monofasica", 0),
            "tributoIcms": profile.get("tributo_icms"),
            "tributoPisCofins": profile.get("tributo_pis_cofins"),
        }
        if cest:
            body["codigoCest"] = cest
        return body

    def hash(self, body: dict[str, Any]) -> str:
        payload = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def sanitize(self, body: dict[str, Any]) -> dict[str, Any]:
        """Copia auditavel sem credencial. O body legado nao carrega chave."""
        return json.loads(json.dumps(body, ensure_ascii=False))
