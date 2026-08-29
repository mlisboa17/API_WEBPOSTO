"""Onda SDS controlada — somente 5555/11495/74014, intervalo explícito.

Dry-run (sem rede):
    python -m src.jobs.sds_gap_backfill --inicio 2026-08-20 --fim 2026-08-28 --dry-run --max-dias 9

Execução real (somente após autorização):
    $env:WEBPOSTO_WRITES='0'
    $env:PYTHONDONTWRITEBYTECODE='1'
    python -m src.jobs.sds_gap_backfill --inicio 2026-08-20 --fim 2026-08-28 --execute --max-dias 9
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date, timedelta
from typing import Any
from urllib.parse import urlparse

from src.services.sds_identity import (
    COMPLETE_STATUSES,
    LICENSED_SDS_CODES,
    STATUS_FALHA,
)
from src.services.sds_sanitize import sanitize_value
from src.services.webposto.schemas import WEBPOSTO_WRITES
from src.services.webposto.write_policy import is_webposto_write_path

GET_ENDPOINTS = ("ABASTECIMENTO",)
ONDA_INICIO = date(2026, 8, 20)
ONDA_FIM = date(2026, 8, 28)
PRESERVADO_INICIO = date(2026, 8, 13)
PRESERVADO_FIM = date(2026, 8, 19)
MAX_PARES_PENDENTES = 27
MAX_DIAS = 9


class DiscoveryBlocked(RuntimeError):
    """Probe de permissão não é permitido na onda."""


def estimate(inicio: date, fim: date, unidades: tuple[int, ...] = LICENSED_SDS_CODES) -> dict:
    dias = (fim - inicio).days + 1
    if dias < 0:
        dias = 0
    pares = dias * len(unidades)
    return {
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "unidades": list(unidades),
        "diasCalendario": dias,
        "paresUnidadeDia": pares,
        "estimativaGetAbastecimento": pares,
        "endpointsGet": list(GET_ENDPOINTS),
        "metodosEscrita": [],
        "webpostoWrites": WEBPOSTO_WRITES,
        "alias6666": False,
        "failFast": True,
    }


async def _inspect(inicio: date, fim: date) -> dict[str, Any]:
    from src.services.sds_catchup_service import SdsCatchupService, SqlDayStatusStore, _wire_defaults

    svc = SdsCatchupService(store=SqlDayStatusStore(), today_fn=date.today)
    _wire_defaults(svc)
    skipped: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    for emp in LICENSED_SDS_CODES:
        cursor = inicio
        while cursor <= fim:
            existing = await svc._store.get(emp, cursor)
            item = {"empresaCodigo": emp, "data": cursor.isoformat()}
            if existing and existing.status in COMPLETE_STATUSES:
                item["status"] = existing.status
                item["skipped"] = True
                skipped.append(item)
            else:
                item["status"] = existing.status if existing else "PENDENTE"
                pending.append(item)
            cursor += timedelta(days=1)
    return {
        "unidades": list(LICENSED_SDS_CODES),
        "intervalo": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
        "pulados": skipped,
        "pendentes": pending,
        "paresPulados": len(skipped),
        "paresPendentes": len(pending),
        "webpostoWrites": WEBPOSTO_WRITES,
        "alias6666": False,
        "failFast": True,
    }


def _install_wave_guards(stats: dict[str, Any], inicio: date, fim: date) -> None:
    import httpx

    import src.gateway.webposto_client as gateway_module
    from src.gateway.webposto_client import WebPostoClient

    allowed = set(LICENSED_SDS_CODES)
    orig_call = WebPostoClient.call_endpoint
    orig_get = httpx.AsyncClient.get

    async def _single_attempt(operation, attempts=1, *args, **kwargs):
        del attempts, args, kwargs
        return await operation()

    def _no_stale_fallback(self, endpoint_key, params, *, reason):
        del self, endpoint_key, params, reason
        return None

    async def _blocked_discover(self, *args, **kwargs):
        stats["discoveryCalls"] += 1
        raise DiscoveryBlocked("discovery/probe bloqueado na onda")

    async def _guarded_call(self, endpoint_key: str, params: dict[str, Any] | None = None):
        emp = (params or {}).get("empresaCodigo")
        if emp not in (None, "") and int(emp) not in allowed:
            raise RuntimeError("WAVE_ABORT: outra unidade")
        if endpoint_key != "abastecimento":
            raise RuntimeError("WAVE_ABORT: endpoint nao autorizado")
        di = date.fromisoformat(str((params or {}).get("dataInicial") or "")[:10])
        df = date.fromisoformat(str((params or {}).get("dataFinal") or "")[:10])
        if di != df or di < inicio or df > fim:
            raise RuntimeError("WAVE_ABORT: outra data")
        key = f"{int(emp)}|{di.isoformat()}"
        stats["paginas"][key] += 1
        resp = await orig_call(self, endpoint_key, params=params)
        if stats["httpPagina0"].get(key) is None and getattr(resp, "error", None):
            stats["httpPagina0"][key] = getattr(resp.error, "status", None)
        return resp

    async def _counted_get(self, url, *args, **kwargs):
        raw = url if isinstance(url, str) else str(url)
        path = urlparse(raw).path if "://" in raw else raw.split("?", 1)[0]
        if is_webposto_write_path(path):
            raise RuntimeError("WAVE_ABORT: path de escrita")
        if not path.endswith("/ABASTECIMENTO"):
            raise RuntimeError("WAVE_ABORT: endpoint nao autorizado")
        params = kwargs.get("params") or {}
        emp = params.get("empresaCodigo")
        di = str(params.get("dataInicial") or "")[:10]
        key = f"{emp}|{di}"
        stats["gets"][path] += 1
        stats["getsPorPar"][key] += 1
        response = await orig_get(self, url, *args, **kwargs)
        if key not in stats["httpPagina0"]:
            stats["httpPagina0"][key] = int(response.status_code)
        if response.request is not None and (response.request.method or "GET").upper() != "GET":
            raise RuntimeError("WAVE_ABORT: metodo nao GET")
        return response

    WebPostoClient.discover_permissions = _blocked_discover  # type: ignore[method-assign]
    WebPostoClient.call_endpoint = _guarded_call  # type: ignore[method-assign]
    WebPostoClient._fallback_stale = _no_stale_fallback  # type: ignore[method-assign]
    gateway_module.retry_async = _single_attempt
    httpx.AsyncClient.get = _counted_get  # type: ignore[method-assign]


async def _execute(inicio: date, fim: date, max_days: int) -> dict[str, Any]:
    from src.services.abastecimento_service import AbastecimentoService
    from src.services.data_sync_service import get_data_sync_service
    from src.services.sds_catchup_service import SdsCatchupService, _wire_defaults

    stats: dict[str, Any] = {
        "gets": Counter(),
        "getsPorPar": Counter(),
        "paginas": Counter(),
        "httpPagina0": {},
        "discoveryCalls": 0,
        "pares": {},
    }
    _install_wave_guards(stats, inicio, fim)

    sync = get_data_sync_service()
    for emp in LICENSED_SDS_CODES:
        sync._catalog_cache[emp] = {}
        sync._cpm_cache[emp] = {}
    orig_fetch = sync._fetch_abastecimentos
    orig_sync = sync.sync_day
    orig_periodo = AbastecimentoService.get_periodo

    async def _counted_periodo(self, data_inicial, data_final, empresa_codigo=None):
        resp = await orig_periodo(self, data_inicial, data_final, empresa_codigo)
        key = f"{empresa_codigo}|{data_inicial}"
        raw = resp.data
        if isinstance(raw, dict):
            stats["pares"].setdefault(key, {})["linhasRecebidas"] = int(
                raw.get("total") or len(raw.get("dados") or [])
            )
        elif isinstance(raw, list):
            stats["pares"].setdefault(key, {})["linhasRecebidas"] = len(raw)
        return resp

    AbastecimentoService.get_periodo = _counted_periodo  # type: ignore[method-assign]

    async def _counted_fetch(empresa_codigo: int, start: str, end: str):
        if int(empresa_codigo) not in LICENSED_SDS_CODES:
            raise RuntimeError("WAVE_ABORT: outra unidade")
        if start != end or date.fromisoformat(start) < inicio or date.fromisoformat(end) > fim:
            raise RuntimeError("WAVE_ABORT: outra data")
        rows = await orig_fetch(empresa_codigo, start, end)
        stats["pares"].setdefault(f"{empresa_codigo}|{start}", {})["linhasValidas"] = len(rows)
        return rows

    async def _captured_sync(empresa_codigo, data_referencia, force: bool = False):
        raw = await orig_sync(empresa_codigo, data_referencia, force=force)
        stats["pares"].setdefault(f"{empresa_codigo}|{data_referencia.isoformat()}", {}).update(
            {
                "status": raw.get("status"),
                "litros": raw.get("litros"),
                "faturamento": raw.get("faturamento"),
                "abastecimentos": raw.get("quantidadeAbastecimentos"),
                "registrosSemIdentidade": raw.get("registrosSemIdentidade"),
                "contagemConfiavel": raw.get("contagemConfiavel"),
                "ticketMedioLitros": raw.get("ticketMedioLitros"),
                "ticketMedioReais": raw.get("ticketMedioReais"),
                "skus": raw.get("linhas_summary") or raw.get("produtos_descobertos"),
            }
        )
        return raw

    sync._fetch_abastecimentos = _counted_fetch
    sync.sync_day = _captured_sync

    svc = SdsCatchupService()
    _wire_defaults(svc)
    svc.retries = 0
    svc.timeout_seconds = 90
    svc.max_days = max_days
    svc._sync_day = sync.sync_day

    result = await svc.run(
        trigger="cli-wave-20-28",
        inicio=inicio,
        fim=fim,
        empresas=list(LICENSED_SDS_CODES),
        max_days=max_days,
        dry_run=False,
        fail_fast=True,
        include_d1=False,
    )
    result["getsPorEndpoint"] = dict(stats["gets"])
    result["getsPorPar"] = dict(stats["getsPorPar"])
    result["paginasPorPar"] = dict(stats["paginas"])
    result["httpPagina0"] = stats["httpPagina0"]
    result["detalhePares"] = stats["pares"]
    result["discoveryCalls"] = stats["discoveryCalls"]
    return result


def _conference(inicio: date, fim: date) -> dict[str, Any]:
    import sqlite3
    from pathlib import Path

    con = sqlite3.connect(Path("logos_gateway.db").as_posix())
    cobertura = []
    skus = []
    for emp in LICENSED_SDS_CODES:
        row = con.execute(
            """
            SELECT MAX(data_referencia), COUNT(*)
            FROM sales_daily_summary
            WHERE empresa_codigo=? AND data_referencia>=? AND data_referencia<=?
            """,
            (emp, inicio.isoformat(), fim.isoformat()),
        ).fetchone()
        cobertura.append(
            {"empresaCodigo": emp, "ultimaDataNoIntervalo": row[0], "linhasIntervalo": row[1]}
        )
        for item in con.execute(
            """
            SELECT data_referencia, COUNT(*)
            FROM sales_daily_summary
            WHERE empresa_codigo=? AND data_referencia>=? AND data_referencia<=?
            GROUP BY 1
            ORDER BY 1
            """,
            (emp, inicio.isoformat(), fim.isoformat()),
        ):
            skus.append({"empresaCodigo": emp, "data": item[0], "skus": item[1]})
    preservado = []
    for emp in LICENSED_SDS_CODES:
        row = con.execute(
            """
            SELECT COUNT(*), ROUND(SUM(litros_vendidos), 2), ROUND(SUM(faturamento_bruto), 2),
                   SUM(quantidade_abastecimentos)
            FROM sales_daily_summary
            WHERE empresa_codigo=? AND data_referencia>=? AND data_referencia<=?
            """,
            (emp, PRESERVADO_INICIO.isoformat(), PRESERVADO_FIM.isoformat()),
        ).fetchone()
        preservado.append(
            {
                "empresaCodigo": emp,
                "linhas": row[0],
                "litros": row[1],
                "faturamento": row[2],
                "abastecimentos": row[3],
            }
        )
    max_por = {
        emp: con.execute(
            "SELECT MAX(data_referencia) FROM sales_daily_summary WHERE empresa_codigo=?",
            (emp,),
        ).fetchone()[0]
        for emp in LICENSED_SDS_CODES
    }
    alias = con.execute(
        "SELECT COUNT(*) FROM sales_daily_summary WHERE empresa_codigo=6666"
    ).fetchone()[0]
    fora = con.execute(
        """
        SELECT COUNT(*) FROM sales_daily_summary
        WHERE empresa_codigo NOT IN (5555, 11495, 74014)
          AND data_referencia>=? AND data_referencia<=?
        """,
        (inicio.isoformat(), fim.isoformat()),
    ).fetchone()[0]
    depois = con.execute(
        """
        SELECT COUNT(*) FROM sales_daily_summary
        WHERE empresa_codigo IN (5555, 11495, 74014) AND data_referencia>?
        """,
        (fim.isoformat(),),
    ).fetchone()[0]
    con.close()
    return {
        "ultimaDataPorUnidade": {str(k): v for k, v in max_por.items()},
        "coberturaIntervalo": cobertura,
        "skusPorPar": skus,
        "preservado13a19": preservado,
        "alias6666": alias,
        "outrasUnidadesNoIntervalo": fora,
        "linhasAposFim": depois,
    }


def _datas_fora_da_janela(itens: list[dict[str, Any]], inicio: date, fim: date) -> bool:
    ini = inicio.isoformat()
    end = fim.isoformat()
    return any(item["data"] < ini or item["data"] > end for item in itens)


async def _run(inicio: date, fim: date, execute: bool, max_days: int | None) -> int:
    if WEBPOSTO_WRITES != 0:
        print("BLOQUEADO: WEBPOSTO_WRITES != 0")
        return 2
    if inicio != ONDA_INICIO or fim != ONDA_FIM:
        print("BLOQUEADO: esta onda aceita somente 2026-08-20 a 2026-08-28")
        return 2
    if 6666 in LICENSED_SDS_CODES:
        print("BLOQUEADO: 6666 nao pode entrar na onda")
        return 2
    limit = max_days if max_days is not None else MAX_DIAS
    if limit > MAX_DIAS:
        print("BLOQUEADO: max-dias acima de 9")
        return 2

    plan = estimate(inicio, fim)
    inspect = await _inspect(inicio, fim)
    conference_previa = _conference(inicio, fim)
    todas = inspect["pulados"] + inspect["pendentes"]
    confirmacao = {
        "unidades": inspect["unidades"],
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "maxPares": MAX_PARES_PENDENTES,
        "paresPlanejados": plan["paresUnidadeDia"],
        "paresPendentes": inspect["paresPendentes"],
        "paresPuladosSucesso": inspect["paresPulados"],
        "nenhumaDataAntes20": not _datas_fora_da_janela(todas, inicio, fim)
        and all(item["data"] >= inicio.isoformat() for item in todas),
        "nenhumaDataDepois28": all(item["data"] <= fim.isoformat() for item in todas),
        "webpostoWrites": WEBPOSTO_WRITES,
        "somenteAbastecimento": True,
        "discoveryBloqueado": True,
        "fallbackStaleDesligado": True,
        "tentativaUnicaPorPagina": True,
        "cursorRepetidoAmbiguo": True,
        "failFastGlobal": True,
        "sucessoNaoReprocessado": True,
        "intervaloPreservado13a19": conference_previa["preservado13a19"],
    }
    print(json.dumps(sanitize_value({
        "plano": plan,
        "dryRun": not execute,
        "inspecao": inspect,
        "confirmacao": confirmacao,
        "failFast": True,
        "tentativaUnicaPorPagina": True,
        "discoveryBloqueado": True,
        "fallbackStaleDesligado": True,
    }), ensure_ascii=False, indent=2))

    if inspect["unidades"] != list(LICENSED_SDS_CODES):
        print("BLOQUEADO: unidades fora do escopo")
        return 2
    if plan["diasCalendario"] != MAX_DIAS or plan["paresUnidadeDia"] > MAX_PARES_PENDENTES:
        print("BLOQUEADO: intervalo ou pares fora do teto autorizado")
        return 2
    if inspect["paresPendentes"] > MAX_PARES_PENDENTES:
        print("BLOQUEADO: mais de 27 pares pendentes")
        return 2
    if _datas_fora_da_janela(todas, inicio, fim):
        print("BLOQUEADO: par fora de 2026-08-20 a 2026-08-28")
        return 2
    if any(item["data"] < inicio.isoformat() for item in inspect["pendentes"]):
        print("BLOQUEADO: pendente anterior a 20/08")
        return 2
    if any(item["data"] > fim.isoformat() for item in inspect["pendentes"]):
        print("BLOQUEADO: pendente posterior a 28/08")
        return 2
    if not execute:
        return 0

    result = await _execute(inicio, fim, limit)
    conference = _conference(inicio, fim)
    conference["preservado13a19Antes"] = conference_previa["preservado13a19"]
    print(json.dumps(sanitize_value({
        "resultado": result,
        "conferencia": conference,
        "webpostoWrites": WEBPOSTO_WRITES,
        "metodos": ["GET"],
    }), ensure_ascii=False, indent=2, default=str))
    if result.get("discoveryCalls"):
        return 1
    if result.get("ondaInterrompida") or result.get("contadores", {}).get(STATUS_FALHA):
        return 1
    return 0 if result.get("success") else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Onda SDS 20–28/08/2026")
    parser.add_argument("--inicio", default=ONDA_INICIO.isoformat())
    parser.add_argument("--fim", default=ONDA_FIM.isoformat())
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--execute", action="store_true", default=False)
    parser.add_argument("--max-dias", type=int, default=None)
    args = parser.parse_args(argv)
    inicio = date.fromisoformat(args.inicio)
    if str(args.fim).upper() in {"D-1", "D1"}:
        print("BLOQUEADO: D-1 nao autorizado nesta onda")
        return 2
    fim = date.fromisoformat(args.fim)
    execute = bool(args.execute) and not bool(args.dry_run)
    if args.execute and args.dry_run:
        execute = False
    if not args.execute:
        execute = False
    return __import__("asyncio").run(_run(inicio, fim, execute, args.max_dias))


if __name__ == "__main__":
    sys.exit(main())
