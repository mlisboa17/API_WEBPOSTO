"""Cache In-Memory RAM para pista (Cockpit 30s) — sem Redis.

Processo único (API_WORKERS=1). Leituras trocam só o ponteiro do snapshot
(sem deepcopy) para manter <50ms e não bloquear o event loop.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from src.services.webposto_pista_service import (
    AbastecimentoRestV1,
    ENDPOINT_REDE,
    FONTE,
    ListaAbastecimentosResponse,
    ResumoDiaPista,
    WebPostoPistaService,
    get_pista_service,
    totais_from_resumo,
)

LOGGER = logging.getLogger(__name__)
TZ = ZoneInfo("America/Recife")


@dataclass(frozen=True)
class PistaCacheSnapshot:
    """Snapshot imutável após publish (listas tratadas como read-only)."""

    data_ref: str = ""
    pendentes: tuple[AbastecimentoRestV1, ...] = ()
    baixados: tuple[AbastecimentoRestV1, ...] = ()
    resumo_dia: ResumoDiaPista = field(default_factory=ResumoDiaPista)
    ultima_sincronizacao_iso: str | None = None
    syncing: bool = False
    last_error: str | None = None
    observacoes: tuple[str, ...] = ()
    sync_count: int = 0
    last_duration_ms: float = 0.0


class PistaCacheService:
    """Storage RAM — publish atômico por troca de ponteiro."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._snap = PistaCacheSnapshot()

    @property
    def ready(self) -> bool:
        return self._snap.ultima_sincronizacao_iso is not None

    def get_snapshot(self) -> PistaCacheSnapshot:
        """Leitura O(1) — sem deepcopy (listas imutáveis pós-publish)."""
        return self._snap

    async def mark_syncing(self, syncing: bool) -> None:
        async with self._lock:
            s = self._snap
            self._snap = PistaCacheSnapshot(
                data_ref=s.data_ref,
                pendentes=s.pendentes,
                baixados=s.baixados,
                resumo_dia=s.resumo_dia,
                ultima_sincronizacao_iso=s.ultima_sincronizacao_iso,
                syncing=syncing,
                last_error=s.last_error,
                observacoes=s.observacoes,
                sync_count=s.sync_count,
                last_duration_ms=s.last_duration_ms,
            )

    async def run_sync(
        self,
        service: WebPostoPistaService | None = None,
        *,
        force_permissions: bool = False,
    ) -> PistaCacheSnapshot:
        svc = service or get_pista_service()
        hoje = str(date.today())
        t0 = datetime.now(TZ)
        await self.mark_syncing(True)
        try:
            await self._ensure_permissions(svc, force=force_permissions)
            # Uma passagem "Todos" (AbastecimentoRede) → split pendentes/baixados
            pend_items, baix_items, baix_resumo, baix_obs, baix_err = (
                await svc.coletar_pista_universo(data_inicio=hoje, data_fim=hoje)
            )
            pend_resp = ListaAbastecimentosResponse(
                success=baix_err is None,
                status="PENDENTE",
                total=len(pend_items),
                items=pend_items,
                observacoes=list(baix_obs or []),
                error=baix_err,
            )

            auth_poison = _looks_like_auth_poison(baix_err, baix_obs, pend_resp)
            if auth_poison and not baix_items and not pend_items:
                LOGGER.warning(
                    "pista_cache: sync vazia por autorização — force discover_permissions + retry"
                )
                await self._ensure_permissions(svc, force=True)
                pend_items, baix_items, baix_resumo, baix_obs, baix_err = (
                    await svc.coletar_pista_universo(data_inicio=hoje, data_fim=hoje)
                )
                pend_resp = ListaAbastecimentosResponse(
                    success=baix_err is None,
                    status="PENDENTE",
                    total=len(pend_items),
                    items=pend_items,
                    observacoes=list(baix_obs or []),
                    error=baix_err,
                )

            return await self._publish(
                pend_resp, baix_items, baix_resumo, baix_obs, baix_err, hoje, t0
            )
        except Exception as exc:
            LOGGER.exception("pista_cache.run_sync falhou: %s", exc)
            await self.mark_syncing(False)
            async with self._lock:
                s = self._snap
                self._snap = PistaCacheSnapshot(
                    data_ref=s.data_ref,
                    pendentes=s.pendentes,
                    baixados=s.baixados,
                    resumo_dia=s.resumo_dia,
                    ultima_sincronizacao_iso=s.ultima_sincronizacao_iso,
                    syncing=False,
                    last_error=str(exc),
                    observacoes=s.observacoes,
                    sync_count=s.sync_count,
                    last_duration_ms=s.last_duration_ms,
                )
                return self._snap

    @staticmethod
    async def _ensure_permissions(svc: WebPostoPistaService, *, force: bool) -> None:
        try:
            from src.utils.permission_cache import clear_permissions

            if force:
                clear_permissions()
            await svc.client.discover_permissions(force=force)
        except Exception as exc:
            LOGGER.warning("pista_cache: discover_permissions falhou: %s", exc)

    async def _publish(
        self,
        pend_resp: ListaAbastecimentosResponse,
        baix_items: list[AbastecimentoRestV1],
        baix_resumo: ResumoDiaPista,
        baix_obs: list[str],
        baix_err: str | None,
        hoje: str,
        t0: datetime,
    ) -> PistaCacheSnapshot:
        pendentes = tuple(pend_resp.items or [])
        resumo = baix_resumo or ResumoDiaPista()
        if pendentes:
            resumo = WebPostoPistaService._merge_pendentes_resumo(resumo, list(pendentes))

        obs = tuple(list(pend_resp.observacoes or []) + list(baix_obs or []))
        err = pend_resp.error or baix_err
        now = datetime.now(TZ)
        duration_ms = (now - t0).total_seconds() * 1000.0

        async with self._lock:
            prev = self._snap
            new_empty = not baix_items and not pendentes
            prev_good = bool(prev.baixados or prev.pendentes)
            auth_fail = bool(
                err
                and (
                    "AUTHORIZATION" in str(err).upper()
                    or "permiss" in str(err).lower()
                )
            )

            if new_empty and prev_good and (auth_fail or err):
                snap = PistaCacheSnapshot(
                    data_ref=prev.data_ref,
                    pendentes=prev.pendentes,
                    baixados=prev.baixados,
                    resumo_dia=prev.resumo_dia,
                    ultima_sincronizacao_iso=prev.ultima_sincronizacao_iso,
                    syncing=False,
                    last_error=err or "sync_vazia_preservou_cache",
                    observacoes=tuple(
                        list(obs)
                        + [
                            "Sync vazia/auth — mantido snapshot anterior (stale-while-revalidate)."
                        ]
                    ),
                    sync_count=prev.sync_count,
                    last_duration_ms=round(duration_ms, 1),
                )
                self._snap = snap
                LOGGER.warning(
                    "pista_cache sync preservou snapshot anterior (baix=%s) após falha: %s",
                    len(prev.baixados),
                    err,
                )
                return snap

            snap = PistaCacheSnapshot(
                data_ref=hoje,
                pendentes=pendentes,
                baixados=tuple(baix_items),
                resumo_dia=resumo,
                ultima_sincronizacao_iso=now.isoformat(),
                syncing=False,
                last_error=err,
                observacoes=obs,
                sync_count=prev.sync_count + 1,
                last_duration_ms=round(duration_ms, 1),
            )
            self._snap = snap
            LOGGER.info(
                "pista_cache sync#%s data=%s pend=%s baix=%s totalDia=%s litros=%.3f valor=%.2f em %.0fms",
                snap.sync_count,
                hoje,
                len(pendentes),
                len(baix_items),
                resumo.totalAbastecimentos,
                resumo.totalLitros,
                resumo.totalValor,
                duration_ms,
            )
            return snap

    def _enrich(
        self,
        resp: ListaAbastecimentosResponse,
        snap: PistaCacheSnapshot,
    ) -> ListaAbastecimentosResponse:
        totais = totais_from_resumo(snap.resumo_dia, snap.baixados)
        resp.resumoDia = snap.resumo_dia
        resp.totaisDia = totais
        resp.ultimaSincronizacaoIso = snap.ultima_sincronizacao_iso
        resp.totalRealDia = totais.qtdTotalAbastecimentos
        resp.volumetriaTotalDia = totais.volumetriaTotalLitros
        resp.fromCache = True
        resp.synthetic = False
        resp.fonte = f"{FONTE}+RAM_CACHE"
        if not snap.ultima_sincronizacao_iso:
            resp.observacoes = list(resp.observacoes or []) + [
                "Cache aquecendo — primeira sincronização Quality em andamento."
            ]
        elif snap.last_error and not resp.error:
            resp.observacoes = list(resp.observacoes or []) + [
                f"Última sync com aviso: {snap.last_error}"
            ]
        return resp

    async def response_pendentes(
        self,
        id_empresa: int | None = None,
        id_bico: int | None = None,
    ) -> ListaAbastecimentosResponse:
        snap = self.get_snapshot()
        items: list[AbastecimentoRestV1] = list(snap.pendentes)
        if id_empresa is not None:
            items = [i for i in items if i.idEmpresa == int(id_empresa)]
        if id_bico is not None:
            items = [i for i in items if i.bico == int(id_bico)]
        resp = ListaAbastecimentosResponse(
            success=True,
            status="PENDENTE",
            total=len(items),
            items=items,
            endpoint=ENDPOINT_REDE,
            observacoes=list(snap.observacoes),
        )
        return self._enrich(resp, snap)

    async def response_baixados(
        self,
        id_empresa: int | None = None,
        data_inicio: str | None = None,
        data_fim: str | None = None,
        pagina: int = 1,
        limite: int = 100,
    ) -> ListaAbastecimentosResponse:
        snap = self.get_snapshot()
        hoje = str(date.today())
        start = data_inicio or hoje
        end = data_fim or hoje
        pagina = max(1, int(pagina or 1))
        limite = max(1, min(500, int(limite or 100)))

        if snap.data_ref and (start != snap.data_ref or end != snap.data_ref):
            resp = ListaAbastecimentosResponse(
                success=True,
                status="BAIXADO",
                total=0,
                pagina=pagina,
                limite=limite,
                items=[],
                observacoes=[
                    f"Cache RAM cobre data_ref={snap.data_ref}; "
                    f"pedido={start}..{end} sem Quality síncrono."
                ],
            )
            return self._enrich(resp, snap)

        items: list[AbastecimentoRestV1] = list(snap.baixados)
        if id_empresa is not None:
            items = [i for i in items if i.idEmpresa == int(id_empresa)]
        offset = (pagina - 1) * limite
        resp = ListaAbastecimentosResponse(
            success=True,
            status="BAIXADO",
            total=len(items),
            pagina=pagina,
            limite=limite,
            items=items[offset : offset + limite],
            endpoint=ENDPOINT_REDE,
            observacoes=list(snap.observacoes),
        )
        return self._enrich(resp, snap)

    async def response_kpis(self) -> dict[str, Any]:
        t0 = datetime.now(TZ)
        snap = self.get_snapshot()
        totais = totais_from_resumo(snap.resumo_dia, snap.baixados)
        latency_ms = (datetime.now(TZ) - t0).total_seconds() * 1000.0
        return {
            "success": True,
            "synthetic": False,
            "fromCache": True,
            "fonte": f"{FONTE}+RAM_CACHE",
            "ultimaSincronizacaoIso": snap.ultima_sincronizacao_iso,
            "syncing": snap.syncing,
            "dataRef": snap.data_ref or str(date.today()),
            "totaisDia": totais.model_dump(),
            "totalRealDia": totais.qtdTotalAbastecimentos,
            "volumetriaTotalDia": totais.volumetriaTotalLitros,
            "resumoDia": snap.resumo_dia.model_dump(),
            "fraude": {
                "alertasCriticos": totais.alertasCriticosRetencao,
                "valorCriticoRetencao": totais.valorCriticoRetencao,
                "valorCartoesDia": totais.valorCartoesDia,
                "qtdCartoesDia": totais.qtdCartoesDia,
                "limiarCriticoMinutos": 30,
                "fonteRegra": "retenção cartão > 30 min (cache RAM = mesma regra card-fraud)",
            },
            "observacoes": list(snap.observacoes),
            "lastDurationMs": snap.last_duration_ms,
            "latencyMs": round(latency_ms, 3),
            "syncCount": snap.sync_count,
            "error": snap.last_error,
        }

    async def status(self) -> dict[str, Any]:
        snap = self.get_snapshot()
        return {
            "ready": bool(snap.ultima_sincronizacao_iso),
            "syncing": snap.syncing,
            "ultimaSincronizacaoIso": snap.ultima_sincronizacao_iso,
            "dataRef": snap.data_ref,
            "pendentes": len(snap.pendentes),
            "baixados": len(snap.baixados),
            "totalDia": snap.resumo_dia.totalAbastecimentos,
            "syncCount": snap.sync_count,
            "lastDurationMs": snap.last_duration_ms,
            "lastError": snap.last_error,
        }


def _looks_like_auth_poison(
    baix_err: str | None,
    baix_obs: list[str],
    pend_resp: ListaAbastecimentosResponse,
) -> bool:
    blob = " ".join(
        [
            str(baix_err or ""),
            str(pend_resp.error or ""),
            " ".join(baix_obs or []),
            " ".join(pend_resp.observacoes or []),
        ]
    ).upper()
    return "AUTHORIZATION" in blob or "PERMISSAO" in blob or "PERMISSION" in blob


_cache: PistaCacheService | None = None


def get_pista_cache() -> PistaCacheService:
    global _cache
    if _cache is None:
        _cache = PistaCacheService()
    return _cache
