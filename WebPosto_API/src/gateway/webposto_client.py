from __future__ import annotations

import asyncio
import json
from datetime import date
from hashlib import sha256
from time import perf_counter
from typing import Any

import httpx

from src.core.config import CoreConfig, load_core_config
from src.core.logger import get_logger, log_structured
from src.gateway.webposto_endpoint_contracts import endpoint_requires_dates
from src.metrics.collector import metrics_collector
from src.models.error_model import WebPostoError
from src.models.response_model import WebPostoResponse
from src.services.date_range_resolver import DateRangeResolver
from src.utils.circuit_breaker import SimpleCircuitBreaker
from src.utils.permission_cache import get_permissions, is_cache_fresh, set_permissions
from src.services.performance.performance_metrics import performance_metrics
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
    "plano_de_contas": "/INTEGRACAO/PLANO_DE_CONTAS",
    "venda": "/INTEGRACAO/VENDA",
    "venda_item": "/INTEGRACAO/VENDA_ITEM",
    "venda_item_rede": "/INTEGRACAO/CONSULTAR_VENDA_ITEM_REDE",
    "venda_forma_pagamento": "/INTEGRACAO/VENDA_FORMA_PAGAMENTO",
    "venda_forma_pagamento_rede": "/INTEGRACAO/CONSULTAR_VENDA_FORMA_PAGAMENTO_REDE",
    "administradora_rede": "/INTEGRACAO/CONSULTAR_ADMINISTRADORA_REDE",
    "cartao_rede": "/INTEGRACAO/CONSULTAR_CARTAO_REDE",
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

# A ordem acompanha OFFICIAL_WEBPOSTO_TOKEN_ENV_KEYS em src.core.config.
OFFICIAL_COMPANY_TOKEN_INDEX = {11495: 0, 5555: 1, 74014: 2}


class WebPostoClient:
    _permissions_lock: asyncio.Lock | None = None

    def __init__(self, config: CoreConfig | None = None) -> None:
        self.config = config or load_core_config()
        self.logger = get_logger(__name__)
        self.breaker = SimpleCircuitBreaker(
            failure_threshold=self.config.circuit_fail_threshold,
            block_seconds=self.config.circuit_block_seconds,
        )

    @classmethod
    def for_api_key(cls, api_key: str, config: CoreConfig | None = None) -> WebPostoClient:
        """Cliente isolado para uma única credencial — evita mistura entre tenants."""
        base = config or load_core_config()
        isolated = CoreConfig(
            webposto_base_url=base.webposto_base_url,
            webposto_api_key=api_key,
            webposto_api_keys=(api_key,),
            timeout_seconds=base.timeout_seconds,
            permission_ttl_seconds=base.permission_ttl_seconds,
            circuit_fail_threshold=base.circuit_fail_threshold,
            circuit_block_seconds=base.circuit_block_seconds,
        )
        return cls(isolated)

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
        # IMPORTANTE: despesas_financeiro_rede EXIGE dataInicial/dataFinal (retorna 400 sem eles)
        if endpoint_key in {"analise_vendas_combustivel", "empresas"}:
            return None
        return self._date_params()

    @property
    def _api_keys(self) -> tuple[str, ...]:
        return self.config.webposto_api_keys or (
            (self.config.webposto_api_key,) if self.config.webposto_api_key else ()
        )

    def _api_keys_for_params(self, params: dict[str, Any] | None) -> tuple[str, ...]:
        keys = self._api_keys
        if not params or params.get("empresaCodigo") in (None, ""):
            return keys
        try:
            index = OFFICIAL_COMPANY_TOKEN_INDEX[int(params["empresaCodigo"])]
        except (KeyError, TypeError, ValueError):
            return keys
        # Configurações isoladas já contêm somente a credencial correta.
        if len(keys) == 1:
            return keys
        return (keys[index],) if index < len(keys) else keys

    @staticmethod
    def _fingerprint(api_key: str) -> str:
        return sha256(api_key.encode("utf-8")).hexdigest()[:12]

    def _with_key(self, params: dict[str, Any] | None, api_key: str) -> dict[str, Any]:
        final = {"CHAVE": api_key}
        if params:
            final.update({k: v for k, v in params.items() if v is not None})
        return final

    @staticmethod
    def _dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for row in rows:
            marker = json.dumps(row, sort_keys=True, ensure_ascii=False, default=str)
            if marker in seen:
                continue
            seen.add(marker)
            unique.append(row)
        return unique

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
            "administradora_rede",
            "cartao_rede",
            "nfce",
            "produto_estoque",
            "estoque_periodo",
            "lmc_rede",
            "funcionario",
        }:
            base = max(20.0, base)
        return httpx.Timeout(base, connect=min(5.0, base))

    async def discover_permissions(self, force: bool = False) -> dict[str, bool]:
        fingerprint = (
            self._fingerprint(self._api_keys[0])
            if len(self._api_keys) == 1
            else "_merged"
        )
        if not force and is_cache_fresh(self.config.permission_ttl_seconds, fingerprint):
            cached = get_permissions(fingerprint)
            if all(key in cached for key in ENDPOINTS):
                performance_metrics.record_permission_cache_hit()
                return cached

        if WebPostoClient._permissions_lock is None:
            WebPostoClient._permissions_lock = asyncio.Lock()

        async with WebPostoClient._permissions_lock:
            if not force and is_cache_fresh(self.config.permission_ttl_seconds, fingerprint):
                cached = get_permissions(fingerprint)
                if all(key in cached for key in ENDPOINTS):
                    performance_metrics.record_permission_cache_hit()
                    return cached

            probe_started = perf_counter()
            permissions: dict[str, bool] = {}

            async def _probe_permission(client: httpx.AsyncClient, key: str, path: str, api_key: str):
                params = self._with_key(self._discovery_params(key), api_key)
                started = perf_counter()
                try:
                    response = await client.get(path, params=params)
                    latency_ms = (perf_counter() - started) * 1000
                    # Alguns endpoints validam payload e retornam 400/422 mesmo com chave autorizada.
                    allowed = response.status_code not in {401, 403}
                    permissions[key] = permissions.get(key, False) or allowed
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
                            "token": self._fingerprint(api_key),
                        },
                    )
                except Exception as exc:
                    permissions.setdefault(key, False)
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
                            "token": self._fingerprint(api_key),
                            "error": str(exc)[:220],
                        },
                    )

            if not self._api_keys:
                return {key: False for key in ENDPOINTS}

            async with httpx.AsyncClient(
                base_url=self.config.webposto_base_url,
                timeout=httpx.Timeout(max(20.0, self.config.timeout_seconds), connect=min(5.0, max(20.0, self.config.timeout_seconds))),
            ) as client:
                tasks = [
                    _probe_permission(client, key, path, api_key)
                    for api_key in self._api_keys
                    for key, path in ENDPOINTS.items()
                ]
                await asyncio.gather(*tasks)

            probe_ms = int((perf_counter() - probe_started) * 1000)
            http_count = len(self._api_keys) * len(ENDPOINTS)
            performance_metrics.record_permission_cache_miss(
                duration_ms=probe_ms,
                http_count=http_count,
                endpoints=len(ENDPOINTS),
            )
            set_permissions(permissions, fingerprint)
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

        selected_keys = self._api_keys_for_params(params)
        targeted_official_call = (
            bool(params and params.get("empresaCodigo") not in (None, ""))
            and len(selected_keys) == 1
        ) or endpoint_key == "despesas_financeiro_rede"
        permissions: dict[str, bool] = {}
        if not targeted_official_call:
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

        # Aplicar datas obrigatórias automaticamente
        if endpoint_requires_dates(endpoint_key):
            params = DateRangeResolver.ensure_date_params(params)
            log_structured(
                self.logger,
                {
                    "system": "webposto",
                    "endpoint": path,
                    "event": "date_params_ensured",
                    "dataInicial": params.get("dataInicial"),
                    "dataFinal": params.get("dataFinal"),
                    "synthetic": False,
                },
            )

        timeout = self._endpoint_timeout(endpoint_key)

        async def _call_with_key(client: httpx.AsyncClient, api_key: str) -> tuple[str, httpx.Response | None, float, Exception | None]:
            final_params = self._with_key(params, api_key)
            async def _do() -> httpx.Response:
                return await client.get(path, params=final_params)

            try:
                started = perf_counter()
                response = await retry_async(_do, attempts=3)
                latency_ms = (perf_counter() - started) * 1000
                return api_key, response, latency_ms, None
            except Exception as exc:
                return api_key, None, 0.0, exc

        if not selected_keys:
            return WebPostoResponse.fail(
                WebPostoError(
                    endpoint=path,
                    status=401,
                    type="AUTHORIZATION_ERROR",
                    message="Nenhum token oficial WebPosto configurado",
                )
            )

        async with httpx.AsyncClient(base_url=self.config.webposto_base_url, timeout=timeout) as client:
            results = await asyncio.gather(*[_call_with_key(client, api_key) for api_key in selected_keys])

        ok_payloads: list[Any] = []
        ok_rows: list[dict[str, Any]] = []
        auth_errors = 0
        last_error: WebPostoError | None = None

        for api_key, response, latency_ms, exc in results:
            if exc is not None:
                is_timeout = "timeout" in str(exc).casefold() or isinstance(exc, httpx.TimeoutException)
                performance_metrics.record_webposto_request(endpoint_key, 500, is_timeout=is_timeout)
                metrics_collector.record(path, 500, 0.0)
                last_error = WebPostoError(endpoint=path, status=500, type="NETWORK_ERROR", message=str(exc)[:220])
                log_structured(
                    self.logger,
                    {
                        "system": "webposto",
                        "endpoint": path,
                        "status": 500,
                        "latency_ms": 0,
                        "has_data": False,
                        "synthetic": False,
                        "token": self._fingerprint(api_key),
                        "error": str(exc)[:220],
                    },
                )
                continue

            if response is None:
                continue

            status = response.status_code
            performance_metrics.record_webposto_request(endpoint_key, status)
            metrics_collector.record(path, status, latency_ms)
            if status == 200:
                payload = response.json()
                rows = self._extract_rows(payload)
                ok_payloads.append(payload)
                ok_rows.extend(rows)
                log_structured(
                    self.logger,
                    {
                        "system": "webposto",
                        "endpoint": path,
                        "status": status,
                        "latency_ms": round(latency_ms, 2),
                        "has_data": bool(rows),
                        "synthetic": False,
                        "token": self._fingerprint(api_key),
                    },
                )
                continue

            if status == 401:
                auth_errors += 1
                log_structured(
                    self.logger,
                    {
                        "system": "webposto",
                        "endpoint": path,
                        "status": status,
                        "latency_ms": round(latency_ms, 2),
                        "has_data": False,
                        "synthetic": False,
                        "token": self._fingerprint(api_key),
                    },
                )
                continue

            last_error = WebPostoError(endpoint=path, status=status, type="UPSTREAM_ERROR", message=response.text[:220])
            log_structured(
                self.logger,
                {
                    "system": "webposto",
                    "endpoint": path,
                    "status": status,
                    "latency_ms": round(latency_ms, 2),
                    "has_data": False,
                    "synthetic": False,
                    "token": self._fingerprint(api_key),
                },
            )

        if ok_payloads:
            self.breaker.record_success(endpoint_key)
            if len(ok_payloads) == 1:
                return WebPostoResponse.ok(ok_payloads[0])
            return WebPostoResponse.ok(
                {
                    "resultados": self._dedupe_rows(ok_rows),
                    "tokensConsultados": len(ok_payloads),
                    "synthetic": False,
                }
            )

        if auth_errors and auth_errors == len(selected_keys):
            permissions[endpoint_key] = False
            fp = (
                self._fingerprint(selected_keys[0])
                if len(selected_keys) == 1
                else "_merged"
            )
            set_permissions(permissions, fp)
            self.breaker.block_endpoint(endpoint_key, duration_seconds=self.config.circuit_block_seconds)
            return WebPostoResponse.fail(
                WebPostoError(endpoint=path, status=401, type="AUTHORIZATION_ERROR", message="Sem permissao para endpoint")
            )

        self.breaker.record_failure(endpoint_key)
        return WebPostoResponse.fail(
            last_error or WebPostoError(endpoint=path, status=500, type="NETWORK_ERROR", message="Falha ao consultar tokens oficiais")
        )

    def get_circuit_status(self, endpoint_keys: set[str] | None = None) -> dict[str, str]:
        from src.gateway.circuit_domains import CIRCUIT_SCOPES

        keys = endpoint_keys or set(ENDPOINTS.keys())
        status = self.breaker.snapshot_status(keys)
        return {
            "endpoints": status,
            "summary": {
                scope: {
                    "OPEN": sum(1 for k in keys_set if status.get(k) == "OPEN"),
                    "HALF_OPEN": sum(1 for k in keys_set if status.get(k) == "HALF_OPEN"),
                    "CLOSED": sum(1 for k in keys_set if status.get(k) == "CLOSED"),
                }
                for scope, keys_set in CIRCUIT_SCOPES.items()
            },
        }

    def reset_circuit(self, scope: str = "global") -> dict[str, Any]:
        from src.gateway.circuit_domains import CIRCUIT_SCOPES

        normalized = (scope or "global").strip().lower()
        keys = CIRCUIT_SCOPES.get(normalized)
        if keys is None:
            return {"scope": normalized, "reset": False, "error": "Escopo invalido"}
        self.breaker.reset_many(set(keys))
        return {"scope": normalized, "reset": True, "endpoints": sorted(keys)}
