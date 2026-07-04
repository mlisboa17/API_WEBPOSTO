"""Contadores runtime — PERFORMANCE-01."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock


@dataclass
class PerformanceMetrics:
    tenant_registry_cache_hit: int = 0
    tenant_registry_cache_miss: int = 0
    empresas_request_count: int = 0
    permission_cache_hit: int = 0
    permission_cache_miss: int = 0
    permission_probe_duration_ms: int = 0
    permission_endpoints_checked: int = 0
    permission_probe_http_count: int = 0
    fuel_cache_hit_count: int = 0
    fuel_cache_miss_count: int = 0
    expense_cache_hit_count: int = 0
    expense_cache_miss_count: int = 0
    receivable_cache_hit_count: int = 0
    receivable_cache_miss_count: int = 0
    webposto_request_total: int = 0
    webposto_venda_requests: int = 0
    webposto_venda_item_requests: int = 0
    webposto_produto_requests: int = 0
    webposto_429_count: int = 0
    webposto_timeout_count: int = 0
    webposto_5xx_count: int = 0
    duplicate_analysis_count: int = 0
    duplicate_request_count: int = 0
    analysis_trigger_count: int = 0
    snapshot_freshness_last: str | None = None
    snapshot_age_seconds_last: int | None = None
    _lock: Lock = field(default_factory=Lock, repr=False)

    def record_tenant_registry_hit(self) -> None:
        with self._lock:
            self.tenant_registry_cache_hit += 1

    def record_tenant_registry_miss(self) -> None:
        with self._lock:
            self.tenant_registry_cache_miss += 1

    def record_empresas_request(self, count: int = 1) -> None:
        with self._lock:
            self.empresas_request_count += count

    def record_permission_cache_hit(self) -> None:
        with self._lock:
            self.permission_cache_hit += 1

    def record_permission_cache_miss(self, *, duration_ms: int = 0, http_count: int = 0, endpoints: int = 0) -> None:
        with self._lock:
            self.permission_cache_miss += 1
            self.permission_probe_duration_ms += duration_ms
            self.permission_probe_http_count += http_count
            self.permission_endpoints_checked += endpoints

    def record_fuel_cache_hit(self) -> None:
        with self._lock:
            self.fuel_cache_hit_count += 1

    def record_fuel_cache_miss(self) -> None:
        with self._lock:
            self.fuel_cache_miss_count += 1

    def record_expense_cache_hit(self) -> None:
        with self._lock:
            self.expense_cache_hit_count += 1

    def record_expense_cache_miss(self) -> None:
        with self._lock:
            self.expense_cache_miss_count += 1

    def record_receivable_cache_hit(self) -> None:
        with self._lock:
            self.receivable_cache_hit_count += 1

    def record_receivable_cache_miss(self) -> None:
        with self._lock:
            self.receivable_cache_miss_count += 1

    def record_webposto_request(self, endpoint_key: str, status: int, *, is_timeout: bool = False) -> None:
        with self._lock:
            self.webposto_request_total += 1
            if endpoint_key == "venda":
                self.webposto_venda_requests += 1
            elif endpoint_key in {"venda_item", "venda_item_rede"}:
                self.webposto_venda_item_requests += 1
            elif endpoint_key == "produto":
                self.webposto_produto_requests += 1
            if is_timeout:
                self.webposto_timeout_count += 1
            elif int(status) == 429:
                self.webposto_429_count += 1
            elif int(status) >= 500:
                self.webposto_5xx_count += 1

    def reset(self) -> None:
        with self._lock:
            self.tenant_registry_cache_hit = 0
            self.tenant_registry_cache_miss = 0
            self.empresas_request_count = 0
            self.permission_cache_hit = 0
            self.permission_cache_miss = 0
            self.permission_probe_duration_ms = 0
            self.permission_endpoints_checked = 0
            self.permission_probe_http_count = 0
            self.fuel_cache_hit_count = 0
            self.fuel_cache_miss_count = 0
            self.expense_cache_hit_count = 0
            self.expense_cache_miss_count = 0
            self.receivable_cache_hit_count = 0
            self.receivable_cache_miss_count = 0
            self.webposto_request_total = 0
            self.webposto_venda_requests = 0
            self.webposto_venda_item_requests = 0
            self.webposto_produto_requests = 0
            self.webposto_429_count = 0
            self.webposto_timeout_count = 0
            self.webposto_5xx_count = 0

    def record_duplicate_analysis(self) -> None:
        with self._lock:
            self.duplicate_analysis_count += 1

    def record_analysis_trigger(self) -> None:
        with self._lock:
            self.analysis_trigger_count += 1

    def record_snapshot_freshness(self, freshness: str, age_seconds: int | None) -> None:
        with self._lock:
            self.snapshot_freshness_last = freshness
            self.snapshot_age_seconds_last = age_seconds

    def snapshot(self) -> dict[str, int | str | None]:
        with self._lock:
            return {
                "tenant_registry_cache_hit": self.tenant_registry_cache_hit,
                "tenant_registry_cache_miss": self.tenant_registry_cache_miss,
                "empresas_request_count": self.empresas_request_count,
                "permission_cache_hit": self.permission_cache_hit,
                "permission_cache_miss": self.permission_cache_miss,
                "permission_probe_duration_ms": self.permission_probe_duration_ms,
                "permission_endpoints_checked": self.permission_endpoints_checked,
                "permission_probe_http_count": self.permission_probe_http_count,
                "fuel_cache_hit_count": self.fuel_cache_hit_count,
                "fuel_cache_miss_count": self.fuel_cache_miss_count,
                "expense_cache_hit_count": self.expense_cache_hit_count,
                "expense_cache_miss_count": self.expense_cache_miss_count,
                "receivable_cache_hit_count": self.receivable_cache_hit_count,
                "receivable_cache_miss_count": self.receivable_cache_miss_count,
                "webposto_request_total": self.webposto_request_total,
                "webposto_venda_requests": self.webposto_venda_requests,
                "webposto_venda_item_requests": self.webposto_venda_item_requests,
                "webposto_produto_requests": self.webposto_produto_requests,
                "webposto_429_count": self.webposto_429_count,
                "webposto_timeout_count": self.webposto_timeout_count,
                "webposto_5xx_count": self.webposto_5xx_count,
                "duplicate_analysis_count": self.duplicate_analysis_count,
                "duplicate_request_count": self.duplicate_request_count,
                "analysis_trigger_count": self.analysis_trigger_count,
                "snapshot_freshness_last": self.snapshot_freshness_last,
                "snapshot_age_seconds_last": self.snapshot_age_seconds_last,
            }


performance_metrics = PerformanceMetrics()
