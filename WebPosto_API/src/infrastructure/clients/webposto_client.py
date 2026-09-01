"""
Cliente de auditoria WebPosto — implementação do AuditGateway (infraestrutura).
Somente dados reais da API; falha explícita se a fonte obrigatória não responder.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any, List, Optional

from src.domain.entities.audit import AuditRawData, SubCentroCusto
from src.domain.exceptions.audit_fetch import AuditFetchError
from src.domain.gateways.audit_gateway import AuditGateway
from src.infrastructure.clients.webposto_audit_mappers import build_audit_raw
from src.infrastructure.clients.webposto_pagination import (
    fetch_all_abastecimento,
    fetch_all_paginated,
)
from src.gateway.webposto_client import WebPostoClient

logger = logging.getLogger(__name__)

__all__ = ["WebPostoAuditClient", "WebPostoClient"]


class WebPostoAuditClient(AuditGateway):
    """ACL: encapsula WebPostoClient síncrono em thread pool."""

    def __init__(self, webposto_client: Any, *, posto_id: str = "default") -> None:
        self._client = webposto_client
        self._posto_id = posto_id

    async def fetch_transactions(
        self,
        data_inicio: date,
        data_fim: date,
        sub_centro: SubCentroCusto,
        *,
        posto_id: str = "default",
        filial: list[int] | None = None,
    ) -> AuditRawData:
        pid = posto_id or self._posto_id
        return await asyncio.to_thread(
            self._fetch_sync,
            data_inicio,
            data_fim,
            sub_centro,
            pid,
            filial,
        )

    def _fetch_sync(
        self,
        data_inicio: date,
        data_fim: date,
        sub_centro: SubCentroCusto,
        posto_id: str,
        filial: Optional[List[int]],
    ) -> AuditRawData:
        fin = self._client.financeiro
        ab = self._client.abastecimento
        integ = self._client.integracoes
        erros: list[str] = []

        caixa_rows: list[dict] = []
        apresentado_rows: list[dict] = []
        abastecimento_rows: list[dict] = []
        venda_rows: list[dict] = []
        titulo_rows: list[dict] = []

        try:
            caixa_rows = fetch_all_paginated(
                fin.listar_caixa, data_inicio, data_fim, filial=filial
            )
        except Exception as exc:
            erros.append(f"CAIXA: {exc}")
            logger.warning("CAIXA indisponível: %s", exc)

        try:
            apresentado_rows = fetch_all_paginated(
                fin.listar_caixa_apresentado, data_inicio, data_fim, filial=filial
            )
        except Exception as exc:
            erros.append(f"CAIXA_APRESENTADO: {exc}")
            logger.warning("CAIXA_APRESENTADO indisponível: %s", exc)

        if sub_centro == SubCentroCusto.PISTA:
            try:
                abastecimento_rows = fetch_all_abastecimento(
                    ab, data_inicio, data_fim, filial=filial
                )
            except Exception as exc:
                erros.append(f"ABASTECIMENTO: {exc}")
                logger.warning("ABASTECIMENTO indisponível: %s", exc)
            if not abastecimento_rows:
                raise AuditFetchError(
                    "Nenhum abastecimento retornado pela API no período "
                    f"({data_inicio} a {data_fim}). Verifique datas, filial e permissões da chave.",
                    erros=erros,
                )
        else:
            try:
                venda_rows = fetch_all_paginated(
                    integ.listar_vendas, data_inicio, data_fim, filial=filial
                )
            except Exception as exc:
                erros.append(f"VENDA: {exc}")
                logger.warning("VENDA indisponível: %s", exc)
            if not venda_rows:
                raise AuditFetchError(
                    f"Nenhuma venda PDV retornada para {sub_centro.value} no período "
                    f"({data_inicio} a {data_fim}).",
                    erros=erros,
                )

        try:
            titulo_rows = fetch_all_paginated(
                fin.listar_titulos_pagar, data_inicio, data_fim, filial=filial
            )
        except Exception as exc:
            logger.warning("TITULO_PAGAR indisponível (despesas omitidas): %s", exc)

        if erros and sub_centro == SubCentroCusto.PISTA and not abastecimento_rows:
            raise AuditFetchError(
                "Não foi possível obter dados reais da WebPosto para PISTA.",
                erros=erros,
            )

        return build_audit_raw(
            posto_id=posto_id,
            sub_centro=sub_centro,
            data_inicio=data_inicio,
            data_fim=data_fim,
            caixa_rows=caixa_rows,
            apresentado_rows=apresentado_rows,
            abastecimento_rows=abastecimento_rows,
            venda_rows=venda_rows,
            titulo_pagar_rows=titulo_rows,
            erros_api=erros,
        )
