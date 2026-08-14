"""GET pós-cadastro para validação — FASE 8."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class PostVerifier:
    """Verifica se produto foi criado via GET /INTEGRACAO/V1/PRODUTOS."""

    def __init__(
        self,
        base_url: str = "https://web.qualityautomacao.com.br",
        chave: str | None = None,
        timeout: int = 120,
    ):
        self.base_url = base_url.rstrip("/")
        self.chave = chave
        self.timeout = timeout

    async def verify_product_created(
        self,
        ean: str,
        expected_codigo: int | None = None,
        expected_descricao: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> dict[str, Any]:
        """
        Busca produto por EAN após 2s de espera.
        
        Retorna {
            found: bool,
            produto: dict | None,
            verification_status: str,
        }
        """
        
        # Aguardar propagação
        await asyncio.sleep(2)

        endpoint = f"{self.base_url}/INTEGRACAO/V1/PRODUTOS"
        params = {"pageIndex": 1, "pageSize": 1000}
        if self.chave:
            params["CHAVE"] = self.chave

        try:
            if client is None:
                async with httpx.AsyncClient(timeout=self.timeout) as _client:
                    response = await _client.get(endpoint, params=params)
            else:
                response = await client.get(endpoint, params=params)

            logger.info(f"[GET_VERIFY] EAN {ean}: HTTP {response.status_code}")

            if response.status_code != 200:
                logger.warning(
                    f"[GET_VERIFY_FAIL] EAN {ean}: HTTP {response.status_code}"
                )
                return {
                    "found": False,
                    "produto": None,
                    "verification_status": f"HTTP {response.status_code}",
                }

            # Parsear resposta paginada
            try:
                resp_json = response.json()
                produtos = resp_json.get("result", resp_json.get("data", []))
                
                if not isinstance(produtos, list):
                    produtos = []

            except Exception as e:
                logger.error(f"[GET_PARSE_ERROR] EAN {ean}: {e}")
                return {
                    "found": False,
                    "produto": None,
                    "verification_status": "PARSE_ERROR",
                }

            # Buscar por EAN
            for product in produtos:
                product_ean = str(product.get("ean") or product.get("codigoBarras") or "").strip()
                if product_ean == str(ean).strip():
                    logger.info(
                        f"[FOUND] EAN {ean}: codProduto={product.get('codigo')}, "
                        f"descricao={product.get('descricao')[:50]}"
                    )
                    return {
                        "found": True,
                        "produto": product,
                        "verification_status": "VERIFIED",
                    }

            logger.warning(f"[NOT_FOUND] EAN {ean} não encontrado no GET")
            return {
                "found": False,
                "produto": None,
                "verification_status": "NOT_FOUND_IN_GET",
            }

        except Exception as e:
            logger.error(f"[VERIFY_ERROR] EAN {ean}: {e}")
            return {
                "found": False,
                "produto": None,
                "verification_status": f"ERROR: {e}",
            }
