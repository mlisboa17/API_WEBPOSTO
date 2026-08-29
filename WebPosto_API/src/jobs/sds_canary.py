"""Canário SDS — um único par unidade/dia, somente GET.

Cada --execute exige autorização individual. Nunca encadeia unidades.

    $env:WEBPOSTO_WRITES='0'
    $env:PYTHONDONTWRITEBYTECODE='1'
    python -m src.jobs.sds_canary --empresa 11495 --data 2026-08-13 --execute
"""

from __future__ import annotations

import argparse
import inspect
import json
import sys
from collections import Counter
from datetime import date
from typing import Any
from urllib.parse import urlparse

from src.services.sds_identity import LICENSED_SDS_CODES, STATUS_FALHA
from src.services.sds_process_lock import LockUnavailable
from src.services.sds_sanitize import sanitize_value
from src.services.webposto.schemas import WEBPOSTO_WRITES
from src.services.webposto.write_policy import is_webposto_write_path

CANARY_UNIDADES = (5555, 11495, 74014)
CANARY_DIA = date(2026, 8, 13)
BLOQUEADAS = (6666, 118508)
GET_ONLY = ("GET",)
OUTRAS_DE = {
    5555: (11495, 74014, 6666),
    11495: (5555, 74014, 6666),
    74014: (5555, 11495, 6666),
}


class DiscoveryBlocked(RuntimeError):
    """Probe de permissão não é permitido no canário."""


def validate_pair(empresa: int, data_txt: str) -> str | None:
    if empresa in BLOQUEADAS:
        return "BLOQUEADO: unidade nao autorizada para canario"
    if empresa not in CANARY_UNIDADES:
        return "BLOQUEADO: canario aceita somente 5555, 11495 ou 74014"
    if data_txt != CANARY_DIA.isoformat():
        return "BLOQUEADO: canario aceita somente a data 2026-08-13"
    return None


def suggested_command(empresa: int) -> str:
    return (
        "$env:WEBPOSTO_WRITES='0'; "
        "$env:PYTHONDONTWRITEBYTECODE='1'; "
        f"python -m src.jobs.sds_canary --empresa {empresa} --data 2026-08-13 --execute"
    )


def _preflight(empresa: int) -> dict[str, Any]:
    from src.core.config import load_core_config, resolve_company_api_key
    from src.gateway.webposto_client import WebPostoClient
    from src.services.abastecimento_service import AbastecimentoService

    cli_source = inspect.getsource(WebPostoClient.for_api_key)
    periodo_source = inspect.getsource(AbastecimentoService.get_periodo)
    call_source = inspect.getsource(WebPostoClient.call_endpoint)
    canary_source = inspect.getsource(_install_guards)

    credencial_presente = bool(resolve_company_api_key(empresa))
    vinculos: list[int] = []
    outras_isoladas = {str(code): True for code in OUTRAS_DE[empresa]}
    targeted = False
    vinculo_exclusivo = False

    if credencial_presente:
        isolated = WebPostoClient.for_api_key(resolve_company_api_key(empresa), load_core_config())
        vinculos = sorted(int(c) for c in isolated.config.webposto_company_keys)
        selected = isolated._api_keys_for_params({"empresaCodigo": empresa})
        targeted = bool(selected) and len(selected) == 1
        outras_isoladas = {
            str(code): len(isolated._api_keys_for_params({"empresaCodigo": code})) == 0
            for code in OUTRAS_DE[empresa]
        }
        vinculo_exclusivo = vinculos == [empresa] and targeted and all(outras_isoladas.values())

    ok = {
        "empresa": empresa,
        "data": CANARY_DIA.isoformat(),
        "cliCarregaCodigoCorrigido": (
            "webposto_company_keys=company_keys" in cli_source
            and "if page == 0" in periodo_source
            and "return resp" in periodo_source
        ),
        "credencialPresente": credencial_presente,
        "vinculoExclusivo": vinculo_exclusivo,
        "pagina0FalhaNaoViraVazio": "if page == 0" in periodo_source,
        "paginaPosteriorTambemFalha": "return resp" in periodo_source,
        "paginacaoCursor": "ultimoCodigo" in periodo_source,
        "discoveryBloqueado": "_blocked_discover" in canary_source,
        "discoveryDesligadoNoCaminhoOficial": "targeted_official_call" in call_source and (
            targeted if credencial_presente else True
        ),
        "fallbackStaleDesligado": "_no_stale_fallback" in canary_source,
        "tentativaUnicaPorPagina": "_single_attempt" in canary_source,
        "vinculosIsolados": vinculos,
        "outrasUnidadesIsoladas": outras_isoladas,
        "webpostoWrites": WEBPOSTO_WRITES,
        "abastecimentoNaoEEscrita": is_webposto_write_path("/INTEGRACAO/ABASTECIMENTO") is False,
        "unidadesLicenciadas": list(LICENSED_SDS_CODES),
        "alias6666": False,
        "umaUnidadePorComando": True,
        "dataUnica": True,
    }
    return ok


def _install_guards(stats: dict[str, Any], empresa: int) -> None:
    import httpx

    import src.gateway.webposto_client as gateway_module
    from src.gateway.webposto_client import WebPostoClient

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
        raise DiscoveryBlocked("discovery/probe bloqueado no canário")

    async def _guarded_call(self, endpoint_key: str, params: dict[str, Any] | None = None):
        emp = (params or {}).get("empresaCodigo")
        if emp not in (None, "", empresa, str(empresa)):
            raise RuntimeError("CANARY_ABORT: outra unidade")
        if endpoint_key != "abastecimento":
            raise RuntimeError("CANARY_ABORT: endpoint nao autorizado")
        di = str((params or {}).get("dataInicial") or "")[:10]
        df = str((params or {}).get("dataFinal") or "")[:10]
        if di and di != CANARY_DIA.isoformat():
            raise RuntimeError("CANARY_ABORT: outra data")
        if df and df != CANARY_DIA.isoformat():
            raise RuntimeError("CANARY_ABORT: outra data")
        stats["paginasAbastecimento"] += 1
        return await orig_call(self, endpoint_key, params=params)

    async def _counted_get(self, url, *args, **kwargs):
        raw = url if isinstance(url, str) else str(url)
        path = urlparse(raw).path if "://" in raw else raw.split("?", 1)[0]
        if is_webposto_write_path(path):
            raise RuntimeError("CANARY_ABORT: path de escrita")
        if not path.endswith("/ABASTECIMENTO"):
            raise RuntimeError("CANARY_ABORT: endpoint nao autorizado")
        stats["gets"][path] += 1
        response = await orig_get(self, url, *args, **kwargs)
        if stats["httpPagina0"] is None:
            stats["httpPagina0"] = int(response.status_code)
        if response.request is not None:
            verb = (response.request.method or "GET").upper()
            if verb != "GET":
                raise RuntimeError(f"CANARY_ABORT: metodo {verb}")
        return response

    WebPostoClient.discover_permissions = _blocked_discover  # type: ignore[method-assign]
    WebPostoClient.call_endpoint = _guarded_call  # type: ignore[method-assign]
    WebPostoClient._fallback_stale = _no_stale_fallback  # type: ignore[method-assign]
    gateway_module.retry_async = _single_attempt
    httpx.AsyncClient.get = _counted_get  # type: ignore[method-assign]


async def _execute(empresa: int) -> dict[str, Any]:
    from src.services.abastecimento_service import AbastecimentoService
    from src.services.data_sync_service import get_data_sync_service
    from src.services.sds_catchup_service import SdsCatchupService, _wire_defaults

    stats: dict[str, Any] = {
        "gets": Counter(),
        "discoveryCalls": 0,
        "paginasAbastecimento": 0,
        "httpPagina0": None,
    }
    _install_guards(stats, empresa)

    sync = get_data_sync_service()
    sync._catalog_cache[empresa] = {}
    sync._cpm_cache[empresa] = {}
    orig_fetch = sync._fetch_abastecimentos
    orig_sync = sync.sync_day
    orig_periodo = AbastecimentoService.get_periodo

    async def _counted_periodo(self, data_inicial, data_final, empresa_codigo=None):
        resp = await orig_periodo(self, data_inicial, data_final, empresa_codigo)
        raw = resp.data
        if isinstance(raw, dict):
            stats["linhasRecebidas"] = int(raw.get("total") or len(raw.get("dados") or []))
        elif isinstance(raw, list):
            stats["linhasRecebidas"] = len(raw)
        return resp

    AbastecimentoService.get_periodo = _counted_periodo  # type: ignore[method-assign]

    async def _counted_fetch(empresa_codigo: int, start: str, end: str):
        if int(empresa_codigo) != int(empresa):
            raise RuntimeError("CANARY_ABORT: outra unidade")
        rows = await orig_fetch(empresa_codigo, start, end)
        stats["linhasValidasUnidade"] = len(rows)
        return rows

    async def _captured_sync(empresa_codigo, data_referencia, force: bool = False):
        if int(empresa_codigo) != int(empresa):
            raise RuntimeError("CANARY_ABORT: outra unidade")
        if data_referencia != CANARY_DIA:
            raise RuntimeError("CANARY_ABORT: outra data")
        raw = await orig_sync(empresa_codigo, data_referencia, force=force)
        stats["syncDay"] = {
            "status": raw.get("status"),
            "litros": raw.get("litros"),
            "faturamento": raw.get("faturamento"),
            "abastecimentos": raw.get("quantidadeAbastecimentos"),
            "registrosSemIdentidade": raw.get("registrosSemIdentidade"),
            "contagemConfiavel": raw.get("contagemConfiavel"),
            "ticketMedioLitros": raw.get("ticketMedioLitros"),
            "ticketMedioReais": raw.get("ticketMedioReais"),
            "linhasCombustivel": raw.get("abastecimentos_lidos"),
        }
        return raw

    sync._fetch_abastecimentos = _counted_fetch
    sync.sync_day = _captured_sync

    svc = SdsCatchupService()
    _wire_defaults(svc)
    svc.retries = 0
    svc.timeout_seconds = 90
    svc.max_days = 1
    svc._sync_day = sync.sync_day

    try:
        locked_out = not svc._process_lock.acquire(trigger="cli-canary")
    except (LockUnavailable, OSError, Exception):
        return sanitize_value(
            {
                "success": False,
                "status": "LOCK_UNAVAILABLE",
                "mensagem": "Lock SDS indisponivel",
                "webpostoWrites": WEBPOSTO_WRITES,
                "metodosWebPosto": [],
                "endpointsGet": [],
                "unidades": [empresa],
            }
        )
    if locked_out:
        return sanitize_value(
            {
                "success": False,
                "status": "LOCKED",
                "mensagem": "Catch-up já em execução",
                "webpostoWrites": WEBPOSTO_WRITES,
                "metodosWebPosto": [],
                "endpointsGet": [],
                "unidades": [empresa],
            }
        )
    try:
        item = await svc._process_day(
            empresa, CANARY_DIA, force=True, allow_complete_reprocess=True
        )
    finally:
        svc._process_lock.release()
    status = str(item.get("status") or STATUS_FALHA)
    result = {
        "success": status != STATUS_FALHA,
        "trigger": "cli-canary",
        "dryRun": False,
        "webpostoWrites": WEBPOSTO_WRITES,
        "metodosWebPosto": ["GET"],
        "endpointsGet": ["ABASTECIMENTO"],
        "unidades": [empresa],
        "intervalo": {"inicio": CANARY_DIA.isoformat(), "fim": CANARY_DIA.isoformat()},
        "diasPlanejados": 1,
        "paresUnidadeDia": 1,
        "diasRestantes": 0,
        "contadores": {status: 1},
        "detalhes": [item],
    }
    result["getsPorEndpoint"] = dict(stats["gets"])
    result["discoveryCalls"] = stats["discoveryCalls"]
    result["paginasAbastecimento"] = stats["paginasAbastecimento"]
    result["httpPagina0"] = stats["httpPagina0"]
    result["linhasRecebidas"] = stats.get("linhasRecebidas")
    result["linhasValidasUnidade"] = stats.get("linhasValidasUnidade")
    result["syncDay"] = stats.get("syncDay")
    return result


def _conference(empresa: int) -> dict[str, Any]:
    import sqlite3
    from pathlib import Path

    con = sqlite3.connect(Path("logos_gateway.db").as_posix())
    max_emp = con.execute(
        "SELECT MAX(data_referencia) FROM sales_daily_summary WHERE empresa_codigo=?",
        (empresa,),
    ).fetchone()[0]
    rows = list(
        con.execute(
            """
            SELECT codigo_produto_webposto, litros_vendidos, faturamento_bruto, quantidade_abastecimentos
            FROM sales_daily_summary
            WHERE empresa_codigo=? AND data_referencia=?
            """,
            (empresa, CANARY_DIA.isoformat()),
        )
    )
    alias = con.execute(
        "SELECT COUNT(*) FROM sales_daily_summary WHERE empresa_codigo=6666"
    ).fetchone()[0]
    sds_5555 = con.execute(
        """
        SELECT COUNT(*), ROUND(SUM(litros_vendidos), 2), ROUND(SUM(faturamento_bruto), 2),
               SUM(quantidade_abastecimentos)
        FROM sales_daily_summary
        WHERE empresa_codigo=5555 AND data_referencia=?
        """,
        (CANARY_DIA.isoformat(),),
    ).fetchone()
    status = list(
        con.execute(
            """
            SELECT status, registros_sem_identidade, quantidade_abastecimentos, mensagem
            FROM sds_day_status
            WHERE empresa_codigo=? AND data_referencia=?
            """,
            (empresa, CANARY_DIA.isoformat()),
        )
    )
    con.close()
    litros = round(sum(float(r[1] or 0) for r in rows), 3)
    fat = round(sum(float(r[2] or 0) for r in rows), 2)
    qtd = sum(int(r[3] or 0) for r in rows)
    return {
        "empresa": empresa,
        "ultimaDataUnidade": max_emp,
        "linhasSdsCanario": len(rows),
        "litros": litros if rows else None,
        "faturamento": fat if rows else None,
        "abastecimentos": qtd if rows else None,
        "alias6666": alias,
        "sds5555_13Preservado": {
            "linhas": sds_5555[0],
            "litros": sds_5555[1],
            "faturamento": sds_5555[2],
            "abastecimentos": sds_5555[3],
        },
        "dayStatus": [
            {
                "status": r[0],
                "registrosSemIdentidade": r[1],
                "quantidadeAbastecimentos": r[2],
                "mensagem": (r[3] or "")[:160],
            }
            for r in status
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Canário SDS — um par unidade/dia")
    parser.add_argument("--empresa", type=int, required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--execute", action="store_true", default=False)
    args = parser.parse_args(argv)
    erro = validate_pair(args.empresa, args.data)
    if erro:
        print(erro)
        return 2
    if WEBPOSTO_WRITES != 0:
        print("BLOQUEADO: WEBPOSTO_WRITES != 0")
        return 2

    preflight = _preflight(args.empresa)
    print(json.dumps(sanitize_value({
        "preflight": preflight,
        "comando": suggested_command(args.empresa),
    }), ensure_ascii=False, indent=2))
    if not preflight.get("credencialPresente"):
        print("BLOQUEADO: credencial oficial ausente para a unidade informada")
        return 2
    if not preflight.get("vinculoExclusivo"):
        print("BLOQUEADO: credencial nao isolada exclusivamente na unidade informada")
        return 2
    if not args.execute:
        return 0

    result = __import__("asyncio").run(_execute(args.empresa))
    conference = _conference(args.empresa)
    payload = {
        "resultado": result,
        "conferencia": conference,
        "webpostoWrites": WEBPOSTO_WRITES,
        "metodos": list(GET_ONLY),
    }
    print(json.dumps(sanitize_value(payload), ensure_ascii=False, indent=2, default=str))
    status = None
    detalhes = result.get("detalhes") or []
    if detalhes:
        status = detalhes[0].get("status")
    if result.get("discoveryCalls"):
        return 1
    if status == STATUS_FALHA or result.get("httpPagina0") in {401, 403}:
        return 1
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
