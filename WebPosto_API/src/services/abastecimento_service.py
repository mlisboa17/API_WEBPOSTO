from __future__ import annotations

import logging
from typing import Any

from src.gateway.webposto_client import WebPostoClient
from src.models.response_model import WebPostoResponse

logger = logging.getLogger(__name__)

FUEL_KEYWORDS = frozenset([
    "GASOLINA", "GAS COMUM", "ADITIVADA", "PREMIUM", "PODIUM",
    "ETANOL", "ALCOOL", "ÁLCOOL", "EAC", "EHC",
    "DIESEL", "S10", "S500", "S-10", "S-500",
    "GNV", "GAS NATURAL", "GÁS NATURAL",
])


class AbastecimentoService:
    """Serviço de abastecimentos com paginação completa e filtro de combustíveis."""
    
    MAX_PAGES = 200
    # WebPosto /ABASTECIMENTO retorna páginas de ~200 — NÃO usar 500 (corta na 1ª página).
    PAGE_SIZE = 200
    
    def __init__(self, client: WebPostoClient) -> None:
        self.client = client

    def _client_for(self, empresa_codigo: int | None) -> WebPostoClient:
        if not empresa_codigo:
            return self.client
        try:
            from src.core.config import resolve_company_api_key

            key = resolve_company_api_key(int(empresa_codigo))
            if key:
                return WebPostoClient.for_api_key(key)
        except Exception as exc:
            logger.warning(
                "Falha ao resolver API key empresa=%s: %s — usando client padrão",
                empresa_codigo,
                exc,
            )
        return self.client

    async def get_periodo(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: int | None = None,
    ) -> WebPostoResponse:
        """
        Busca TODOS os abastecimentos do período com paginação completa.
        
        - Itera sobre todas as páginas (page size real do WebPosto = 200)
        - Usa API key da filial quando empresaCodigo é informado
        - Filtra empresaCodigo no payload (API pode misturar filiais da rede)
        """
        params: dict[str, Any] = {
            "dataInicial": data_inicial,
            "dataFinal": data_final,
        }
        if empresa_codigo:
            params["empresaCodigo"] = empresa_codigo

        client = self._client_for(empresa_codigo)
        all_records: list[dict[str, Any]] = []
        ultimo_codigo: Any = None
        prev_ultimo: Any = None
        
        for page in range(self.MAX_PAGES):
            page_params = {**params}
            if ultimo_codigo is not None:
                page_params["ultimoCodigo"] = ultimo_codigo
            
            resp = await client.call_endpoint("abastecimento", params=page_params)
            
            if not resp.success:
                logger.warning(
                    "Falha na página %d de abastecimentos empresa=%s: %s",
                    page,
                    empresa_codigo,
                    resp.error,
                )
                break
            
            raw = resp.data
            batch: list[dict] = []
            new_ultimo: Any = None
            
            if isinstance(raw, dict):
                batch = raw.get("dados") or raw.get("data") or raw.get("resultados") or []
                new_ultimo = raw.get("ultimoCodigo")
            elif isinstance(raw, list):
                batch = raw
            
            if not batch:
                logger.info(
                    "Paginação completa empresa=%s: %d páginas, %d registros",
                    empresa_codigo,
                    page + 1,
                    len(all_records),
                )
                break

            raw_len = len(batch)
            # Isola a filial pedida (token de rede pode misturar Casa+VIP)
            if empresa_codigo:
                batch = [
                    row
                    for row in batch
                    if int(row.get("empresaCodigo") or row.get("empresa") or 0)
                    == int(empresa_codigo)
                ]

            all_records.extend(batch)
            
            if new_ultimo in (None, "", prev_ultimo, ultimo_codigo):
                logger.info(
                    "Fim da paginação (cursor): empresa=%s registros=%d",
                    empresa_codigo,
                    len(all_records),
                )
                break
            
            prev_ultimo = ultimo_codigo
            ultimo_codigo = new_ultimo
            
            # Página parcial pelo tamanho bruto da API (não pelo filtrado)
            if raw_len < self.PAGE_SIZE:
                logger.info(
                    "Última página parcial empresa=%s: raw=%d total_filtrado=%d",
                    empresa_codigo,
                    raw_len,
                    len(all_records),
                )
                break

        logger.info(
            "ABASTECIMENTO completo empresa=%s periodo=%s..%s total=%d",
            empresa_codigo,
            data_inicial,
            data_final,
            len(all_records),
        )
        return WebPostoResponse.ok({
            "dados": all_records,
            "total": len(all_records),
            "paginacao_completa": True,
            "empresaCodigo": empresa_codigo,
        })
    
    @staticmethod
    def is_fuel_product(product_name: str | None, group_name: str | None = None) -> bool:
        """Verifica se o produto é combustível baseado no nome/grupo."""
        name_upper = (product_name or "").upper()
        group_upper = (group_name or "").upper()
        
        return any(
            kw in name_upper or kw in group_upper
            for kw in FUEL_KEYWORDS
        )
    
    @staticmethod
    def classify_fuel_type(product_name: str | None) -> str | None:
        """Classifica o tipo de combustível."""
        name_upper = (product_name or "").upper()
        
        if any(kw in name_upper for kw in ["GNV", "GAS NATURAL", "GÁS NATURAL"]):
            return "GNV"
        if any(kw in name_upper for kw in ["DIESEL", "S10", "S500", "S-10", "S-500"]):
            return "DIESEL"
        if any(kw in name_upper for kw in ["ETANOL", "ALCOOL", "ÁLCOOL", "EAC", "EHC"]):
            return "ETANOL"
        if any(kw in name_upper for kw in ["GASOLINA", "GAS COMUM", "ADITIVADA", "PREMIUM", "PODIUM"]):
            return "GASOLINA"
        return None
