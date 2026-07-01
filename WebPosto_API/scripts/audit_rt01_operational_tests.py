#!/usr/bin/env python3
"""RT-01 — Testes reais operacionais (read-only, escopo RT-01B MANTER)."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PERIOD = "dataInicial=2026-06-01&dataFinal=2026-06-07"
BASE_HTTP = "http://127.0.0.1:8050"
OUT_JSON = ROOT / "scripts" / "rt01_test_results.json"


def probe_http(path: str, timeout: float = 3.0) -> dict[str, Any]:
    url = f"{BASE_HTTP}{path}"
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read()
            elapsed = round(time.perf_counter() - t0, 2)
            try:
                parsed = json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                parsed = None
            return {
                "status": resp.status,
                "elapsed_s": elapsed,
                "ok": 200 <= resp.status < 400,
                "json": parsed,
                "bytes": len(body),
            }
    except urllib.error.HTTPError as ex:
        return {
            "status": ex.code,
            "elapsed_s": round(time.perf_counter() - t0, 2),
            "ok": False,
            "error": ex.reason,
        }
    except Exception as ex:
        return {
            "status": 0,
            "elapsed_s": round(time.perf_counter() - t0, 2),
            "ok": False,
            "error": type(ex).__name__ if "timed out" not in str(ex).lower() else "timeout",
        }


def has_path(obj: Any, *keys: str) -> bool:
    cur = obj
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return False
        cur = cur[k]
    return cur is not None


def non_empty_list(obj: Any, *keys: str) -> bool:
    cur = obj
    for k in keys:
        if not isinstance(cur, dict):
            return False
        cur = cur.get(k)
    return isinstance(cur, list) and len(cur) > 0


def run_testclient() -> tuple[list[dict], bool]:
    from fastapi.testclient import TestClient
    from src.interfaces.http.app import create_app

    client = TestClient(create_app())
    rows: list[dict] = []

    def get(path: str, timeout: float = 35.0) -> dict:
        t0 = time.perf_counter()
        try:
            r = client.get(path, timeout=timeout)
            elapsed = round(time.perf_counter() - t0, 2)
            ct = r.headers.get("content-type", "")
            body = r.json() if "json" in ct else None
            return {"status": r.status_code, "elapsed_s": elapsed, "ok": r.status_code < 400, "json": body}
        except Exception as ex:
            return {
                "status": 0,
                "elapsed_s": round(time.perf_counter() - t0, 2),
                "ok": False,
                "error": str(ex)[:120],
            }

    def shell_ok(view: str) -> bool:
        r = get(f"/app/financial?view={view}", timeout=10)
        return r["ok"] and (r.get("bytes") or 0) > 1000 if "bytes" in r else r["ok"]

    tests = [
        {
            "id": "FIN-OPS",
            "tela": "F08.3 Operations Center",
            "view": "financial-operations-center",
            "path": f"/api/v1/financial/operations-center/cockpit?{PERIOD}",
            "perf_max_s": 3.0,
            "validate": lambda j: (
                has_path(j, "data", "executiveHealthScore") or has_path(j, "executiveHealthScore"),
                has_path(j, "data", "timeline") or has_path(j, "timeline"),
                has_path(j, "data", "alerts") or has_path(j, "alerts") is not False,
                has_path(j, "data", "circuitBreakers") or has_path(j, "circuitBreakers"),
                has_path(j, "data", "snapshotHealth") or has_path(j, "snapshotHealth"),
            ),
        },
        {
            "id": "FIN-INT",
            "tela": "F08.4 Intelligence Center",
            "view": "financial-intelligence",
            "path": f"/api/v1/financial/intelligence-center/cockpit?{PERIOD}",
            "perf_max_s": 3.0,
            "validate": lambda j: (
                j.get("success") is True or isinstance(j.get("data"), dict),
                isinstance((j.get("data") or j), dict),
            ),
        },
        {
            "id": "FIN-REC",
            "tela": "Receitas",
            "view": "dashboard",
            "path": f"/v1/financial/overview?{PERIOD}",
            "perf_max_s": 35.0,
            "validate": lambda j: (j.get("success") is True, isinstance(j.get("data"), (dict, list))),
        },
        {
            "id": "FIN-DESP",
            "tela": "Despesas",
            "view": "expenses",
            "path": f"/v1/financial/expenses?{PERIOD}&page=1&limit=10",
            "perf_max_s": 25.0,
            "validate": lambda j: (
                j.get("success") is True,
                isinstance(j.get("data"), (dict, list)) or isinstance(j.get("items"), list),
            ),
        },
        {
            "id": "PROD-PERF",
            "tela": "Produtos — Performance",
            "view": "non-fuel-products",
            "path": f"/api/v1/non-fuel-products/cockpit?{PERIOD}",
            "perf_max_s": 3.0,
            "validate": lambda j: j.get("success") is True or isinstance(j.get("data"), dict),
        },
        {
            "id": "PROD-OPP",
            "tela": "Produtos — Oportunidades",
            "view": "commercial-copilot",
            "path": f"/api/v1/commercial-copilot/cockpit?{PERIOD}",
            "perf_max_s": 3.0,
            "validate": lambda j: j.get("success") is True or isinstance(j.get("data"), dict),
        },
        {
            "id": "PROD-ACO",
            "tela": "Produtos — Ações Comerciais",
            "view": "commercial-execution",
            "path": f"/api/v1/commercial-execution/cockpit?{PERIOD}",
            "perf_max_s": 3.0,
            "validate": lambda j: j.get("success") is True or isinstance(j.get("data"), dict),
        },
        {
            "id": "PROD-RES",
            "tela": "Produtos — Resultados",
            "view": "commercial-learning",
            "path": f"/api/v1/commercial-learning/cockpit?{PERIOD}",
            "perf_max_s": 3.0,
            "validate": lambda j: j.get("success") is True or isinstance(j.get("data"), dict),
        },
        {
            "id": "COMB-VEND",
            "tela": "Combustíveis — Vendas",
            "view": "sales",
            "path": f"/v1/sales?{PERIOD}&page=1&limit=10",
            "perf_max_s": 25.0,
            "validate": lambda j: (
                j.get("success") is True,
                j.get("source") in (None, "snapshot", "live", "snapshot_fallback") or "data" in j,
            ),
        },
        {
            "id": "COMB-EST",
            "tela": "Combustíveis — Estoque",
            "view": "stock",
            "path": f"/v1/stock?{PERIOD}&page=1&limit=10",
            "perf_max_s": 35.0,
            "validate": lambda j: j.get("success") is True,
        },
        {
            "id": "COMB-LMC",
            "tela": "Combustíveis — LMC",
            "view": "lmc-intelligence",
            "path": f"/api/v1/lmc-intelligence/cockpit?{PERIOD}",
            "perf_max_s": 3.0,
            "validate": lambda j: j.get("success") is True or isinstance(j.get("data"), dict),
        },
        {
            "id": "COMB-GOV",
            "tela": "Combustíveis — Governança",
            "view": "fuel-governance",
            "path": f"/api/v1/fuel-governance/cockpit?{PERIOD}",
            "perf_max_s": 3.0,
            "validate": lambda j: j.get("success") is True or isinstance(j.get("data"), dict),
        },
        {
            "id": "FISC-NFCE",
            "tela": "Fiscal — NFCE",
            "view": "nfce-intelligence",
            "path": f"/api/v1/nfce-intelligence/cockpit?{PERIOD}",
            "perf_max_s": 3.0,
            "validate": lambda j: j.get("success") is True or isinstance(j.get("data"), dict),
        },
        {
            "id": "FISC-CONC",
            "tela": "Fiscal — Conciliação",
            "view": "fiscal-reconciliation",
            "path": f"/api/v1/fiscal-reconciliation/cockpit?{PERIOD}",
            "perf_max_s": 3.0,
            "validate": lambda j: j.get("success") is True or isinstance(j.get("data"), dict),
        },
        {
            "id": "FISC-RISC",
            "tela": "Fiscal — Riscos",
            "view": "fiscal-intelligence",
            "path": f"/api/v1/fiscal-intelligence/cockpit?{PERIOD}",
            "perf_max_s": 3.0,
            "validate": lambda j: j.get("success") is True or isinstance(j.get("data"), dict),
        },
        {
            "id": "EXEC-RES",
            "tela": "Executivo — Resumo",
            "view": "executive-workspace",
            "path": f"/api/v1/executive-scorecard/cockpit?{PERIOD}",
            "perf_max_s": 3.0,
            "validate": lambda j: j.get("success") is True or isinstance(j.get("data"), dict),
            "note": "Workspace agrega múltiplos cockpits; proxy scorecard",
        },
        {
            "id": "EXEC-IND",
            "tela": "Executivo — Indicadores",
            "view": "executive-scorecard",
            "path": f"/api/v1/executive-scorecard/cockpit?{PERIOD}",
            "perf_max_s": 3.0,
            "validate": lambda j: j.get("success") is True or isinstance(j.get("data"), dict),
        },
        {
            "id": "EXEC-ALR",
            "tela": "Executivo — Alertas",
            "view": "action-center",
            "path": f"/api/v1/action-center/cockpit?{PERIOD}",
            "perf_max_s": 3.0,
            "validate": lambda j: j.get("success") is True or isinstance(j.get("data"), dict),
        },
    ]

    http_live = False
    health = probe_http("/health", timeout=2)
    if health.get("ok"):
        http_live = True

    for t in tests:
        r = get(t["path"], timeout=max(t["perf_max_s"] + 5, 10))
        j = r.get("json") or {}
        checks = t["validate"](j)
        if isinstance(checks, bool):
            checks = (checks,)
        data_ok = all(checks) if checks else r["ok"]
        perf_ok = r["elapsed_s"] <= t["perf_max_s"]
        shell = get(f"/app/financial?view={t['view']}", timeout=10)
        shell_ok_flag = shell["ok"] and shell["status"] == 200

        if r["ok"] and data_ok and perf_ok:
            result = "FUNCIONA"
        elif r["ok"] and data_ok:
            result = "PRECISA CORREÇÃO"
        elif r["ok"]:
            result = "PRECISA CORREÇÃO"
        else:
            result = "NÃO ENTREGA VALOR"

        source = None
        if isinstance(j, dict):
            source = j.get("source") or (j.get("data") or {}).get("source") if isinstance(j.get("data"), dict) else None
            mode = j.get("mode") or j.get("resilience", {}).get("mode") if isinstance(j.get("resilience"), dict) else None
            if mode:
                source = mode

        rows.append(
            {
                "id": t["id"],
                "tela": t["tela"],
                "view": t["view"],
                "path": t["path"],
                "carrega": shell_ok_flag and r["ok"],
                "dados_ok": data_ok,
                "performance_ok": perf_ok,
                "elapsed_s": r["elapsed_s"],
                "perf_max_s": t["perf_max_s"],
                "status_http": r.get("status"),
                "source": source,
                "resultado": result,
                "note": t.get("note"),
            }
        )

    return rows, http_live


def main() -> int:
    rows, http_live = run_testclient()
    payload = {
        "generated_at": datetime.now().isoformat(),
        "period": "2026-06-01 → 2026-06-07",
        "http_server_live": http_live,
        "method": "TestClient (in-process) + optional HTTP health",
        "tests": rows,
        "summary": {
            "total": len(rows),
            "funciona": sum(1 for r in rows if r["resultado"] == "FUNCIONA"),
            "corrigir": sum(1 for r in rows if r["resultado"] == "PRECISA CORREÇÃO"),
            "descartar": sum(1 for r in rows if r["resultado"] == "NÃO ENTREGA VALOR"),
        },
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload["summary"], indent=2))
    for r in rows:
        print(
            r["resultado"][:4],
            f"{r['elapsed_s']:>5}s",
            r["id"],
            r["tela"],
            "| perf" if r["performance_ok"] else "| LENTO",
            "| dados" if r["dados_ok"] else "| SEM DADOS",
        )
    print(f"saved {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
