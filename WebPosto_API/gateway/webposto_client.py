"""Onda 2 — Gateway unificado WebPosto (facade incremental, snapshot-first)."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any, AsyncIterator

import httpx

from gateway.webposto_errors import (
    WebPostoAuthError,
    WebPostoDataError,
    WebPostoGatewayError,
    WebPostoRateLimitError,
    WebPostoServerError,
    WebPostoSnapshotGuardError,
)
from gateway.webposto_types import PaginationState, WebPostoLogEvent, WebPostoResponse

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"

ENDPOINTS: dict[str, str] = {
    "venda": "/INTEGRACAO/VENDA",
    "venda_item": "/INTEGRACAO/VENDA_ITEM",
    "nfce": "/INTEGRACAO/NFCE",
    "abastecimento": "/INTEGRACAO/ABASTECIMENTO",
    "lmc_rede": "/INTEGRACAO/CONSULTAR_LMC_REDE",
    "produto": "/INTEGRACAO/PRODUTO",
    "produto_empresa": "/INTEGRACAO/PRODUTO_EMPRESA",
    "conta": "/INTEGRACAO/CONTA",
    "plano_conta_gerencial": "/INTEGRACAO/PLANO_CONTA_GERENCIAL",
}

TOKEN_ENV_KEYS: tuple[str, ...] = (
    "WEBPOSTO_API_KEY",
    "WEBPOSTO_API_KEY_POSTO_VIP_RIO_DOCE",
    "WEBPOSTO_API_KEY_POSTO_CASA_CAIADA",
)

RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
MAX_BACKOFF_S = 8.0


def _load_dotenv() -> None:
    if not ENV_FILE.is_file():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


def token_fingerprint(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:12]


def resolve_api_key(explicit: str | None = None) -> str:
    if explicit:
        return explicit.strip()
    _load_dotenv()
    for key in TOKEN_ENV_KEYS:
        value = os.environ.get(key, "").strip()
        if value:
            return value
    raise WebPostoDataError(
        "Nenhuma chave WebPosto configurada (WEBPOSTO_API_KEY ou variantes por filial).",
        endpoint="config",
        status=400,
    )


def resolve_base_url(explicit: str | None = None) -> str:
    if explicit:
        return explicit.rstrip("/")
    _load_dotenv()
    return os.environ.get("WEBPOSTO_BASE_URL", "https://web.qualityautomacao.com.br").rstrip("/")


def extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("resultados", "data"):
            inner = payload.get(key)
            if isinstance(inner, list):
                return [row for row in inner if isinstance(row, dict)]
    return []


def build_params(
    *,
    api_key: str,
    empresa_codigo: str | None,
    data_inicial: str | date | None = None,
    data_final: str | date | None = None,
    extra_params: dict[str, object] | None = None,
) -> dict[str, object]:
    params: dict[str, object] = {"CHAVE": api_key}
    if empresa_codigo is not None:
        params["empresaCodigo"] = str(empresa_codigo)
    if data_inicial is not None:
        params["dataInicial"] = data_inicial.isoformat() if isinstance(data_inicial, date) else str(data_inicial)
    if data_final is not None:
        params["dataFinal"] = data_final.isoformat() if isinstance(data_final, date) else str(data_final)
    if extra_params:
        for key, value in extra_params.items():
            if value is not None:
                params[key] = value
    return params


class WebPostoClient:
    """Facade unificada — token ≠ filial; empresaCodigo segrega escopo lógico."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        *,
        allow_live: bool = False,
        max_retries: int = 3,
        default_timeout_s: float = 30.0,
    ) -> None:
        self.api_key = resolve_api_key(api_key)
        self.base_url = resolve_base_url(base_url)
        self.allow_live = allow_live
        self.max_retries = max(1, max_retries)
        self.default_timeout_s = default_timeout_s
        self._fingerprint = token_fingerprint(self.api_key)

    @property
    def token_fingerprint(self) -> str:
        return self._fingerprint

    def _log_event(self, event: WebPostoLogEvent) -> None:
        logger.info(json.dumps(event.to_dict(), ensure_ascii=False))

    def _ensure_live_allowed(self, endpoint: str) -> None:
        if not self.allow_live:
            raise WebPostoSnapshotGuardError(
                "Chamada WebPosto live bloqueada (allow_live=False). "
                "Use snapshots homologados ou ative allow_live apenas em scripts de auditoria.",
                endpoint=endpoint,
                status=403,
            )

    def _raise_for_status(self, endpoint: str, status: int, body: str, empresa_codigo: str | None) -> None:
        message = body[:220] if body else f"HTTP {status}"
        if status in (401, 403):
            raise WebPostoAuthError(message, endpoint=endpoint, status=status, empresa_codigo=empresa_codigo)
        if status == 429:
            raise WebPostoRateLimitError(message, endpoint=endpoint, status=status, empresa_codigo=empresa_codigo)
        if status >= 500:
            raise WebPostoServerError(message, endpoint=endpoint, status=status, empresa_codigo=empresa_codigo)
        if status >= 400:
            raise WebPostoDataError(message, endpoint=endpoint, status=status, empresa_codigo=empresa_codigo)

    async def request(
        self,
        endpoint: str,
        params: dict[str, object] | None = None,
        empresa_codigo: str | None = None,
        timeout_s: float | None = None,
    ) -> WebPostoResponse:
        path = endpoint if endpoint.startswith("/") else ENDPOINTS.get(endpoint, endpoint)
        if not path.startswith("/INTEGRACAO/"):
            raise WebPostoDataError(f"Endpoint inválido: {endpoint}", endpoint=str(endpoint), status=400)

        self._ensure_live_allowed(path)
        final_params = build_params(
            api_key=self.api_key,
            empresa_codigo=empresa_codigo,
            extra_params=params,
        )
        timeout = httpx.Timeout(timeout_s or self.default_timeout_s, connect=min(5.0, timeout_s or self.default_timeout_s))
        started = perf_counter()
        last_error = "unknown"

        async with httpx.AsyncClient(base_url=self.base_url, timeout=timeout) as client:
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = await client.get(path, params=final_params)
                except httpx.TimeoutException as exc:
                    last_error = f"timeout: {exc}"
                    if attempt >= self.max_retries:
                        latency_ms = (perf_counter() - started) * 1000
                        self._log_event(
                            WebPostoLogEvent(
                                endpoint=path,
                                status=408,
                                latency_ms=latency_ms,
                                has_data=False,
                                empresa_codigo=empresa_codigo,
                                token_fingerprint=self._fingerprint,
                                extra={"error": last_error},
                            )
                        )
                        raise WebPostoServerError(last_error, endpoint=path, status=408, empresa_codigo=empresa_codigo) from exc
                    await asyncio.sleep(min(2 ** (attempt - 1), MAX_BACKOFF_S))
                    continue
                except httpx.HTTPError as exc:
                    last_error = str(exc)[:220]
                    if attempt >= self.max_retries:
                        raise WebPostoServerError(last_error, endpoint=path, status=500, empresa_codigo=empresa_codigo) from exc
                    await asyncio.sleep(min(2 ** (attempt - 1), MAX_BACKOFF_S))
                    continue

                latency_ms = (perf_counter() - started) * 1000
                if response.status_code in RETRYABLE_STATUS and attempt < self.max_retries:
                    await asyncio.sleep(min(2 ** (attempt - 1), MAX_BACKOFF_S))
                    continue

                if response.status_code != 200:
                    self._log_event(
                        WebPostoLogEvent(
                            endpoint=path,
                            status=response.status_code,
                            latency_ms=latency_ms,
                            has_data=False,
                            empresa_codigo=empresa_codigo,
                            token_fingerprint=self._fingerprint,
                        )
                    )
                    self._raise_for_status(path, response.status_code, response.text, empresa_codigo)

                payload = response.json()
                rows = extract_rows(payload)
                self._log_event(
                    WebPostoLogEvent(
                        endpoint=path,
                        status=200,
                        latency_ms=latency_ms,
                        has_data=bool(rows),
                        empresa_codigo=empresa_codigo,
                        token_fingerprint=self._fingerprint,
                    )
                )
                return WebPostoResponse.success(
                    endpoint=path,
                    status=200,
                    data=payload,
                    rows=rows,
                    latency_ms=latency_ms,
                    empresa_codigo=empresa_codigo,
                    token_fingerprint=self._fingerprint,
                )

        raise WebPostoServerError(last_error, endpoint=path, status=500, empresa_codigo=empresa_codigo)

    async def _dated_request(
        self,
        endpoint_key: str,
        *,
        empresa_codigo: str | None,
        data_inicial: str | date | None,
        data_final: str | date | None,
        extra_params: dict[str, object] | None = None,
        timeout_s: float | None = None,
    ) -> WebPostoResponse:
        params = build_params(
            api_key=self.api_key,
            empresa_codigo=empresa_codigo,
            data_inicial=data_inicial,
            data_final=data_final,
            extra_params=extra_params,
        )
        params.pop("CHAVE", None)
        return await self.request(
            ENDPOINTS[endpoint_key],
            params=params,
            empresa_codigo=empresa_codigo,
            timeout_s=timeout_s,
        )

    async def get_venda(
        self,
        *,
        empresa_codigo: str | None = None,
        data_inicial: str | date | None = None,
        data_final: str | date | None = None,
        extra_params: dict[str, object] | None = None,
        timeout_s: float | None = None,
    ) -> WebPostoResponse:
        return await self._dated_request(
            "venda",
            empresa_codigo=empresa_codigo,
            data_inicial=data_inicial,
            data_final=data_final,
            extra_params=extra_params,
            timeout_s=timeout_s,
        )

    async def get_venda_item(
        self,
        *,
        empresa_codigo: str | None = None,
        data_inicial: str | date | None = None,
        data_final: str | date | None = None,
        extra_params: dict[str, object] | None = None,
        timeout_s: float | None = None,
    ) -> WebPostoResponse:
        return await self._dated_request(
            "venda_item",
            empresa_codigo=empresa_codigo,
            data_inicial=data_inicial,
            data_final=data_final,
            extra_params=extra_params,
            timeout_s=timeout_s,
        )

    async def get_nfce(
        self,
        *,
        empresa_codigo: str | None = None,
        data_inicial: str | date | None = None,
        data_final: str | date | None = None,
        extra_params: dict[str, object] | None = None,
        timeout_s: float | None = None,
    ) -> WebPostoResponse:
        return await self._dated_request(
            "nfce",
            empresa_codigo=empresa_codigo,
            data_inicial=data_inicial,
            data_final=data_final,
            extra_params=extra_params,
            timeout_s=timeout_s,
        )

    async def get_abastecimento(
        self,
        *,
        empresa_codigo: str | None = None,
        data_inicial: str | date | None = None,
        data_final: str | date | None = None,
        extra_params: dict[str, object] | None = None,
        timeout_s: float | None = None,
    ) -> WebPostoResponse:
        return await self._dated_request(
            "abastecimento",
            empresa_codigo=empresa_codigo,
            data_inicial=data_inicial,
            data_final=data_final,
            extra_params=extra_params,
            timeout_s=timeout_s,
        )

    async def get_lmc_rede(
        self,
        *,
        empresa_codigo: str | None = None,
        data_inicial: str | date | None = None,
        data_final: str | date | None = None,
        extra_params: dict[str, object] | None = None,
        timeout_s: float | None = None,
    ) -> WebPostoResponse:
        return await self._dated_request(
            "lmc_rede",
            empresa_codigo=empresa_codigo,
            data_inicial=data_inicial,
            data_final=data_final,
            extra_params=extra_params,
            timeout_s=timeout_s,
        )

    async def get_produto(
        self,
        *,
        empresa_codigo: str | None = None,
        data_inicial: str | date | None = None,
        data_final: str | date | None = None,
        extra_params: dict[str, object] | None = None,
        timeout_s: float | None = None,
    ) -> WebPostoResponse:
        return await self._dated_request(
            "produto",
            empresa_codigo=empresa_codigo,
            data_inicial=data_inicial,
            data_final=data_final,
            extra_params=extra_params,
            timeout_s=timeout_s,
        )

    async def get_produto_empresa(
        self,
        *,
        empresa_codigo: str | None = None,
        data_inicial: str | date | None = None,
        data_final: str | date | None = None,
        extra_params: dict[str, object] | None = None,
        timeout_s: float | None = None,
    ) -> WebPostoResponse:
        return await self._dated_request(
            "produto_empresa",
            empresa_codigo=empresa_codigo,
            data_inicial=data_inicial,
            data_final=data_final,
            extra_params=extra_params,
            timeout_s=timeout_s,
        )

    async def get_conta(
        self,
        *,
        empresa_codigo: str | None = None,
        data_inicial: str | date | None = None,
        data_final: str | date | None = None,
        extra_params: dict[str, object] | None = None,
        timeout_s: float | None = None,
    ) -> WebPostoResponse:
        return await self._dated_request(
            "conta",
            empresa_codigo=empresa_codigo,
            data_inicial=data_inicial,
            data_final=data_final,
            extra_params=extra_params,
            timeout_s=timeout_s,
        )

    async def get_plano_conta_gerencial(
        self,
        *,
        empresa_codigo: str | None = None,
        data_inicial: str | date | None = None,
        data_final: str | date | None = None,
        extra_params: dict[str, object] | None = None,
        timeout_s: float | None = None,
    ) -> WebPostoResponse:
        return await self._dated_request(
            "plano_conta_gerencial",
            empresa_codigo=empresa_codigo,
            data_inicial=data_inicial,
            data_final=data_final,
            extra_params=extra_params,
            timeout_s=timeout_s,
        )

    async def paginate(
        self,
        endpoint_key: str,
        *,
        empresa_codigo: str | None = None,
        data_inicial: str | date | None = None,
        data_final: str | date | None = None,
        state: PaginationState | None = None,
        extra_params: dict[str, object] | None = None,
    ) -> AsyncIterator[WebPostoResponse]:
        pagination = state or PaginationState()
        ultimo: str | int | None = pagination.ultimo_codigo

        for page in range(pagination.max_pages):
            page_params = dict(extra_params or {})
            if endpoint_key == "abastecimento":
                if ultimo is not None:
                    page_params["ultimoCodigo"] = ultimo
                page_params.setdefault("tamanhoPagina", pagination.tamanho_pagina)
            else:
                page_params["pagina"] = page
                page_params.setdefault("tamanhoPagina", pagination.tamanho_pagina)

            response = await self._dated_request(
                endpoint_key,
                empresa_codigo=empresa_codigo,
                data_inicial=data_inicial,
                data_final=data_final,
                extra_params=page_params,
            )
            yield response
            if not response.rows:
                break
            if endpoint_key == "abastecimento":
                payload = response.data if isinstance(response.data, dict) else {}
                novo = payload.get("ultimoCodigo")
                if novo in (None, "") or novo == ultimo:
                    break
                ultimo = novo
            elif len(response.rows) < pagination.tamanho_pagina:
                break
