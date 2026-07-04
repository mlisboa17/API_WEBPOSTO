"""Owner Analysis Snapshot — Fast Daily Analysis Loop (PERFORMANCE-01)."""

from __future__ import annotations

import asyncio
import uuid
from datetime import timedelta
from typing import Any

from src.services.owner_analysis_models import (
    DETECTOR_SET_SIGNATURE,
    OWNER_ANALYSIS_FRESHNESS_TTL_SECONDS,
    OWNER_ANALYSIS_SNAPSHOT_DIR,
    FreshnessState,
    RefreshJob,
    RefreshStatus,
    StoredAnalysisSnapshot,
    TenantProgressCallback,
)
from src.services.owner_analysis_runner import run_owner_analysis
from src.services.performance.performance_metrics import performance_metrics
from src.services.snapshot_store import SnapshotStore
from src.utils.utc_datetime import age_seconds, parse_utc_datetime, utc_now, utc_now_iso


class OwnerAnalysisSnapshotService:
    """Armazena último resultado válido e orquestra refresh em background."""

    def __init__(
        self,
        output_dir: str = OWNER_ANALYSIS_SNAPSHOT_DIR,
        freshness_ttl_seconds: float = OWNER_ANALYSIS_FRESHNESS_TTL_SECONDS,
    ) -> None:
        self._store = SnapshotStore(output_dir, freshness_ttl_seconds)
        self._freshness_ttl = freshness_ttl_seconds
        self._jobs: dict[str, RefreshJob] = {}
        self._scope_running: dict[str, str] = {}
        self._scope_locks: dict[str, asyncio.Lock] = {}
        self._lock = asyncio.Lock()

    async def _get_scope_lock(self, scope_key: str) -> asyncio.Lock:
        async with self._lock:
            scope_lock = self._scope_locks.get(scope_key)
            if scope_lock is None:
                scope_lock = asyncio.Lock()
                self._scope_locks[scope_key] = scope_lock
            return scope_lock

    def _cleanup_scope_lock(self, scope_key: str) -> None:
        if scope_key in self._scope_running:
            return
        self._scope_locks.pop(scope_key, None)

    def _peek_active_job(self, scope_key: str) -> RefreshJob | None:
        """Consulta job ativo sem efeitos colaterais (single-flight)."""
        running_id = self._scope_running.get(scope_key)
        if not running_id:
            return None
        job = self._jobs.get(running_id)
        if job and job.status in {RefreshStatus.PENDING, RefreshStatus.RUNNING}:
            return job
        return None

    def _release_scope_if_terminal(self, scope_key: str, analysis_id: str) -> None:
        if self._scope_running.get(scope_key) == analysis_id:
            self._scope_running.pop(scope_key, None)
        self._cleanup_scope_lock(scope_key)

    async def _acquire_refresh_scope(
        self,
        scope_key: str,
    ) -> tuple[RefreshJob, bool]:
        """
        Reserva atomicamente um refresh por scope.
        Retorna (job, already_running).
        Caller deve segurar o scope_lock externo.
        """
        async with self._lock:
            active = self._peek_active_job(scope_key)
            if active:
                active.duplicate_prevented = True
                performance_metrics.record_duplicate_analysis()
                return active, True

            stale_id = self._scope_running.pop(scope_key, None)
            if stale_id:
                self._jobs.pop(stale_id, None)

            analysis_id = str(uuid.uuid4())
            job = RefreshJob(
                analysis_id=analysis_id,
                scope_key=scope_key,
                status=RefreshStatus.PENDING,
                started_at=utc_now_iso(),
                progress_message="Preparando análise...",
            )
            self._jobs[analysis_id] = job
            self._scope_running[scope_key] = analysis_id
            return job, False

    @staticmethod
    def build_scope_key(
        period_start: str,
        period_end: str,
        *,
        empresa_codigo: str | None = None,
        tenant_set: list[str] | None = None,
    ) -> str:
        tenants = ",".join(sorted(tenant_set)) if tenant_set else "all_discovered"
        empresa = str(empresa_codigo).strip() if empresa_codigo else "all"
        return f"{period_start}:{period_end}:{tenants}:{DETECTOR_SET_SIGNATURE}:{empresa}"

    @classmethod
    def snapshot_storage_key(cls, scope_key: str) -> str:
        return f"owner_analysis:last_valid:{scope_key}"

    def _snapshot_age_seconds(self, completed_at: str | None) -> int | None:
        if not completed_at:
            return None
        try:
            return age_seconds(completed_at)
        except ValueError:
            return None

    def _is_snapshot_fresh(self, stored: StoredAnalysisSnapshot | None) -> bool:
        if not stored:
            return False
        if stored.expires_at:
            try:
                return utc_now() <= parse_utc_datetime(stored.expires_at)
            except ValueError:
                pass
        age = self._snapshot_age_seconds(stored.completed_at)
        return age is not None and age <= self._freshness_ttl

    def _load_stored(self, scope_key: str) -> StoredAnalysisSnapshot | None:
        payload, _expired = self._store.load_stale(self.snapshot_storage_key(scope_key))
        if not payload:
            return None
        snap = payload.get("snapshot") or {}
        if not snap.get("analysis_id"):
            return None
        try:
            return StoredAnalysisSnapshot(
                analysis_id=str(snap["analysis_id"]),
                response=dict(snap.get("response") or {}),
                period_start=str(snap.get("period_start") or ""),
                period_end=str(snap.get("period_end") or ""),
                scope_key=str(snap.get("scope_key") or scope_key),
                created_at=str(snap.get("created_at") or payload.get("lastUpdated") or ""),
                completed_at=str(snap.get("completed_at") or payload.get("lastUpdated") or ""),
                duration_ms=int(snap.get("duration_ms") or 0),
                expires_at=str(snap.get("expires_at") or ""),
                refresh_status=RefreshStatus(str(snap.get("refresh_status") or RefreshStatus.COMPLETED.value)),
                metrics=dict(snap.get("metrics") or {}),
            )
        except (TypeError, ValueError):
            return None

    def _running_job_for_scope(self, scope_key: str) -> RefreshJob | None:
        job = self._peek_active_job(scope_key)
        if job:
            return job
        running_id = self._scope_running.get(scope_key)
        if running_id and running_id not in self._jobs:
            self._scope_running.pop(scope_key, None)
            self._cleanup_scope_lock(scope_key)
        return None

    def _resolve_freshness(
        self,
        stored: StoredAnalysisSnapshot | None,
        scope_key: str,
    ) -> FreshnessState:
        running = self._running_job_for_scope(scope_key)
        if running:
            return FreshnessState.STALE_REFRESHING if stored else FreshnessState.NO_ANALYSIS
        if not stored:
            return FreshnessState.NO_ANALYSIS
        if self._is_snapshot_fresh(stored):
            return FreshnessState.FRESH
        return FreshnessState.STALE

    def _coverage_from_job(self, job: RefreshJob | None) -> dict[str, Any] | None:
        if not job:
            return None
        return {
            "tenants_total": job.tenants_total,
            "tenants_completed": job.tenants_completed,
            "tenants_failed": job.tenants_failed,
            "progress_message": job.progress_message,
        }

    def _envelope(
        self,
        *,
        scope_key: str,
        stored: StoredAnalysisSnapshot | None,
        job: RefreshJob | None,
        auto_refresh_triggered: bool = False,
    ) -> dict[str, Any]:
        freshness = self._resolve_freshness(stored, scope_key)
        running = job or self._running_job_for_scope(scope_key)
        last_completed_id = stored.analysis_id if stored else None
        last_analysis_at = stored.completed_at if stored else None
        snapshot_age = self._snapshot_age_seconds(last_analysis_at)

        if stored:
            body = dict(stored.response)
        else:
            body = {
                "success": True,
                "data": {
                    "top_5_decisions": [],
                    "observations": [],
                    "total_decisions": 0,
                    "total_observations": 0,
                    "filtered_by_confidence": 0,
                    "has_sufficient_data": False,
                    "message": None,
                },
            }

        refresh_status = (
            running.status.value
            if running
            else (stored.refresh_status.value if stored else RefreshStatus.IDLE.value)
        )

        body.update({
            "freshness": freshness.value,
            "refresh_status": refresh_status,
            "analysis_id": running.analysis_id if running else last_completed_id,
            "last_completed_analysis_id": last_completed_id,
            "last_analysis_at": last_analysis_at,
            "snapshot_age_seconds": snapshot_age,
            "snapshot_freshness_ttl_seconds": int(self._freshness_ttl),
            "coverage": self._coverage_from_job(running),
            "auto_refresh_triggered": auto_refresh_triggered,
            "scope_key": scope_key,
        })

        if freshness == FreshnessState.NO_ANALYSIS:
            body.pop("monitoring_state", None)
            body.pop("analysis_status", None)

        performance_metrics.record_snapshot_freshness(freshness.value, snapshot_age)
        return body

    async def get_current_analysis(
        self,
        period_start: str,
        period_end: str,
        *,
        empresa_codigo: str | None = None,
        auto_refresh: bool = True,
    ) -> dict[str, Any]:
        scope_key = self.build_scope_key(
            period_start,
            period_end,
            empresa_codigo=empresa_codigo,
        )
        stored = self._load_stored(scope_key)
        running = self._running_job_for_scope(scope_key)
        freshness = self._resolve_freshness(stored, scope_key)

        auto_triggered = False
        if auto_refresh and freshness in {FreshnessState.NO_ANALYSIS, FreshnessState.STALE} and not running:
            trigger = await self.trigger_refresh(
                period_start,
                period_end,
                empresa_codigo=empresa_codigo,
                reason="auto_freshness",
            )
            running = self._jobs.get(trigger["analysis_id"])
            auto_triggered = True

        return self._envelope(
            scope_key=scope_key,
            stored=stored,
            job=running,
            auto_refresh_triggered=auto_triggered,
        )

    async def trigger_refresh(
        self,
        period_start: str,
        period_end: str,
        *,
        empresa_codigo: str | None = None,
        reason: str = "manual",
        force_tenant_discovery: bool = False,
    ) -> dict[str, Any]:
        scope_key = self.build_scope_key(
            period_start,
            period_end,
            empresa_codigo=empresa_codigo,
        )

        scope_lock = await self._get_scope_lock(scope_key)
        async with scope_lock:
            job, already_running = await self._acquire_refresh_scope(scope_key)
            if already_running:
                return {
                    "analysis_id": job.analysis_id,
                    "refresh_status": job.status.value,
                    "already_running": True,
                    "scope_key": scope_key,
                    "reason": reason,
                }

            analysis_id = job.analysis_id
            job.status = RefreshStatus.RUNNING
            job.progress_message = "Iniciando análise dos postos..."
            performance_metrics.record_analysis_trigger()

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    self._run_refresh(
                        analysis_id=analysis_id,
                        period_start=period_start,
                        period_end=period_end,
                        empresa_codigo=empresa_codigo,
                        force_tenant_discovery=force_tenant_discovery,
                    )
                )
            except RuntimeError:
                async with self._lock:
                    job.status = RefreshStatus.FAILED
                    job.error = "Event loop indisponível para background refresh"
                    self._release_scope_if_terminal(scope_key, analysis_id)

            return {
                "analysis_id": analysis_id,
                "refresh_status": RefreshStatus.PENDING.value,
                "already_running": False,
                "scope_key": scope_key,
                "reason": reason,
            }

    async def _run_refresh(
        self,
        *,
        analysis_id: str,
        period_start: str,
        period_end: str,
        empresa_codigo: str | None,
        force_tenant_discovery: bool,
    ) -> None:
        job = self._jobs.get(analysis_id)
        if not job:
            return

        job.progress_message = job.progress_message or "Iniciando análise dos postos..."
        job.tenants_failed = 0

        async def on_tenant_progress(
            record,
            completed: int,
            total: int,
        ) -> None:
            job.tenants_total = total
            job.tenants_completed = completed
            if record.status == "FAILED":
                job.tenants_failed += 1
            job.progress_message = f"Analisando {completed} de {total} postos"
            job.current_detector = DETECTOR_SET_SIGNATURE

        try:
            result = await run_owner_analysis(
                period_start,
                period_end,
                analysis_id=analysis_id,
                empresa_codigo=empresa_codigo,
                force_tenant_discovery=force_tenant_discovery,
                on_tenant_progress=on_tenant_progress,
            )
        except Exception as exc:
            job.status = RefreshStatus.FAILED
            job.completed_at = utc_now_iso()
            job.error = str(exc)[:220]
            job.progress_message = "Não foi possível concluir a análise"
            self._release_scope_if_terminal(job.scope_key, analysis_id)
            return

        analysis_status = str(result.get("analysis_status") or "")
        meta = result.get("_meta") or {}
        job.tenants_total = int(meta.get("tenants_total") or job.tenants_total)
        job.tenants_completed = int(meta.get("tenants_analyzed") or 0) + int(meta.get("tenants_failed") or 0)
        job.tenants_failed = int(meta.get("tenants_failed") or 0)
        job.completed_at = utc_now_iso()

        if analysis_status == "ANALYSIS_ERROR":
            job.status = RefreshStatus.FAILED
            job.progress_message = "Não foi possível concluir a análise"
            self._release_scope_if_terminal(job.scope_key, analysis_id)
            return

        refresh_result = RefreshStatus.PARTIAL if analysis_status == "PARTIAL_ANALYSIS" else RefreshStatus.COMPLETED
        job.status = refresh_result
        job.progress_message = (
            f"{job.tenants_completed - job.tenants_failed} de {job.tenants_total} postos analisados"
            if job.tenants_failed
            else "Análise concluída"
        )

        completed_at = result.get("generated_at") or utc_now_iso()
        expires_at = (utc_now() + timedelta(seconds=self._freshness_ttl)).isoformat()
        stored = StoredAnalysisSnapshot(
            analysis_id=analysis_id,
            response={
                k: v for k, v in result.items() if not k.startswith("_")
            },
            period_start=period_start,
            period_end=period_end,
            scope_key=job.scope_key,
            created_at=job.started_at,
            completed_at=completed_at,
            duration_ms=int((result.get("_meta") or {}).get("duration_ms") or 0),
            expires_at=expires_at,
            refresh_status=refresh_result,
            metrics=performance_metrics.snapshot(),
        )
        self._store.save(
            self.snapshot_storage_key(job.scope_key),
            stored.to_store_payload(),
        )
        self._release_scope_if_terminal(job.scope_key, analysis_id)

    def get_refresh_status(self, analysis_id: str) -> dict[str, Any] | None:
        job = self._jobs.get(analysis_id)
        if not job:
            stored_scope = None
            for scope, running_id in self._scope_running.items():
                if running_id == analysis_id:
                    stored_scope = scope
                    break
            if not stored_scope:
                return None
            job = self._jobs.get(analysis_id)
            if not job:
                return None
        return job.to_dict()

    def get_metrics(self) -> dict[str, Any]:
        return performance_metrics.snapshot()


_owner_analysis_snapshot = OwnerAnalysisSnapshotService()


def get_owner_analysis_snapshot_service() -> OwnerAnalysisSnapshotService:
    return _owner_analysis_snapshot
