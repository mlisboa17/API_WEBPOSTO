"""Catch-up idempotente do SDS — somente GET no WebPosto, sem payloads."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Awaitable

from src.services.sds_identity import (
    COMPLETE_STATUSES,
    LICENSED_SDS_CODES,
    STATUS_FALHA,
    STATUS_PARCIAL,
    STATUS_PENDENTE,
    STATUS_SEM_MOVIMENTO,
    STATUS_SUCESSO,
)
from src.services.sds_process_lock import (
    LockUnavailable,
    NullSdsProcessLock,
    production_process_lock,
)
from src.services.sds_sanitize import sanitize_text, sanitize_value
from src.services.webposto.schemas import WEBPOSTO_WRITES
from src.utils.filial_normalizer import (
    EMPRESA_VIP,
    EMPRESA_VIP_LEGACY_ALIAS,
    resolve_empresa_codigo,
)

logger = logging.getLogger(__name__)

GET_ENDPOINTS = ("ABASTECIMENTO",)


def _count(counters: dict[str, int], item: dict[str, Any]) -> None:
    if item.get("skipped"):
        counters["skipped"] += 1
        return
    status = str(item.get("status") or STATUS_FALHA)
    counters[status] = counters.get(status, 0) + 1


@dataclass
class DayStatus:
    empresa_codigo: int
    data: date
    status: str
    registros_sem_identidade: int = 0
    quantidade_abastecimentos: int | None = None
    tentativas: int = 0
    mensagem: str = ""
    updated_at: datetime | None = None


class InMemoryDayStatusStore:
    def __init__(self) -> None:
        self._rows: dict[tuple[int, date], DayStatus] = {}

    async def get(self, empresa: int, dia: date) -> DayStatus | None:
        return self._rows.get((empresa, dia))

    async def upsert(self, row: DayStatus) -> None:
        self._rows[(row.empresa_codigo, row.data)] = row

    async def last_complete(self, empresa: int) -> date | None:
        days = [
            row.data
            for (emp, _dia), row in self._rows.items()
            if emp == empresa and row.status in COMPLETE_STATUSES
        ]
        return max(days) if days else None

class SdsCatchupService:
    def __init__(
        self,
        *,
        sync_day: Callable[..., Awaitable[dict[str, Any]]] | None = None,
        last_sds_date: Callable[[int], Awaitable[date | None]] | None = None,
        store: InMemoryDayStatusStore | None = None,
        today_fn: Callable[[], date] | None = None,
        max_days: int = 7,
        timeout_seconds: float = 40,
        retries: int = 2,
        sleep_fn: Callable[[float], Awaitable[None]] | None = None,
        process_lock: Any = None,
    ) -> None:
        self._sync_day = sync_day
        self._last_sds_date = last_sds_date
        self._store = store or InMemoryDayStatusStore()
        self._today = today_fn or date.today
        self.max_days = max_days
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self._sleep = sleep_fn or asyncio.sleep
        self._lock = asyncio.Lock()
        self._process_lock = process_lock if process_lock is not None else NullSdsProcessLock()
        self._holder: str | None = None
        self.last_result: dict[str, Any] | None = None
        self.last_run_at: datetime | None = None
        self.running = False

    @property
    def locked(self) -> bool:
        return self._lock.locked()

    def resolve_units(self, empresas: list[int] | None = None) -> list[int]:
        if not empresas:
            return list(LICENSED_SDS_CODES)
        out: list[int] = []
        for raw in empresas:
            code = resolve_empresa_codigo(raw)
            if code == EMPRESA_VIP_LEGACY_ALIAS:
                code = EMPRESA_VIP
            if code in LICENSED_SDS_CODES and code not in out:
                out.append(code)
        return out

    def d_minus_1(self) -> date:
        return self._today() - timedelta(days=1)

    def _locked_payload(self, trigger: str, *, status: str = "LOCKED") -> dict[str, Any]:
        peek = None
        mensagem = (
            "Lock SDS indisponivel"
            if status == "LOCK_UNAVAILABLE"
            else "Catch-up já em execução"
        )
        try:
            peek = self._process_lock.peek()
        except Exception:
            peek = None
        return sanitize_value(
            {
                "success": False,
                "status": status,
                "mensagem": mensagem,
                "webpostoWrites": WEBPOSTO_WRITES,
                "trigger": trigger,
                "lock": peek,
                "metodosWebPosto": [],
                "endpointsGet": [],
            }
        )

    async def last_consolidated(self, empresa: int) -> date | None:
        from_store = await self._store.last_complete(empresa)
        from_sds = await self._last_sds_date(empresa) if self._last_sds_date else None
        candidates = [item for item in (from_store, from_sds) if item]
        return max(candidates) if candidates else None

    async def discover_gaps(
        self,
        *,
        inicio: date | None = None,
        fim: date | None = None,
        empresas: list[int] | None = None,
    ) -> list[tuple[int, date]]:
        units = self.resolve_units(empresas)
        end = fim or self.d_minus_1()
        gaps: list[tuple[int, date]] = []
        for code in units:
            last = inicio - timedelta(days=1) if inicio else await self.last_consolidated(code)
            cursor = (last + timedelta(days=1)) if last else (inicio or end)
            if inicio and cursor < inicio:
                cursor = inicio
            while cursor <= end:
                existing = await self._store.get(code, cursor)
                if existing is None or existing.status not in COMPLETE_STATUSES:
                    gaps.append((code, cursor))
                cursor += timedelta(days=1)
        return gaps

    async def run(
        self,
        *,
        trigger: str = "manual",
        inicio: date | None = None,
        fim: date | None = None,
        empresas: list[int] | None = None,
        max_days: int | None = None,
        force_days: set[date] | None = None,
        include_d1: bool = False,
        dry_run: bool = False,
        fail_fast: bool = False,
    ) -> dict[str, Any]:
        if self._lock.locked():
            return self._locked_payload(trigger)
        acquired = False
        try:
            acquired = bool(self._process_lock.acquire(trigger=trigger))
        except LockUnavailable as exc:
            logger.warning("SDS lock indisponivel: %s", sanitize_text(str(exc)))
            return self._locked_payload(trigger, status="LOCK_UNAVAILABLE")
        except Exception as exc:
            logger.warning("SDS lock acquire falhou: %s", sanitize_text(str(exc)))
            return self._locked_payload(trigger, status="LOCK_UNAVAILABLE")
        if not acquired:
            return self._locked_payload(trigger)
        async with self._lock:
            self._holder = sanitize_text(trigger)
            self.running = True
            started = datetime.now(timezone.utc)
            try:
                result = await self._run_locked(
                    trigger=trigger,
                    inicio=inicio,
                    fim=fim,
                    empresas=empresas,
                    max_days=max_days,
                    force_days=force_days,
                    include_d1=include_d1,
                    dry_run=dry_run,
                    fail_fast=fail_fast,
                    started=started,
                )
                self.last_result = result
                self.last_run_at = datetime.now(timezone.utc)
                return result
            finally:
                self.running = False
                self._holder = None
                try:
                    self._process_lock.release()
                except Exception as exc:
                    logger.warning("SDS lock release falhou: %s", sanitize_text(str(exc)))

    async def _run_locked(
        self,
        *,
        trigger: str,
        inicio: date | None,
        fim: date | None,
        empresas: list[int] | None,
        max_days: int | None,
        force_days: set[date] | None,
        include_d1: bool,
        dry_run: bool,
        fail_fast: bool,
        started: datetime,
    ) -> dict[str, Any]:
        units = self.resolve_units(empresas)
        end = fim or self.d_minus_1()
        gaps = await self.discover_gaps(inicio=inicio, fim=end, empresas=units)
        limit = max_days if max_days is not None else self.max_days
        unique_days = sorted({dia for _emp, dia in gaps})
        planned_days = unique_days[: max(0, limit)]
        planned = [(emp, dia) for emp, dia in gaps if dia in set(planned_days)]
        remaining = max(0, len(unique_days) - len(planned_days))
        counters = {
            STATUS_SUCESSO: 0,
            STATUS_SEM_MOVIMENTO: 0,
            STATUS_PARCIAL: 0,
            STATUS_FALHA: 0,
            STATUS_PENDENTE: 0,
            "skipped": 0,
        }
        detalhes: list[dict[str, Any]] = []
        if dry_run:
            for emp, dia in planned:
                counters[STATUS_PENDENTE] += 1
                detalhes.append(
                    {
                        "empresaCodigo": emp,
                        "data": dia.isoformat(),
                        "status": STATUS_PENDENTE,
                    }
                )
        else:
            interrompida = False
            for emp, dia in planned:
                item = await self._process_day(emp, dia, force=bool(force_days and dia in force_days))
                detalhes.append(item)
                _count(counters, item)
                if fail_fast and str(item.get("status") or "") == STATUS_FALHA:
                    interrompida = True
                    break
            if include_d1 and not interrompida:
                d1 = self.d_minus_1()
                for emp in units:
                    item = await self._process_day(emp, d1, force=False)
                    detalhes.append(item)
                    _count(counters, item)
                    if fail_fast and str(item.get("status") or "") == STATUS_FALHA:
                        interrompida = True
                        break

        payload = {
            "success": counters.get(STATUS_FALHA, 0) == 0,
            "failFast": fail_fast,
            "ondaInterrompida": bool(fail_fast and counters.get(STATUS_FALHA, 0)),
            "trigger": trigger,
            "dryRun": dry_run,
            "webpostoWrites": WEBPOSTO_WRITES,
            "metodosWebPosto": ["GET"] if not dry_run else [],
            "endpointsGet": list(GET_ENDPOINTS) if not dry_run else [],
            "unidades": units,
            "intervalo": {
                "inicio": (inicio or (planned_days[0] if planned_days else end)).isoformat(),
                "fim": end.isoformat(),
            },
            "diasPlanejados": len(planned_days),
            "paresUnidadeDia": len(planned),
            "diasRestantes": remaining,
            "contadores": counters,
            "detalhes": detalhes,
            "startedAt": started.isoformat(),
            "finishedAt": datetime.now(timezone.utc).isoformat(),
            "emAndamento": False,
        }
        logger.info(
            "SDS catch-up trigger=%s dry=%s pares=%s falhas=%s restantes=%s writes=%s",
            trigger,
            dry_run,
            len(planned),
            counters.get(STATUS_FALHA, 0),
            remaining,
            WEBPOSTO_WRITES,
        )
        return sanitize_value(payload)

    async def _process_day(
        self,
        empresa: int,
        dia: date,
        *,
        force: bool,
        allow_complete_reprocess: bool = False,
    ) -> dict[str, Any]:
        existing = await self._store.get(empresa, dia)
        complete = bool(existing and existing.status in COMPLETE_STATUSES)
        if complete and not allow_complete_reprocess:
            return {
                "empresaCodigo": empresa,
                "data": dia.isoformat(),
                "status": existing.status if existing else STATUS_SUCESSO,
                "skipped": True,
            }
        last_error = "Falha de leitura"
        attempts = (existing.tentativas if existing else 0)
        for attempt in range(self.retries + 1):
            attempts += 1
            try:
                if not self._sync_day:
                    raise RuntimeError("sync_day não configurado")
                raw = await asyncio.wait_for(
                    self._sync_day(empresa, dia, force=force),
                    timeout=self.timeout_seconds,
                )
                status = str(raw.get("status") or STATUS_SUCESSO)
                mensagem = sanitize_text(str(raw.get("mensagem") or ""))
                row = DayStatus(
                    empresa_codigo=empresa,
                    data=dia,
                    status=status,
                    registros_sem_identidade=int(raw.get("registrosSemIdentidade") or 0),
                    quantidade_abastecimentos=raw.get("quantidadeAbastecimentos")
                    or raw.get("quantidade_abastecimentos"),
                    tentativas=attempts,
                    mensagem=mensagem,
                )
                await self._store.upsert(row)
                return {
                    "empresaCodigo": empresa,
                    "data": dia.isoformat(),
                    "status": status,
                    "registrosSemIdentidade": row.registros_sem_identidade,
                    "tentativas": attempts,
                }
            except Exception as exc:
                last_error = sanitize_text(str(exc) or "Falha de integração")
                logger.warning(
                    "SDS dia falhou empresa=%s data=%s tentativa=%s",
                    empresa,
                    dia.isoformat(),
                    attempts,
                )
                if attempt < self.retries:
                    await self._sleep(0.4 * (2**attempt))
        row = DayStatus(
            empresa_codigo=empresa,
            data=dia,
            status=STATUS_FALHA,
            tentativas=attempts,
            mensagem=last_error,
        )
        await self._store.upsert(row)
        return {
            "empresaCodigo": empresa,
            "data": dia.isoformat(),
            "status": STATUS_FALHA,
            "mensagem": last_error,
            "tentativas": attempts,
        }

    async def operational_snapshot(self) -> dict[str, Any]:
        end = self.d_minus_1()
        units = list(LICENSED_SDS_CODES)
        last_dates = {}
        pendentes = 0
        for code in units:
            last = await self.last_consolidated(code)
            last_dates[str(code)] = last.isoformat() if last else None
            if last is None:
                pendentes += 1
            else:
                pendentes += max(0, (end - last).days)
        return sanitize_value(
            {
                "webpostoWrites": WEBPOSTO_WRITES,
                "unidades": units,
                "ultimaDataConsolidada": last_dates,
                "diasPendentesEstimados": pendentes,
                "execucaoEmAndamento": self.running,
                "ultimaExecucao": self.last_run_at.isoformat() if self.last_run_at else None,
                "ultimoResultado": self.last_result,
            }
        )


_service: SdsCatchupService | None = None


def get_sds_catchup_service() -> SdsCatchupService:
    global _service
    if _service is None:
        _service = SdsCatchupService()
        _wire_defaults(_service)
    return _service


def _wire_defaults(service: SdsCatchupService) -> None:
    from src.infrastructure.config.settings import settings
    from src.services.data_sync_service import get_data_sync_service

    service.max_days = int(getattr(settings, "data_sync_catchup_max_days", 7) or 7)
    service.timeout_seconds = float(getattr(settings, "data_sync_day_timeout_seconds", 40) or 40)
    service.retries = int(getattr(settings, "data_sync_day_retries", 2) or 2)
    sync = get_data_sync_service()
    service._sync_day = sync.sync_day
    service._last_sds_date = sync.last_summary_date
    service._store = SqlDayStatusStore()
    try:
        service._process_lock = production_process_lock()
    except LockUnavailable:
        raise


class SqlDayStatusStore(InMemoryDayStatusStore):
    async def get(self, empresa: int, dia: date) -> DayStatus | None:
        try:
            from sqlalchemy import select

            from src.infrastructure.config.database import AsyncSessionLocal
            from src.models.sds_day_status_model import SdsDayStatusModel

            async with AsyncSessionLocal() as session:
                stmt = select(SdsDayStatusModel).where(
                    SdsDayStatusModel.empresa_codigo == empresa,
                    SdsDayStatusModel.data_referencia == dia,
                )
                item = (await session.execute(stmt)).scalar_one_or_none()
            if item is None:
                return None
            return DayStatus(
                empresa_codigo=item.empresa_codigo,
                data=item.data_referencia,
                status=item.status,
                registros_sem_identidade=item.registros_sem_identidade,
                quantidade_abastecimentos=item.quantidade_abastecimentos,
                tentativas=item.tentativas,
                mensagem=item.mensagem or "",
                updated_at=getattr(item, "updated_at", None),
            )
        except Exception as exc:
            logger.warning("sds_day_status get falhou: %s", sanitize_text(str(exc)))
            return await super().get(empresa, dia)

    async def upsert(self, row: DayStatus) -> None:
        await super().upsert(row)
        try:
            from sqlalchemy import select

            from src.infrastructure.config.database import AsyncSessionLocal
            from src.models.sds_day_status_model import SdsDayStatusModel

            async with AsyncSessionLocal() as session:
                stmt = select(SdsDayStatusModel).where(
                    SdsDayStatusModel.empresa_codigo == row.empresa_codigo,
                    SdsDayStatusModel.data_referencia == row.data,
                )
                existing = (await session.execute(stmt)).scalar_one_or_none()
                now = datetime.now(timezone.utc)
                if existing:
                    existing.status = row.status
                    existing.registros_sem_identidade = row.registros_sem_identidade
                    existing.quantidade_abastecimentos = row.quantidade_abastecimentos
                    existing.tentativas = row.tentativas
                    existing.mensagem = (row.mensagem or "")[:400]
                    existing.updated_at = now
                else:
                    session.add(
                        SdsDayStatusModel(
                            empresa_codigo=row.empresa_codigo,
                            data_referencia=row.data,
                            status=row.status,
                            registros_sem_identidade=row.registros_sem_identidade,
                            quantidade_abastecimentos=row.quantidade_abastecimentos,
                            tentativas=row.tentativas,
                            mensagem=(row.mensagem or "")[:400],
                            updated_at=now,
                        )
                    )
                await session.commit()
        except Exception as exc:
            logger.warning("sds_day_status upsert falhou: %s", sanitize_text(str(exc)))

    async def last_complete(self, empresa: int) -> date | None:
        try:
            from sqlalchemy import select, func

            from src.infrastructure.config.database import AsyncSessionLocal
            from src.models.sds_day_status_model import SdsDayStatusModel

            async with AsyncSessionLocal() as session:
                stmt = select(func.max(SdsDayStatusModel.data_referencia)).where(
                    SdsDayStatusModel.empresa_codigo == empresa,
                    SdsDayStatusModel.status.in_(tuple(COMPLETE_STATUSES)),
                )
                value = (await session.execute(stmt)).scalar_one_or_none()
            return value
        except Exception:
            return await super().last_complete(empresa)
