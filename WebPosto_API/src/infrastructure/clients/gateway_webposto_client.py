from __future__ import annotations

from datetime import date
from typing import Any

import httpx


class GatewayWebPostoClient:
    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._timeout = httpx.Timeout(timeout_seconds, connect=min(timeout_seconds, 3.0))

    @staticmethod
    def _extract_rows(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            if isinstance(payload.get("resultados"), list):
                return payload["resultados"]
            if isinstance(payload.get("data"), list):
                return payload["data"]
        return []

    async def fetch_expenses(
        self,
        *,
        posto_id: str,
        data_consulta: date,
        base_url: str,
        api_key: str,
    ) -> list[dict[str, Any]]:
        # WebPosto REST docs: autenticação via CHAVE na query.
        params = {
            "CHAVE": api_key,
            "dataInicial": data_consulta.isoformat(),
            "dataFinal": data_consulta.isoformat(),
        }
        async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=self._timeout) as client:
            response = await client.get("/INTEGRACAO/FINANCEIRO", params=params)
            if response.status_code in (401, 403):
                # Mantém o gateway útil mesmo quando FINANCEIRO não está liberado.
                alt = await client.get("/INTEGRACAO/ABASTECIMENTO", params=params)
                alt.raise_for_status()
                abastecimentos = self._extract_rows(alt.json())
                synthesized: list[dict[str, Any]] = []
                for row in abastecimentos:
                    valor = (
                        row.get("valorTotal")
                        or row.get("valor")
                        or row.get("total")
                    )
                    descricao = (
                        row.get("produto")
                        or row.get("produtoDescricao")
                        or row.get("combustivel")
                        or row.get("codigoProduto")
                    )
                    ts = (
                        row.get("dataHoraAbastecimento")
                        or row.get("dataAbastecimento")
                        or row.get("dataFiscal")
                        or row.get("data")
                        or row.get("dataEmissao")
                    )
                    if valor is None or descricao is None or ts is None:
                        # Apenas registros com campos reais completos.
                        continue
                    synthesized.append(
                        {
                            "descricao": descricao,
                            "valor": valor,
                            "timestamp": ts,
                            "origem": "abastecimento_fallback",
                            "posto_id": posto_id,
                        }
                    )
                return synthesized

            response.raise_for_status()
            return self._extract_rows(response.json())
