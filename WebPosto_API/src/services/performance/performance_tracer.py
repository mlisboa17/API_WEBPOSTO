"""Instrumentação de performance — PERFORMANCE-01 (measure first)."""

from __future__ import annotations

import contextvars
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

_active_tracer: contextvars.ContextVar["PerformanceTracer | None"] = contextvars.ContextVar(
    "performance_tracer",
    default=None,
)


@dataclass
class PerformanceEvent:
    operation: str
    started_at: str
    finished_at: str
    duration_ms: int
    tenant_id: str | None = None
    empresa_codigo: str | None = None
    endpoint: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    cache_hit: bool = False
    cache_miss: bool = False
    requests_count: int = 0
    status: str = "ok"
    metadata: dict[str, Any] = field(default_factory=dict)


class PerformanceTracer:
    def __init__(self, analysis_id: str) -> None:
        self.analysis_id = analysis_id
        self.events: list[PerformanceEvent] = []
        self._webposto_requests: list[dict[str, Any]] = []
        self._stack: list[tuple[str, float]] = []

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def record(
        self,
        operation: str,
        duration_ms: int,
        *,
        tenant_id: str | None = None,
        empresa_codigo: str | None = None,
        endpoint: str | None = None,
        period_start: str | None = None,
        period_end: str | None = None,
        cache_hit: bool = False,
        cache_miss: bool = False,
        requests_count: int = 0,
        status: str = "ok",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        finished = self._now_iso()
        self.events.append(
            PerformanceEvent(
                operation=operation,
                started_at=finished,
                finished_at=finished,
                duration_ms=duration_ms,
                tenant_id=tenant_id,
                empresa_codigo=empresa_codigo,
                endpoint=endpoint,
                period_start=period_start,
                period_end=period_end,
                cache_hit=cache_hit,
                cache_miss=cache_miss,
                requests_count=requests_count,
                status=status,
                metadata=metadata or {},
            )
        )

    class _Span:
        def __init__(
            self,
            tracer: PerformanceTracer,
            operation: str,
            *,
            tenant_id: str | None = None,
            empresa_codigo: str | None = None,
            endpoint: str | None = None,
            period_start: str | None = None,
            period_end: str | None = None,
            metadata: dict[str, Any] | None = None,
        ) -> None:
            self._tracer = tracer
            self._operation = operation
            self._tenant_id = tenant_id
            self._empresa_codigo = empresa_codigo
            self._endpoint = endpoint
            self._period_start = period_start
            self._period_end = period_end
            self._metadata = metadata or {}
            self._started_at = tracer._now_iso()
            self._t0 = perf_counter()
            self._status = "ok"

        def __enter__(self) -> PerformanceTracer._Span:
            self._tracer._stack.append((self._operation, self._t0))
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            if self._tracer._stack:
                self._tracer._stack.pop()
            if exc is not None:
                self._status = "error"
                self._metadata["error"] = str(exc)[:220]
            duration_ms = int((perf_counter() - self._t0) * 1000)
            self._tracer.events.append(
                PerformanceEvent(
                    operation=self._operation,
                    started_at=self._started_at,
                    finished_at=self._tracer._now_iso(),
                    duration_ms=duration_ms,
                    tenant_id=self._tenant_id,
                    empresa_codigo=self._empresa_codigo,
                    endpoint=self._endpoint,
                    period_start=self._period_start,
                    period_end=self._period_end,
                    status=self._status,
                    metadata=self._metadata,
                )
            )

        async def __aenter__(self) -> PerformanceTracer._Span:
            return self.__enter__()

        async def __aexit__(self, exc_type, exc, tb) -> None:
            self.__exit__(exc_type, exc, tb)

    def span(
        self,
        operation: str,
        *,
        tenant_id: str | None = None,
        empresa_codigo: str | None = None,
        endpoint: str | None = None,
        period_start: str | None = None,
        period_end: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> _Span:
        return self._Span(
            self,
            operation,
            tenant_id=tenant_id,
            empresa_codigo=empresa_codigo,
            endpoint=endpoint,
            period_start=period_start,
            period_end=period_end,
            metadata=metadata,
        )

    def record_webposto_request(
        self,
        *,
        tenant_id: str | None,
        empresa_codigo: str | None,
        endpoint: str,
        period_start: str | None,
        period_end: str | None,
        duration_ms: int,
        status: int,
        credential_fingerprint: str | None = None,
        cache_hit: bool = False,
    ) -> None:
        request_number = len(self._webposto_requests) + 1
        self._webposto_requests.append(
            {
                "analysis_id": self.analysis_id,
                "request_number": request_number,
                "tenant_id": tenant_id,
                "empresa_codigo": empresa_codigo,
                "endpoint": endpoint,
                "period_start": period_start,
                "period_end": period_end,
                "duration_ms": duration_ms,
                "status": status,
                "credential_fingerprint": credential_fingerprint,
                "cache_hit": cache_hit,
            }
        )

    def summarize(self) -> dict[str, Any]:
        by_operation: dict[str, int] = {}
        for event in self.events:
            by_operation[event.operation] = by_operation.get(event.operation, 0) + event.duration_ms

        ranked = sorted(by_operation.items(), key=lambda item: item[1], reverse=True)

        duplicate_groups: dict[str, list[dict[str, Any]]] = {}
        for req in self._webposto_requests:
            key = "|".join(
                str(v or "")
                for v in (
                    req.get("endpoint"),
                    req.get("tenant_id"),
                    req.get("empresa_codigo"),
                    req.get("period_start"),
                    req.get("period_end"),
                    req.get("credential_fingerprint"),
                )
            )
            duplicate_groups.setdefault(key, []).append(req)

        duplicates = [
            {
                "key": key,
                "count": len(items),
                "endpoint": items[0].get("endpoint"),
                "tenant_id": items[0].get("tenant_id"),
                "period_start": items[0].get("period_start"),
                "period_end": items[0].get("period_end"),
            }
            for key, items in duplicate_groups.items()
            if len(items) > 1
        ]

        return {
            "analysis_id": self.analysis_id,
            "total_duration_ms": sum(event.duration_ms for event in self.events),
            "operation_ranking_ms": ranked,
            "events": [event.__dict__ for event in self.events],
            "webposto_requests": self._webposto_requests,
            "webposto_request_count": len(self._webposto_requests),
            "duplicate_request_groups": duplicates,
            "duplicate_request_count": sum(max(0, g["count"] - 1) for g in duplicates),
        }


def get_active_tracer() -> PerformanceTracer | None:
    return _active_tracer.get()


def set_active_tracer(tracer: PerformanceTracer | None) -> contextvars.Token:
    return _active_tracer.set(tracer)
