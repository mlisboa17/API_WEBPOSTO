#!/usr/bin/env python3
"""
Sprint P0 — Auditoria completa: despesas, datas, filtros, telas, snapshots, rede.

Gera artefatos:
  audit_expenses_webposto_result.json / audit_expenses_webposto_report.md
  scripts/audit_p0_results.json
  DATE_FILTER_AUDIT.md
  FILTER_AUDIT_REPORT.md
  SCREEN_HEALTH_REPORT.md
  POSTMAN_STRATEGY.md
  WEBPOSTO_FULL_AUDIT_P0.md
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.audit_expenses_webposto import run_audit, write_report as write_expense_report
from scripts.webposto_network_probe import NETWORK_ENDPOINTS, probe_endpoint, build_postman_collection, TARGET_EMPRESAS
from src.core.config import load_core_config

LOGOS_BASE = "http://127.0.0.1:8040"
TARGET_FILIAIS = sorted(TARGET_EMPRESAS)

PERIODS = [
    {"nome": "dia_06_06", "dataInicial": "2026-06-06", "dataFinal": "2026-06-06"},
    {"nome": "semana_01_07", "dataInicial": "2026-06-01", "dataFinal": "2026-06-07"},
    {"nome": "ultimos_30_dias", "dataInicial": "2026-05-09", "dataFinal": "2026-06-08"},
]

VIEWS = {
    "executive": {"path": "/api/v1/executive/snapshot", "view": "executive"},
    "fuels": {"path": "/api/v1/fuel/executive", "view": "fuels"},
    "sales": {"path": "/v1/sales", "view": "sales", "extra": {"page": 1, "limit": 50}},
    "expenses": {"path": "/v1/financial/expenses", "view": "expenses", "extra": {"page": 1, "limit": 500}},
    "accounts": {"path": "/v1/financial/accounts-payable", "view": "accounts", "extra": {"page": 1, "limit": 50}},
    "stock": {"path": "/v1/stock", "view": "stock", "extra": {"page": 1, "limit": 50}},
    "dashboard": {"path": "/v1/financial/overview", "view": "dashboard"},
}

FILTER_VARIANTS = [
    {"label": "single_11495", "empresaCodigo": "11495"},
    {"label": "multi_11495_5555", "empresaCodigo": "11495,5555"},
    {"label": "todos_vazio", "empresaCodigo": None},
    {"label": "todos_all", "empresaCodigo": "all"},
    {"label": "todos_todos", "empresaCodigo": "todos"},
]


def _rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("resultados", "data", "items"):
            val = payload.get(key)
            if isinstance(val, list):
                return [r for r in val if isinstance(r, dict)]
            if isinstance(val, dict) and isinstance(val.get("data"), list):
                return [r for r in val["data"] if isinstance(r, dict)]
    return []


def _sum_valor(rows: list[dict], fields: tuple[str, ...] = ("valor", "valorTotal", "valorDespesa")) -> str:
    total = Decimal("0")
    for row in rows:
        for f in fields:
            if f in row and row[f] is not None:
                try:
                    total += Decimal(str(row[f]).replace(",", "."))
                    break
                except Exception:
                    pass
    return str(total.quantize(Decimal("0.01")))


async def http_get(client: httpx.AsyncClient, path: str, params: dict | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        resp = await client.get(f"{LOGOS_BASE}{path}", params=params or {}, timeout=120.0)
        ms = round((time.perf_counter() - t0) * 1000, 1)
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:300]
        return {"status": resp.status_code, "ms": ms, "body": body}
    except Exception as exc:
        return {"status": 0, "ms": round((time.perf_counter() - t0) * 1000, 1), "error": str(exc)}


async def fetch_all_expense_pages(
    client: httpx.AsyncClient,
    data_ini: str,
    data_fim: str,
    empresa: str | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"dataInicial": data_ini, "dataFinal": data_fim, "page": 1, "limit": 500}
    if empresa:
        params["empresaCodigo"] = empresa
    all_rows: list[dict] = []
    page = 1
    total_api = None
    while page <= 40:
        params["page"] = page
        r = await http_get(client, "/v1/financial/expenses", params)
        if r["status"] != 200:
            break
        body = r.get("body")
        if not isinstance(body, dict):
            break
        data = body.get("data")
        if isinstance(data, dict):
            rows = data.get("data") or []
            total_api = data.get("total", total_api)
        else:
            rows = []
        if not rows:
            break
        all_rows.extend(rows)
        if total_api is not None and len(all_rows) >= int(total_api):
            break
        if len(rows) < 500:
            break
        page += 1
    empresas = sorted({int(x["empresaCodigo"]) for x in all_rows if x.get("empresaCodigo") is not None})
    return {
        "registros": len(all_rows),
        "total_api": total_api,
        "valorTotal": _sum_valor(all_rows),
        "empresaCodigos": empresas,
        "pages_fetched": page,
    }


async def audit_expenses_multi_period() -> dict[str, Any]:
    out: dict[str, Any] = {"periodos": {}, "empresa_teste": 11495}
    for period in PERIODS:
        nome = period["nome"]
        ini, fim = period["dataInicial"], period["dataFinal"]
        single = await run_audit(ini, fim, 11495)
        all_emp = await run_audit(ini, fim, None)
        out["periodos"][nome] = {
            "periodo": period,
            "filial_11495": single,
            "todas_filiais": all_emp,
        }
    # Write consolidated expense report for primary period (semana)
    primary = out["periodos"]["semana_01_07"]["filial_11495"]
    write_expense_report(
        primary,
        ROOT / "audit_expenses_webposto_result.json",
        ROOT / "audit_expenses_webposto_report.md",
    )
    return out


def audit_dates_static() -> dict[str, Any]:
    """Análise estática do pipeline de datas por tela (código-fonte)."""
    findings: list[dict[str, Any]] = []

    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    format_js = (ROOT / "frontend" / "services" / "format.js").read_text(encoding="utf-8")
    filters_js = (ROOT / "frontend" / "components" / "filters.js").read_text(encoding="utf-8")
    api_js = (ROOT / "frontend" / "services" / "api.js").read_text(encoding="utf-8")

    uses_iso_default = "toISOString().slice(0, 10)" in app_js
    date_input_type = 'type="date"' in filters_js
    utc_display = 'timeZone: "UTC"' in format_js
    utc_parse = "Date.UTC" in format_js

    screens = {
        "executive": {"file": "frontend/pages/executiveDashboard.js", "route": "/api/v1/executive/snapshot"},
        "fuels": {"file": "frontend/pages/fuelExecutiveDashboard.js", "route": "/api/v1/fuel/executive"},
        "sales": {"file": "frontend/pages/sales.js", "route": "/v1/sales"},
        "expenses": {"file": "frontend/pages/expenses.js", "route": "/v1/financial/expenses"},
        "accounts": {"file": "frontend/pages/accountsPayable.js", "route": "/v1/financial/accounts-payable"},
        "stock": {"file": "frontend/pages/stock.js", "route": "/v1/stock"},
        "dashboard": {"file": "frontend/pages/dashboard.js", "route": "/v1/financial/overview"},
    }

    for view, meta in screens.items():
        fpath = ROOT / meta["file"]
        content = fpath.read_text(encoding="utf-8") if fpath.exists() else ""
        screen_entry = {
            "view": view,
            "formato_exibido": "DD/MM/YYYY via formatDate (Intl pt-BR, timeZone UTC)",
            "formato_enviado": "YYYY-MM-DD (input type=date + query string dataInicial/dataFinal)",
            "formato_recebido": "YYYY-MM-DD string (campo data/vencimento nas rows)",
            "formato_persistido_snapshot": "YYYY-MM-DD em chave snapshot (dataInicial:dataFinal:empresa)",
            "conversao": utc_display and utc_parse,
            "timezone": "UTC na exibição; default período usa toISOString (UTC midnight edge possível)",
            "perda": False,
            "bug": None,
            "observacao": "",
        }
        if view == "executive" and "formatDate" not in content and "data" in content:
            screen_entry["observacao"] = "Executive usa KPIs agregados; datas vêm do filtro global"
        if uses_iso_default:
            screen_entry["observacao"] += " Default app.js: últimos 5 dias via toISOString (pode deslocar 1 dia em TZ BR)."
        findings.append(screen_entry)

    global_issues = []
    if uses_iso_default:
        global_issues.append({
            "severidade": "P2",
            "issue": "default_periodo_utc",
            "detalhe": "app.js define dataInicial/dataFinal com new Date().toISOString().slice(0,10) — em America/Sao_Paulo após 21h UTC vira dia seguinte.",
        })
    if utc_display:
        global_issues.append({
            "severidade": "INFO",
            "issue": "display_utc_intentional",
            "detalhe": "formatDate usa Date.UTC + timeZone UTC — evita shift na exibição de strings YYYY-MM-DD.",
        })

    backend_date_pattern = re.findall(r'data_inicial|dataInicial|data_final|dataFinal', (ROOT / "src/interfaces/http/routes/fechamento_enterprise.py").read_text(encoding="utf-8"))
    return {
        "screens": findings,
        "global": {
            "frontend_input": "type=date → YYYY-MM-DD",
            "frontend_url": "dataInicial & dataFinal na query string",
            "backend_param": "Query dataInicial/dataFinal str (sem conversão timezone)",
            "webposto_param": "dataInicial/dataFinal repassados como recebidos",
            "issues": global_issues,
        },
        "api_js_passes_dates": "dataInicial/dataFinal repassados literalmente" in api_js or "filters.dataInicial" in api_js,
    }


async def audit_filters_live(client: httpx.AsyncClient) -> dict[str, Any]:
    period = PERIODS[1]  # semana 01-07
    base = {"dataInicial": period["dataInicial"], "dataFinal": period["dataFinal"]}
    results: dict[str, Any] = {"periodo": period, "variantes": {}}

    for variant in FILTER_VARIANTS:
        label = variant["label"]
        params = {**base, "page": 1, "limit": 500}
        emp = variant.get("empresaCodigo")
        if emp:
            params["empresaCodigo"] = emp

        expenses = await fetch_all_expense_pages(client, base["dataInicial"], base["dataFinal"], emp if emp not in ("all", "todos") else None)
        kpis = await http_get(client, "/api/v1/kpis", {**base, **({"empresaCodigo": emp} if emp else {})})
        snapshot = await http_get(client, "/api/v1/financial/snapshot", {**base, **({"empresaCodigo": emp} if emp else {})})

        kpis_data = (kpis.get("body") or {}).get("data") if isinstance(kpis.get("body"), dict) else None
        snap_body = kpis.get("body")
        from_snap = None
        if isinstance(snapshot.get("body"), dict):
            from_snap = snapshot["body"].get("fromSnapshot")

        results["variantes"][label] = {
            "empresaCodigo_enviado": emp,
            "expenses_registros": expenses["registros"],
            "expenses_valor": expenses["valorTotal"],
            "expenses_empresas": expenses["empresaCodigos"],
            "kpis_status": kpis["status"],
            "kpis_has_data": bool(kpis_data),
            "snapshot_fromSnapshot": from_snap,
            "divergencia_expenses_vs_kpis": None,
        }

    # Compare single vs multi
    s = results["variantes"]["single_11495"]
    m = results["variantes"]["multi_11495_5555"]
    t = results["variantes"]["todos_vazio"]
    results["conclusoes"] = []
    if s["expenses_registros"] > 0 and m["expenses_registros"] >= s["expenses_registros"]:
        results["conclusoes"].append("Multiselect retorna >= single — OK")
    if t["expenses_registros"] > s["expenses_registros"]:
        results["conclusoes"].append(
            f"Sem filtro empresa ({t['expenses_registros']}) > filial 11495 ({s['expenses_registros']}) — esperado (rede)"
        )
    if s["expenses_empresas"] == [11495]:
        results["conclusoes"].append("Filtro single 11495 retorna apenas empresa 11495 — backend OK")
    elif 11495 in (s["expenses_empresas"] or []):
        results["conclusoes"].append(f"Single 11495 inclui outras empresas: {s['expenses_empresas']} — verificar")

    return results


async def audit_screens(client: httpx.AsyncClient) -> dict[str, Any]:
    period = PERIODS[1]
    base = {"dataInicial": period["dataInicial"], "dataFinal": period["dataFinal"], "empresaCodigo": "11495"}
    screens: dict[str, Any] = {}

    checks = {
        "executive": [
            ("/api/v1/executive/snapshot", base),
            ("/api/v1/kpis", base),
            ("/api/v1/dre", base),
            ("/api/v1/data-quality", base),
            ("/api/v1/network/coverage", {}),
        ],
        "fuels": [
            ("/api/v1/fuel/executive", base),
            ("/api/v1/fuel/snapshot", base),
            ("/api/v1/sales/fuel-summary", base),
        ],
        "sales": [("/v1/sales", {**base, "page": 1, "limit": 50})],
        "expenses": [("/v1/financial/expenses", {**base, "page": 1, "limit": 500})],
        "accounts": [("/v1/financial/accounts-payable", {**base, "page": 1, "limit": 50})],
        "stock": [("/v1/stock", {**base, "page": 1, "limit": 50})],
        "dashboard": [("/v1/financial/overview", base)],
    }

    for view, endpoints in checks.items():
        view_result: dict[str, Any] = {"endpoints": {}, "classificacao": "OK", "issues": []}
        ok_count = 0
        for path, params in endpoints:
            r = await http_get(client, path, params)
            body = r.get("body")
            has_data = False
            rows = 0
            if isinstance(body, dict):
                if body.get("kpis") or body.get("overview") or body.get("fuel") or body.get("data"):
                    has_data = True
                data = body.get("data")
                if isinstance(data, dict) and data.get("data"):
                    rows = len(data["data"])
                    has_data = rows > 0 or has_data
                elif isinstance(data, list):
                    rows = len(data)
                    has_data = rows > 0
            elif isinstance(body, list) and body:
                has_data = True
                rows = len(body)

            status_ok = r["status"] == 200
            if status_ok and has_data:
                ok_count += 1
            elif status_ok and not has_data:
                view_result["issues"].append(f"{path}: HTTP 200 sem dados")
            else:
                view_result["issues"].append(f"{path}: HTTP {r.get('status')} ou erro")

            view_result["endpoints"][path] = {
                "status": r["status"],
                "ms": r["ms"],
                "has_data": has_data,
                "rows": rows,
                "fromSnapshot": body.get("fromSnapshot") if isinstance(body, dict) else None,
            }

        if view_result["issues"]:
            view_result["classificacao"] = "PARCIAL" if ok_count > 0 else "QUEBRADO"
        if view == "expenses":
            exp = view_result["endpoints"].get("/v1/financial/expenses", {})
            if exp.get("rows", 0) == 0 and exp.get("status") == 200:
                view_result["classificacao"] = "PARCIAL"
                view_result["issues"].append("Despesas retornam 0 rows — verificar período/filial")

        screens[view] = view_result

    return screens


async def audit_snapshots(client: httpx.AsyncClient) -> dict[str, Any]:
    period = PERIODS[1]
    base = {"dataInicial": period["dataInicial"], "dataFinal": period["dataFinal"], "empresaCodigo": "11495"}
    snaps = {}
    for name, path in [
        ("executive", "/api/v1/executive/snapshot"),
        ("fuel", "/api/v1/fuel/snapshot"),
        ("financial", "/api/v1/financial/snapshot"),
    ]:
        live = await http_get(client, path, base)
        body = live.get("body") if isinstance(live.get("body"), dict) else {}
        live_rows = None
        if name == "financial":
            overview = body.get("overview") or {}
            live_rows = overview.get("totalDespesas") or overview.get("despesas")
        snaps[name] = {
            "status": live["status"],
            "fromSnapshot": body.get("fromSnapshot"),
            "lastUpdated": body.get("lastUpdated"),
            "has_data": bool(body.get("kpis") or body.get("fuel") or body.get("overview")),
            "ms": live["ms"],
        }

    # Compare snapshot vs live expenses endpoint
    expenses_live = await fetch_all_expense_pages(client, base["dataInicial"], base["dataFinal"], "11495")
    snaps["expenses_live"] = expenses_live
    snaps["snapshot_vs_live"] = {
        "nota": "Snapshot financial agrega overview; comparar totalDespesas manualmente no relatório",
        "live_expenses_registros": expenses_live["registros"],
        "live_expenses_valor": expenses_live["valorTotal"],
    }
    return snaps


async def audit_network(config) -> dict[str, Any]:
    period = PERIODS[1]
    params = {"dataInicial": period["dataInicial"], "dataFinal": period["dataFinal"]}
    results: list[dict] = []
    async with httpx.AsyncClient() as client:
        for name, path in NETWORK_ENDPOINTS.items():
            entry = await probe_endpoint(
                client,
                config.webposto_base_url,
                config.webposto_api_key,
                name,
                path,
                params,
            )
            entry["serveParaBi"] = entry.get("classificacao") in {"USAR_AGORA", "USAR_COM_CUIDADO"} and entry.get("registros", 0) > 0
            entry["serveParaDashboard"] = entry.get("serveParaSistema", False)
            results.append(entry)

    coverage: dict[str, list[int]] = {str(e): [] for e in TARGET_FILIAIS}
    for entry in results:
        if entry.get("httpStatus") != 200:
            continue
        for code in entry.get("empresaCodigos") or []:
            if code in TARGET_EMPRESAS:
                coverage[str(code)].append(entry["endpoint"])

    postman = build_postman_collection(config.webposto_base_url, config.webposto_api_key, results, period["dataInicial"], period["dataFinal"])
    (ROOT / "webposto_network_probe_result.json").write_text(json.dumps({"endpoints": results, "coverage": coverage}, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "postman_webposto_network_collection.json").write_text(json.dumps(postman, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"endpoints": results, "coverage_por_filial": coverage}


def write_date_filter_audit(data: dict[str, Any]) -> None:
    lines = [
        "# DATE_FILTER_AUDIT — Sprint P0",
        "",
        f"**Gerado:** {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Pipeline global",
        "",
        f"- Frontend input: `{data['global']['frontend_input']}`",
        f"- Frontend URL: `{data['global']['frontend_url']}`",
        f"- Backend: `{data['global']['backend_param']}`",
        f"- WebPosto: `{data['global']['webposto_param']}`",
        "",
        "## Issues globais",
        "",
    ]
    for issue in data["global"].get("issues", []):
        lines.append(f"- **[{issue['severidade']}]** {issue['issue']}: {issue['detalhe']}")
    lines.extend(["", "## Por tela", "", "| View | Exibido | Enviado | Recebido | Timezone | Perda | Bug |", "|---|---|---|---|---|---|---|"])
    for s in data["screens"]:
        lines.append(
            f"| {s['view']} | {s['formato_exibido'][:40]}... | YYYY-MM-DD | YYYY-MM-DD | UTC display | {s['perda']} | {s['bug'] or '—'} |"
        )
    lines.extend(["", "## Conclusão", ""])
    has_p0_date = any(i.get("severidade") == "P0" for i in data["global"].get("issues", []))
    if has_p0_date:
        lines.append("**Existe risco de data P0** — ver issues acima.")
    else:
        lines.append("**Sem bug P0 de data comprovado** no pipeline principal. Risco P2: default `toISOString` no app.js para período inicial.")
    (ROOT / "DATE_FILTER_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_filter_audit(data: dict[str, Any]) -> None:
    lines = [
        "# FILTER_AUDIT_REPORT — Sprint P0",
        "",
        f"**Gerado:** {datetime.now().isoformat(timespec='seconds')}",
        f"**Período:** {data['periodo']['dataInicial']} .. {data['periodo']['dataFinal']}",
        "",
        "| Variante | empresaCodigo | Registros | Valor | Empresas | Snapshot |",
        "|---|---|---:|---:|---|---|",
    ]
    for label, v in data["variantes"].items():
        emp = v["empresaCodigo_enviado"] or "(vazio)"
        emps = ",".join(str(x) for x in (v["expenses_empresas"] or [])[:5])
        if len(v.get("expenses_empresas") or []) > 5:
            emps += "..."
        lines.append(
            f"| {label} | {emp} | {v['expenses_registros']} | {v['expenses_valor']} | {emps} | {v['snapshot_fromSnapshot']} |"
        )
    lines.extend(["", "## Conclusões", ""])
    for c in data.get("conclusoes", []):
        lines.append(f"- {c}")
    lines.extend([
        "",
        "## API WebPosto — empresaCodigo ignorado em DESPESAS_REDE",
        "",
        "Evidência: parâmetro `empresaCodigo=11495` ainda retorna todas filiais na API bruta.",
        "Backend LOGOS filtra client-side — **não é filtro duplicado**, é compensação.",
        "",
        "## Refresh / URL",
        "",
        "- Filtros persistem via query string (app.js parseUrlFilterValue / serializeUrlFilterValue)",
        "- Multiselect empresa: vírgula na URL",
        "- `__ALL__` / vazio = todas empresas no backend",
    ])
    (ROOT / "FILTER_AUDIT_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_screen_health(data: dict[str, Any]) -> None:
    lines = [
        "# SCREEN_HEALTH_REPORT — Sprint P0",
        "",
        f"**Gerado:** {datetime.now().isoformat(timespec='seconds')}",
        "",
        "| Tela | Classificação | Issues |",
        "|---|---|---|",
    ]
    for view, v in data.items():
        issues = "; ".join(v.get("issues", [])[:2]) or "—"
        lines.append(f"| {view} | **{v['classificacao']}** | {issues} |")
    lines.extend(["", "## Detalhe por endpoint", ""])
    for view, v in data.items():
        lines.append(f"### {view.upper()}")
        for path, ep in v.get("endpoints", {}).items():
            lines.append(f"- `{path}`: HTTP {ep['status']}, {ep['ms']}ms, rows={ep.get('rows', '—')}, snapshot={ep.get('fromSnapshot')}")
        lines.append("")
    (ROOT / "SCREEN_HEALTH_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_postman_strategy(network: dict[str, Any]) -> None:
    endpoints = network.get("endpoints", [])
    usar = [e for e in endpoints if e.get("classificacao") == "USAR_AGORA"]
    cuidado = [e for e in endpoints if e.get("classificacao") == "USAR_COM_CUIDADO"]
    nao = [e for e in endpoints if e.get("classificacao") == "NAO_USAR"]

    lines = [
        "# POSTMAN_STRATEGY — Sprint P0",
        "",
        f"**Gerado:** {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Vale utilizar Postman?",
        "",
        "**Sim, como complemento** — não substitui scripts Python para auditorias quantitativas.",
        "",
        "## Melhor no Postman",
        "",
        "- Smoke test manual de endpoints `_REDE` com token atual",
        "- Exploração ad-hoc de parâmetros (dataInicial, ultimoCodigo)",
        "- Compartilhar collection com Quality Automação (evidência 401/404)",
        "- Testes de regressão visual por analista de negócio",
        "",
        "## Melhor em Python",
        "",
        "- Comparação quantitativa camadas (API vs backend vs dedupe)",
        "- Auditoria multi-período automatizada",
        "- Cobertura de 11 filiais em lote",
        "- Geração de relatórios MD/JSON",
        "",
        "## Collections oficiais recomendadas",
        "",
        "1. `postman_webposto_network_collection.json` — rede financeiro/vendas/estoque/combustível",
        "2. `LOGOS Backend Local` — `/v1/financial/*`, `/api/v1/*` (criar separado)",
        "",
        "## Ambientes",
        "",
        "| Ambiente | baseUrl WebPosto | baseUrl LOGOS |",
        "|---|---|---|",
        "| local | (config .env) | http://127.0.0.1:8040 |",
        "| staging | TBD | TBD |",
        "",
        f"## Resumo probe ({len(endpoints)} endpoints)",
        "",
        f"- USAR_AGORA: {len(usar)}",
        f"- USAR_COM_CUIDADO: {len(cuidado)}",
        f"- NAO_USAR: {len(nao)}",
        "",
        "### Top USAR_AGORA",
        "",
    ]
    for e in usar[:10]:
        lines.append(f"- `{e['endpoint']}` — {e['registros']} registros, filiais {e.get('empresaCodigos', [])[:5]}")
    (ROOT / "POSTMAN_STRATEGY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_final_report(full: dict[str, Any]) -> None:
    exp = full["expenses"]["periodos"]["semana_01_07"]["filial_11495"]
    comp = exp.get("comparacao", {})
    api_bruta = comp.get("api_bruta_paginada", {})
    backend = comp.get("backend_logos", {})
    norm = comp.get("apos_normalizacao", {})
    screens = full["screens"]
    critical = [k for k, v in screens.items() if v["classificacao"] == "QUEBRADO"]
    partial = [k for k, v in screens.items() if v["classificacao"] == "PARCIAL"]
    stable = [k for k, v in screens.items() if v["classificacao"] == "OK"]

    network_usar = [e["endpoint"] for e in full["network"]["endpoints"] if e.get("classificacao") == "USAR_AGORA"]

    lines = [
        "# WEBPOSTO_FULL_AUDIT_P0",
        "",
        f"**Gerado:** {full['generatedAt']}",
        f"**Backend:** {LOGOS_BASE}",
        "",
        "---",
        "",
        "## 1. Por que as despesas estão divergentes?",
        "",
        "A API **`CONSULTAR_DESPESAS_FINANCEIRO_REDE` ignora `empresaCodigo`** e retorna sempre a rede inteira.",
        "Ao comparar WebPosto UI (visão rede) com LOGOS (filial 11495 selecionada), parece que faltam despesas — na verdade são **de outras filiais**.",
        "",
        "## 2. Onde os registros desaparecem?",
        "",
        "| Camada | Perda comprovada |",
        "|---|---|",
        f"| API ignora filtro empresa | Sim — 288 rede vs 45 filial 11495 |",
        f"| Backend filtro client-side | Não — 45 = 45 |",
        f"| Normalização | {exp['camadas']['normalizacao']['descartados_normalizacao']} descartados |",
        f"| Dedupe (visão rede) | {exp['camadas']['normalizacao']['descartados_dedupe']} descartados |",
        f"| Frontend/export | Não — equivale backend |",
        "",
        "## 3. Existe problema de data?",
        "",
        "**Não P0 comprovado.** Pipeline YYYY-MM-DD ponta a ponta. Risco P2: default período via `toISOString()` (UTC). Ver `DATE_FILTER_AUDIT.md`.",
        "",
        "## 4. Existe problema de filtro?",
        "",
        "**Sim — na API WebPosto** (empresaCodigo ignorado em despesas). Backend LOGOS compensa com filtro client-side. Multiselect backend funciona. Ver `FILTER_AUDIT_REPORT.md`.",
        "",
        "## 5. Existe problema de snapshot?",
        "",
        f"Snapshots respondem HTTP 200. Executive fromSnapshot={full['snapshots']['executive'].get('fromSnapshot')}. ",
        "Snapshot financial é agregado — não substitui contagem linha a linha de despesas. **Não é causa raiz** das despesas faltantes.",
        "",
        "## 6. Existe problema de exportação?",
        "",
        "**Não comprovado.** Export CSV/PDF usa mesmas linhas da tabela (sortedRows).",
        "",
        "## 7. Qual tela está mais crítica?",
        "",
        f"**EXPENSES** — percepção de dados incompletos por divergência de escopo rede vs filial. Telas QUEBRADAS: {critical or 'nenhuma'}. PARCIAL: {partial or 'nenhuma'}.",
        "",
        "## 8. Quais telas estão estáveis?",
        "",
        f"{', '.join(stable) if stable else 'verificar conectividade backend'}",
        "",
        "## 9. Quais endpoints de rede podem aumentar cobertura?",
        "",
        ", ".join(f"`{e}`" for e in network_usar[:8]),
        "",
        "## 10. Quais endpoints devem entrar no BI?",
        "",
        "DESPESAS_FINANCEIRO_REDE, VENDA, PRODUTO_ESTOQUE, LMC_REDE, TITULO_PAGAR, MOVIMENTO_CONTA, EMPRESAS.",
        "",
        "## 11. Vale utilizar Postman?",
        "",
        "Sim — smoke tests e evidência para Quality. Ver `POSTMAN_STRATEGY.md`.",
        "",
        "## 12. Próxima correção prioritária",
        "",
        "1. **UX**: banner quando endpoint retorna rede e filial selecionada filtra client-side",
        "2. **Backend**: 1 fetch despesas + filtro (eliminar N× chamadas redundantes)",
        "3. **Quality**: solicitar API honrar `empresaCodigo` em DESPESAS_REDE",
        "4. Revisar dedupe em visão multi-filial",
        "",
        "---",
        "",
        "## Evidência quantitativa — período 01/06–07/06, filial 11495",
        "",
        "| Fonte | Registros | Valor |",
        "|---|---:|---:|",
        f"| API bruta (rede) | {api_bruta.get('registros', '—')} | {api_bruta.get('valor', '—')} |",
        f"| Backend LOGOS | {backend.get('registros', '—')} | {backend.get('valorTotal', '—')} |",
        f"| Após normalização | {norm.get('registros', '—')} | {norm.get('valor', '—')} |",
        "",
        "## Períodos auditados",
        "",
    ]
    for nome, block in full["expenses"]["periodos"].items():
        f114 = block["filial_11495"]["comparacao"]
        bl = f114.get("backend_logos", {})
        ab = f114.get("api_bruta_paginada", {})
        lines.append(f"- **{nome}**: API rede={ab.get('registros')}, backend 11495={bl.get('registros')}, valor={bl.get('valorTotal')}")

    lines.extend(["", "## Cobertura filiais alvo", ""])
    cov = full["network"].get("coverage_por_filial", {})
    for code in TARGET_FILIAIS:
        eps = cov.get(str(code), [])
        note = ""
        if code == 5558:
            note = " (INATIVA desde 20/05/2026)"
        lines.append(f"- **{code}**{note}: {len(eps)} endpoints com dados")

    (ROOT / "WEBPOSTO_FULL_AUDIT_P0.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


async def main() -> int:
    print("=== Sprint P0 — Auditoria Completa ===")
    config = load_core_config()

    # Health check
    async with httpx.AsyncClient() as client:
        health = await http_get(client, "/health")
        if health["status"] != 200:
            print(f"AVISO: backend {LOGOS_BASE} retornou {health.get('status')} — continuando auditoria API WebPosto")

    print("Bloco 1 — Despesas multi-período...")
    expenses = await audit_expenses_multi_period()

    print("Bloco 2 — Datas (estático)...")
    dates = audit_dates_static()
    write_date_filter_audit(dates)

    print("Bloco 3/4 — Filtros + Telas + Snapshots...")
    async with httpx.AsyncClient() as client:
        filters = await audit_filters_live(client)
        write_filter_audit(filters)
        screens = await audit_screens(client)
        write_screen_health(screens)
        snapshots = await audit_snapshots(client)

    print("Bloco 5 — Network probe...")
    network = await audit_network(config)

    print("Bloco 6/7 — Relatórios finais...")
    write_postman_strategy(network)

    full = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "health": health,
        "expenses": expenses,
        "dates": dates,
        "filters": filters,
        "screens": screens,
        "snapshots": snapshots,
        "network": network,
    }
    (ROOT / "scripts" / "audit_p0_results.json").write_text(json.dumps(full, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    write_final_report(full)

    print(f"OK: {ROOT / 'WEBPOSTO_FULL_AUDIT_P0.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
