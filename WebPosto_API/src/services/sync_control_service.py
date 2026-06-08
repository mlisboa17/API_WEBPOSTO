from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from src.core.logger import get_logger

_logger = get_logger(__name__)

_SYNC_CONTROL: dict[str, dict[str, Any]] = {}
_INTEGRATION_LOG: list[dict[str, Any]] = []
_MAX_LOG_ENTRIES = 1000

SUPPORTED_ENDPOINTS = [
    "empresas",
    "despesas_financeiro_rede",
    "venda",
    "venda_item_rede",
    "venda_forma_pagamento_rede",
    "financeiro",
    "conta",
    "produto_estoque",
    "abastecimento",
    "titulo_receber",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SyncControlService:
    """
    Controla o estado de sincronizacao por endpoint.
    Guarda: ultimo_codigo, ultima_execucao, status e erros recentes.
    """

    def get_all(self) -> list[dict[str, Any]]:
        return [
            {"endpoint": k, **v}
            for k, v in _SYNC_CONTROL.items()
        ]

    def get(self, endpoint: str) -> dict[str, Any] | None:
        return _SYNC_CONTROL.get(endpoint)

    def update(
        self,
        endpoint: str,
        *,
        ultimo_codigo: Any = None,
        status: str = "ok",
        total_registros: int = 0,
        erro: str | None = None,
    ) -> None:
        _SYNC_CONTROL[endpoint] = {
            "ultimoCodigo": str(ultimo_codigo) if ultimo_codigo is not None else None,
            "ultimaExecucao": _now_iso(),
            "status": status,
            "totalRegistros": total_registros,
            "erro": erro,
        }

    def reset(self, endpoint: str) -> None:
        _SYNC_CONTROL.pop(endpoint, None)


class IntegrationLogService:
    """
    Log de todas as chamadas de integracao.
    Mantido em memória com limite configuravel.
    Pode ser substituido por banco real sem alterar interface.
    """

    def add(
        self,
        *,
        endpoint: str,
        status_http: int,
        latency_ms: float,
        total_registros: int = 0,
        ultimo_codigo: Any = None,
        erro: str | None = None,
        filtros: dict[str, Any] | None = None,
        empresa_codigo: int | None = None,
    ) -> None:
        entry: dict[str, Any] = {
            "id": len(_INTEGRATION_LOG) + 1,
            "endpoint": endpoint,
            "statusHttp": status_http,
            "latencyMs": round(latency_ms, 2),
            "totalRegistros": total_registros,
            "ultimoCodigo": str(ultimo_codigo) if ultimo_codigo is not None else None,
            "erro": erro,
            "filtros": filtros or {},
            "empresaCodigo": empresa_codigo,
            "dataHora": _now_iso(),
            "origemSistema": "webpostos",
        }
        _INTEGRATION_LOG.append(entry)
        if len(_INTEGRATION_LOG) > _MAX_LOG_ENTRIES:
            _INTEGRATION_LOG.pop(0)

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        return list(reversed(_INTEGRATION_LOG[-limit:]))

    def list_errors(self, limit: int = 50) -> list[dict[str, Any]]:
        errors = [e for e in _INTEGRATION_LOG if e.get("erro") is not None]
        return list(reversed(errors[-limit:]))


sync_control_service = SyncControlService()
integration_log_service = IntegrationLogService()
