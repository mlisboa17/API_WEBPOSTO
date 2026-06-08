from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass
class EndpointMetrics:
    calls: int = 0
    success: int = 0
    errors: int = 0
    unauthorized_401: int = 0
    total_latency_ms: float = 0.0
    circuit_open_count: int = 0


class MetricsCollector:
    def __init__(self) -> None:
        self._lock = Lock()
        self._per_endpoint: dict[str, EndpointMetrics] = {}

    def _get(self, endpoint: str) -> EndpointMetrics:
        metric = self._per_endpoint.get(endpoint)
        if metric is None:
            metric = EndpointMetrics()
            self._per_endpoint[endpoint] = metric
        return metric

    def record(self, endpoint: str, status: int, latency_ms: float, circuit_open: bool = False) -> None:
        with self._lock:
            metric = self._get(endpoint)
            metric.calls += 1
            metric.total_latency_ms += max(float(latency_ms), 0.0)
            if 200 <= int(status) < 300:
                metric.success += 1
            else:
                metric.errors += 1
            if int(status) == 401:
                metric.unauthorized_401 += 1
            if circuit_open:
                metric.circuit_open_count += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            data: dict[str, Any] = {}
            for endpoint, metric in self._per_endpoint.items():
                calls = metric.calls
                avg_latency = (metric.total_latency_ms / calls) if calls else 0.0
                rate_401 = (metric.unauthorized_401 / calls) if calls else 0.0
                data[endpoint] = {
                    "calls": calls,
                    "success": metric.success,
                    "errors": metric.errors,
                    "avg_latency_ms": round(avg_latency, 2),
                    "rate_401": round(rate_401, 4),
                    "circuit_breaker_activated": metric.circuit_open_count,
                }
            return data


metrics_collector = MetricsCollector()


def get_metrics_snapshot() -> dict[str, Any]:
    return metrics_collector.snapshot()
