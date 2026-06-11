from __future__ import annotations

import asyncio
from datetime import date
from time import perf_counter
from typing import Any

import httpx

from src.core.config import CoreConfig, load_core_config
from src.core.logger import get_logger, log_structured
from src.metrics.collector import metrics_collector
from src.models.error_model import WebPostoError
from src.models.response_model import WebPostoResponse
from src.utils.circuit_breaker import SimpleCircuitBreaker
from src.utils.permission_cache import get_permissions, is_cache_fresh, set_permissions
from src.utils.retry import retry_async

ENDPOINTS = {
    "abastecimento": "/INTEGRACAO/ABASTECIMENTO",
    "financeiro": "/INTEGRACAO/TITULO_PAGAR",
    "titulo_receber": "/INTEGRACAO/TITULO_RECEBER",
    "movimento_conta": "/INTEGRACAO/MOVIMENTO_CONTA",
    "transferencia_bancaria": "/INTEGRACAO/TRANSFERENCIA_BANCARIA",
    "caixa": "/INTEGRACAO/CAIXA",
    "caixa_apresentado": "/INTEGRACAO/CAIXA_APRESENTADO",
    "caixa_rede": "/INTEGRACAO/CONSULTAR_CAIXA_REDE",
    "caixa_apresentado_rede": "/INTEGRACAO/CONSULTAR_CAIXA_APRESENTADO_REDE",
    "analise_vendas_combustivel": "/INTEGRACAO/CONSULTAR_ANALISE_VENDAS_COMBUSTIVEL",
    "despesas_financeiro_rede": "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
    "empresas": "/INTEGRACAO/EMPRESAS",
    "conta": "/INTEGRACAO/CONTA",
    "venda": "/INTEGRACAO/VENDA",
    "venda_item": "/INTEGRACAO/VENDA_ITEM",
    "venda_item_rede": "/INTEGRACAO/CONSULTAR_VENDA_ITEM_REDE",
    "venda_forma_pagamento": "/INTEGRACAO/VENDA_FORMA_PAGAMENTO",
    "venda_forma_pagamento_rede": "/INTEGRACAO/CONSULTAR_VENDA_FORMA_PAGAMENTO_REDE",
    "nfce": "/INTEGRACAO/NFCE",
    "produto_estoque": "/INTEGRACAO/PRODUTO_ESTOQUE",
    "produto": "/INTEGRACAO/PRODUTO",
    "produto_empresa": "/INTEGRACAO/PRODUTO_EMPRESA",
    "produto_rede": "/INTEGRACAO/PRODUTO_REDE",
    "produto_empresa_rede": "/INTEGRACAO/PRODUTO_EMPRESA_REDE",
    "produto_combustivel": "/INTEGRACAO/PRODUTO_COMBUSTIVEL",
    "tanque": "/INTEGRACAO/TANQUE",
    "estoque_periodo": "/INTEGRACAO/ESTOQUE_PERIODO",
    "lmc_rede": "/INTEGRACAO/CONSULTAR_LMC_REDE",
    "funcionario": "/INTEGRACAO/FUNCIONARIO",
}


class WebPostoClient:
    _permissions_lock: asyncio.Lock | None = None

    def __init__(self, config: CoreConfig | None = None) -> None:
        self.config = config or load_core_config()
        self.logger = get_logger(__name__)
        self.breaker = SimpleCircuitBreaker(
            failure_threshold=self.config.circuit_fail_threshold,
            block_seconds=self.config.circuit_block_seconds,
        )

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

    @staticmethod
    def _date_params() -> dict[str, str]:
        today = date.today().isoformat()
        return {"dataInicial": today, "dataFinal": today}

    def _discovery_params(self, endpoint_key: str) -> dict[str, str] | None:
        # Endpoint analitico pode retornar payload muito grande com filtro diario.
        # Probe sem datas reduz risco de timeout e valida permissao real.
        if endpoint_key in {"analise_vendas_combustivel", "empresas"}:
            return None
        return self._date_params()

    def _with_key(self, params: dict[str, Any] | None) -> dict[str, Any]:
        final = {"CHAVE": self.config.webposto_api_key}
        if params:
            final.update({k: v for k, v in params.items() if v is not None})
        return final

    def _endpoint_timeout(self, endpoint_key: str) -> httpx.Timeout:
        base = self.config.timeout_seconds
        if endpoint_key in {
            "analise_vendas_combustivel",
            "despesas_financeiro_rede",
            "venda",
            "venda_item",
            "venda_item_rede",
            "venda_forma_pagamento",
            "venda_forma_pagamento_rede",
            "nfce",
            "produto_estoque",
            "estoque_periodo",
            "lmc_rede",
            "funcionario",
        }:
            base = max(20.0, base)
        return httpx.Timeout(base, connect=min(5.0, base))

    async def discover_permissions(self, force: bool = False) -> dict[str, bool]:
        if not force and is_cache_fresh(self.config.permission_ttl_seconds):
            cached = get_permissions()
            if all(key in cached for key in ENDPOINTS):
                return cached

        if WebPostoClient._permissions_lock is None:
            WebPostoClient._permissions_lock = asyncio.Lock()

        async with WebPostoClient._permissions_lock:
            if not force and is_cache_fresh(self.config.permission_ttl_seconds):
                cached = get_permissions()
                if all(key in cached for key in ENDPOINTS):
                    return cached

            permissions: dict[str, bool] = {}

            async def _probe_permission(client: httpx.AsyncClient, key: str, path: str):
                params = self._with_key(self._discovery_params(key))
                started = perf_counter()
                try:
                    response = await client.get(path, params=params)
                    latency_ms = (perf_counter() - started) * 1000
                    # Alguns endpoints validam payload e retornam 400/422 mesmo com chave autorizada.
                    allowed = response.status_code not in {401, 403}
                    permissions[key] = allowed
                    metrics_collector.record(path, response.status_code, latency_ms)
                    log_structured(
                        self.logger,
                        {
                            "system": "webposto",
                            "endpoint": path,
                            "status": response.status_code,
                            "latency_ms": round(latency_ms, 2),
                            "has_data": allowed,
                            "synthetic": False,
                            "check": "permission_discovery",
                        },
                    )
                except Exception as exc:
                    permissions[key] = False
                    log_structured(
                        self.logger,
                        {
                            "system": "webposto",
                            "endpoint": path,
                            "status": 0,
                            "latency_ms": round((perf_counter() - started) * 1000, 2),
                            "has_data": False,
                            "synthetic": False,
                            "check": "permission_discovery",
                            "error": str(exc)[:220],
                        },
                    )

            async with httpx.AsyncClient(
                base_url=self.config.webposto_base_url,
                timeout=httpx.Timeout(max(20.0, self.config.timeout_seconds), connect=min(5.0, max(20.0, self.config.timeout_seconds))),
            ) as client:
                tasks = [_probe_permission(client, key, path) for key, path in ENDPOINTS.items()]
                await asyncio.gather(*tasks)

            set_permissions(permissions)
            return permissions


    async def call_endpoint(
        self,
        endpoint_key: str,
        params: dict[str, Any] | None = None,
    ) -> WebPostoResponse:
        path = ENDPOINTS.get(endpoint_key)
        if not path:
            return WebPostoResponse.fail(
                WebPostoError(endpoint=endpoint_key, status=400, type="INVALID_ENDPOINT", message="Endpoint nao mapeado")
            )

        permissions = await self.discover_permissions()
        if not permissions.get(endpoint_key, False):
            return WebPostoResponse.fail(
                WebPostoError(endpoint=path, status=401, type="AUTHORIZATION_ERROR", message="Endpoint sem permissao")
            )

        if self.breaker.is_blocked(endpoint_key):
            metrics_collector.record(path, 503, 0.0, circuit_open=True)
            log_structured(
                self.logger,
                {
                    "system": "webposto",
                    "endpoint": path,
                    "status": 503,
                    "latency_ms": 0,
                    "has_data": False,
                    "synthetic": False,
                    "circuit_open": True,
                },
            )
            return WebPostoResponse.fail(
                WebPostoError(endpoint=path, status=503, type="CIRCUIT_OPEN", message="Endpoint bloqueado temporariamente")
            )

        final_params = self._with_key(params)
        timeout = self._endpoint_timeout(endpoint_key)

        async with httpx.AsyncClient(base_url=self.config.webposto_base_url, timeout=timeout) as client:
            async def _do() -> httpx.Response:
                return await client.get(path, params=final_params)

            try:
                started = perf_counter()
                response = await retry_async(_do, attempts=3)
                latency_ms = (perf_counter() - started) * 1000
            except Exception as exc:
                self.breaker.record_failure(endpoint_key)
                metrics_collector.record(path, 500, 0.0)
                return WebPostoResponse.fail(
                    WebPostoError(endpoint=path, status=500, type="NETWORK_ERROR", message=str(exc)[:220])
                )

        status = response.status_code
        metrics_collector.record(path, status, latency_ms)
        if status == 200:
            self.breaker.record_success(endpoint_key)
            payload = response.json()
            rows = self._extract_rows(payload)
            log_structured(
                self.logger,
                {
                    "system": "webposto",
                    "endpoint": path,
                    "status": status,
                    "latency_ms": round(latency_ms, 2),
                    "has_data": bool(rows),
                    "synthetic": False,
                },
            )
            return WebPostoResponse.ok(payload)

        if status == 401:
            permissions[endpoint_key] = False
            set_permissions(permissions)
            self.breaker.block_endpoint(endpoint_key, duration_seconds=self.config.circuit_block_seconds)
            return WebPostoResponse.fail(
                WebPostoError(endpoint=path, status=401, type="AUTHORIZATION_ERROR", message="Sem permissao para endpoint")
            )

        self.breaker.record_failure(endpoint_key)
        log_structured(
            self.logger,
            {
                "system": "webposto",
                "endpoint": path,
                "status": status,
                "latency_ms": round(latency_ms, 2),
                "has_data": False,
                "synthetic": False,
            },
        )
        return WebPostoResponse.fail(
            WebPostoError(endpoint=path, status=status, type="UPSTREAM_ERROR", message=response.text[:220])
        )
