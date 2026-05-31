"""
Implementação do PostoGateway via API Quality (CHAVE na query).
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import List, Optional

from src.domain.entities.sales import Filial, Product, SalesInvoice, TankVolume
from src.domain.gateways.posto_gateway import PostoGateway
from src.infrastructure.clients.webposto_mappers import (
    _rows,
    map_filial,
    map_product,
    map_sales_invoice,
    map_tank_volume,
)
from src.infrastructure.http.http_client import ExternalHttpClient

logger = logging.getLogger(__name__)


class PostoAPIClient(PostoGateway):
    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._chave = api_key
        self._http = ExternalHttpClient(self._base_url)

    def _params(self, extra: Optional[dict] = None) -> dict:
        p = {"CHAVE": self._chave}
        if extra:
            p.update({k: v for k, v in extra.items() if v is not None})
        return p

    async def _get_json(self, path: str, params: Optional[dict] = None) -> object:
        r = await self._http.get(path, params=self._params(params))
        if r.status_code in (401, 403):
            logger.critical(
                "Permissão negada na API WebPosto path=%s status=%s",
                path,
                r.status_code,
            )
            raise PermissionError(f"CHAVE sem acesso a {path} (HTTP {r.status_code})")
        if r.status_code >= 400:
            logger.error("Erro HTTP %s em %s: %s", r.status_code, path, r.text[:300])
            return []
        try:
            return r.json()
        except Exception:
            return r.text

    async def get_vendas_recentes(self, horas: int = 24) -> List[SalesInvoice]:
        fim = date.today()
        ini = fim - timedelta(days=max(1, (horas + 23) // 24))
        raw = await self._get_json(
            "/INTEGRACAO/VENDA",
            {
                "dataInicial": ini.isoformat(),
                "dataFinal": fim.isoformat(),
                "pagina": 0,
                "tamanhoPagina": 200,
            },
        )
        return [map_sales_invoice(r) for r in _rows(raw)]

    async def get_volume_tanques(self) -> List[TankVolume]:
        raw = await self._get_json("/INTEGRACAO/ESTOQUE", {"pagina": 0, "tamanhoPagina": 100})
        return [map_tank_volume(r) for r in _rows(raw)]

    async def get_produto(self, produto_id: int) -> Optional[Product]:
        raw = await self._get_json(
            "/INTEGRACAO/PRODUTO",
            {"codigo": produto_id, "pagina": 0, "tamanhoPagina": 5},
        )
        rows = _rows(raw)
        if not rows:
            return None
        emp = await self._get_json(
            "/INTEGRACAO/PRODUTO_EMPRESA",
            {"produtoCodigo": produto_id, "pagina": 0, "tamanhoPagina": 5},
        )
        emp_rows = _rows(emp)
        return map_product(rows[0], emp_rows[0] if emp_rows else None)

    async def listar_produtos(
        self,
        *,
        pagina: int = 0,
        tamanho: int = 50,
        nome: Optional[str] = None,
    ) -> List[Product]:
        raw = await self._get_json(
            "/INTEGRACAO/PRODUTO",
            {"pagina": pagina, "tamanhoPagina": tamanho, "nome": nome},
        )
        return [map_product(r) for r in _rows(raw)]

    async def listar_filiais(self) -> List[Filial]:
        raw = await self._get_json("/INTEGRACAO/EMPRESAS", {})
        return [map_filial(r) for r in _rows(raw)]

    async def get_caixa_periodo(self, data_inicial: date, data_final: date) -> List[dict]:
        raw = await self._get_json(
            "/INTEGRACAO/CAIXA",
            {
                "dataInicial": data_inicial.isoformat(),
                "dataFinal": data_final.isoformat(),
                "pagina": 0,
                "tamanhoPagina": 200,
            },
        )
        return _rows(raw)
