"""Onda 2 — exceções padronizadas do gateway WebPosto."""
from __future__ import annotations


class WebPostoGatewayError(Exception):
    """Erro base do gateway unificado."""

    def __init__(
        self,
        message: str,
        *,
        endpoint: str = "",
        status: int = 0,
        empresa_codigo: str | None = None,
    ) -> None:
        super().__init__(message)
        self.endpoint = endpoint
        self.status = status
        self.empresa_codigo = empresa_codigo


class WebPostoAuthError(WebPostoGatewayError):
    """401/403 — token inválido ou sem permissão."""


class WebPostoRateLimitError(WebPostoGatewayError):
    """429 — rate limit upstream."""


class WebPostoServerError(WebPostoGatewayError):
    """5xx — falha upstream."""


class WebPostoDataError(WebPostoGatewayError):
    """Payload inválido ou resposta inesperada."""


class WebPostoSnapshotGuardError(WebPostoDataError):
    """Chamada live bloqueada — snapshot-first (allow_live=False)."""
