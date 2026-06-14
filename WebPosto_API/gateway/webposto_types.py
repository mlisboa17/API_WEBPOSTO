"""Onda 2 — tipos do gateway WebPosto."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class WebPostoResponse:
    ok: bool
    status: int
    endpoint: str
    data: Any
    rows: list[dict[str, Any]]
    latency_ms: float
    empresa_codigo: str | None
    token_fingerprint: str
    synthetic: bool = False
    error: str | None = None

    @classmethod
    def success(
        cls,
        *,
        endpoint: str,
        status: int,
        data: Any,
        rows: list[dict[str, Any]],
        latency_ms: float,
        empresa_codigo: str | None,
        token_fingerprint: str,
    ) -> WebPostoResponse:
        return cls(
            ok=True,
            status=status,
            endpoint=endpoint,
            data=data,
            rows=rows,
            latency_ms=latency_ms,
            empresa_codigo=empresa_codigo,
            token_fingerprint=token_fingerprint,
        )

    @classmethod
    def failure(
        cls,
        *,
        endpoint: str,
        status: int,
        error: str,
        latency_ms: float,
        empresa_codigo: str | None,
        token_fingerprint: str,
        data: Any = None,
    ) -> WebPostoResponse:
        return cls(
            ok=False,
            status=status,
            endpoint=endpoint,
            data=data,
            rows=[],
            latency_ms=latency_ms,
            empresa_codigo=empresa_codigo,
            token_fingerprint=token_fingerprint,
            error=error,
        )


@dataclass(frozen=True)
class PaginationState:
    pagina: int = 0
    tamanho_pagina: int = 200
    ultimo_codigo: str | int | None = None
    max_pages: int = 50


@dataclass
class WebPostoLogEvent:
    system: str = "webposto"
    endpoint: str = ""
    status: int = 0
    latency_ms: float = 0.0
    has_data: bool = False
    synthetic: bool = False
    empresa_codigo: str | None = None
    token_fingerprint: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "system": self.system,
            "endpoint": self.endpoint,
            "status": self.status,
            "latency_ms": round(self.latency_ms, 2),
            "has_data": self.has_data,
            "synthetic": self.synthetic,
            "empresaCodigo": self.empresa_codigo,
            "tokenFingerprint": self.token_fingerprint,
        }
        payload.update(self.extra)
        return payload
