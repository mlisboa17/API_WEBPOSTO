#!/usr/bin/env python3
"""
Sprint Emergencial — Auditoria de despesas WebPosto vs LOGOS SPACE.

Compara camadas:
  WebPosto API bruta (com paginação ultimoCodigo)
  → normalização backend
  → API LOGOS /v1/financial/expenses
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.config import load_core_config
from src.gateway.webposto_client import WebPostoClient, ENDPOINTS
from src.services.money_normalizer import normalize_webposto_expense_value
from src.services.network_financial_overview_service import (
    FinancialOverviewFilters,
    NetworkFinancialOverviewService,
)

DEFAULT_INI = "2026-06-03"
DEFAULT_FIM = "2026-06-08"
DEFAULT_EMPRESA = 11495
LOGOS_BASE = "http://127.0.0.1:8040"

EXPENSE_ENDPOINTS = {
    "despesas_financeiro_rede": "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
    "financeiro": "/INTEGRACAO/TITULO_PAGAR",
    "conta": "/INTEGRACAO/CONTA",
    "movimento_conta": "/INTEGRACAO/MOVIMENTO_CONTA",
}


def _rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("resultados", "data", "items"):
            val = payload.get(key)
            if isinstance(val, list):
                return [r for r in val if isinstance(r, dict)]
    return []


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except Exception:
        return None


def normalize_expense_like_backend(row: dict[str, Any]) -> dict[str, Any] | None:
    data = row.get("data") or row.get("dataMovimento") or row.get("dataCompetencia")
    valor_raw = row.get("valor") or row.get("valorTotal") or row.get("valorDespesa")
    valor = normalize_webposto_expense_value(valor_raw)
    if not (data and valor is not None):
        return None
    return {
        "empresaCodigo": row.get("empresaCodigo"),
        "data": str(data),
        "valor": str(valor),
        "planoConta": str(row.get("planoConta") or row.get("descricaoPlanoConta") or ""),
        "tipoDespesa": str(row.get("tipoDespesa") or row.get("tipo") or ""),
        "centroCusto": str(row.get("centroCusto") or row.get("descricaoCentroCusto") or ""),
        "_raw_keys": list(row.keys()),
    }


def dedupe_like_backend(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = ("empresaCodigo", "data", "valor", "planoConta", "tipoDespesa", "centroCusto")
    seen: set[tuple[Any, ...]] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        key = tuple(row.get(k) for k in keys)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


async def fetch_raw_paginated(
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
    path: str,
    params: dict[str, Any],
    max_pages: int = 50,
) -> dict[str, Any]:
    all_rows: list[dict[str, Any]] = []
    ultimo_codigo: Any = None
    pages = 0
    errors: list[str] = []

    for page_num in range(1, max_pages + 1):
        page_params = {**params, "CHAVE": api_key}
        if ultimo_codigo is not None:
            page_params["ultimoCodigo"] = ultimo_codigo

        try:
            resp = await client.get(f"{base_url}{path}", params=page_params, timeout=90.0)
        except Exception as exc:
            errors.append(f"page{page_num}: {exc}")
            break

        if resp.status_code != 200:
            errors.append(f"page{page_num}: HTTP {resp.status_code}")
            break

        try:
            payload = resp.json()
        except Exception:
            errors.append(f"page{page_num}: invalid JSON")
            break

        batch = _rows(payload)
        all_rows.extend(batch)
        pages += 1

        if not isinstance(payload, dict):
            break
        novo = payload.get("ultimoCodigo")
        if novo is None or novo == ultimo_codigo or not batch:
            break
        ultimo_codigo = novo

    total_valor = sum(_to_decimal(r.get("valor") or r.get("valorTotal") or r.get("valorDespesa")) or Decimal("0") for r in all_rows)
    empresas = sorted({int(r["empresaCodigo"]) for r in all_rows if r.get("empresaCodigo") is not None})

    return {
        "path": path,
        "pages": pages,
        "registros": len(all_rows),
        "valorTotal": str(total_valor.quantize(Decimal("0.01"))),
        "empresaCodigos": empresas,
        "ultimoCodigoUsed": ultimo_codigo is not None,
        "errors": errors,
        "sampleFields": list(all_rows[0].keys()) if all_rows else [],
    }


async def fetch_logos_backend(
    client: httpx.AsyncClient,
    data_inicial: str,
    data_final: str,
    empresa_codigo: int | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "dataInicial": data_inicial,
        "dataFinal": data_final,
        "page": 1,
        "limit": 500,
    }
    if empresa_codigo is not None:
        params["empresaCodigo"] = str(empresa_codigo)

    try:
        resp = await client.get(f"{LOGOS_BASE}/v1/financial/expenses", params=params, timeout=120.0)
        body = resp.json()
    except Exception as exc:
        return {"status": 0, "error": str(exc), "registros": 0, "valorTotal": "0"}

    data = body.get("data") if isinstance(body, dict) else {}
    rows = data.get("data") if isinstance(data, dict) else []
    if not isinstance(rows, list):
        rows = []
    total_valor = sum(_to_decimal(r.get("valor")) or Decimal("0") for r in rows if isinstance(r, dict))
    return {
        "status": resp.status_code,
        "registros": len(rows),
        "total_api": data.get("total") if isinstance(data, dict) else None,
        "valorTotal": str(total_valor.quantize(Decimal("0.01"))),
        "empresaCodigos": sorted({int(r["empresaCodigo"]) for r in rows if isinstance(r, dict) and r.get("empresaCodigo")}),
    }


async def fetch_single_page_like_backend(
    wp: WebPostoClient,
    filters: FinancialOverviewFilters,
    empresa_codigo: int,
) -> dict[str, Any]:
    """Simula _fetch_despesas atual (SEM paginação ultimoCodigo)."""
    params = {
        "dataInicial": filters.data_inicial,
        "dataFinal": filters.data_final,
        "empresaCodigo": empresa_codigo,
    }
    resp = await wp.call_endpoint("despesas_financeiro_rede", params=params)
    if not resp.success:
        return {"success": False, "error": resp.error, "registros": 0}
    rows = _rows(resp.data)
    return {
        "success": True,
        "registros": len(rows),
        "hasUltimoCodigo": isinstance(resp.data, dict) and resp.data.get("ultimoCodigo") is not None,
        "ultimoCodigo": resp.data.get("ultimoCodigo") if isinstance(resp.data, dict) else None,
    }


async def run_audit(
    data_inicial: str,
    data_final: str,
    empresa_codigo: int | None,
) -> dict[str, Any]:
    config = load_core_config()
    result: dict[str, Any] = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "periodo": {"dataInicial": data_inicial, "dataFinal": data_final, "empresaCodigo": empresa_codigo},
        "camadas": {},
        "diagnostico": [],
        "registrosPerdidos": {},
    }

    base_params: dict[str, Any] = {"dataInicial": data_inicial, "dataFinal": data_final}
    if empresa_codigo is not None:
        base_params["empresaCodigo"] = empresa_codigo

    async with httpx.AsyncClient() as http:
        # Camada 1: API bruta COM paginação
        raw_paginated = await fetch_raw_paginated(
            http,
            config.webposto_base_url,
            config.webposto_api_key,
            EXPENSE_ENDPOINTS["despesas_financeiro_rede"],
            base_params,
        )
        result["camadas"]["api_bruta_paginada"] = raw_paginated

        # Camada 1b: API bruta página única (como backend hoje)
        single_params = {**base_params, "CHAVE": config.webposto_api_key}
        try:
            r1 = await http.get(
                f"{config.webposto_base_url}{EXPENSE_ENDPOINTS['despesas_financeiro_rede']}",
                params=single_params,
                timeout=90,
            )
            p1 = r1.json() if r1.status_code == 200 else {}
            rows1 = _rows(p1)
            result["camadas"]["api_bruta_pagina_unica"] = {
                "registros": len(rows1),
                "hasUltimoCodigo": isinstance(p1, dict) and p1.get("ultimoCodigo") is not None,
                "ultimoCodigo": p1.get("ultimoCodigo") if isinstance(p1, dict) else None,
                "valorTotal": str(
                    sum(_to_decimal(x.get("valor") or x.get("valorTotal")) or Decimal("0") for x in rows1).quantize(Decimal("0.01"))
                ),
            }
        except Exception as exc:
            result["camadas"]["api_bruta_pagina_unica"] = {"error": str(exc)}

        # Endpoints alternativos
        alt = {}
        for key, path in EXPENSE_ENDPOINTS.items():
            if key == "despesas_financeiro_rede":
                continue
            alt[key] = await fetch_raw_paginated(http, config.webposto_base_url, config.webposto_api_key, path, base_params, max_pages=5)
        result["camadas"]["endpoints_alternativos"] = alt

        # Camada 2: Backend LOGOS
        result["camadas"]["backend_logos"] = await fetch_logos_backend(http, data_inicial, data_final, empresa_codigo)

    # Camada 2b: simulação normalização
    wp = WebPostoClient()
    raw_rows: list[dict[str, Any]] = []
    if empresa_codigo is not None:
        empresas = [empresa_codigo]
    else:
        empresas = raw_paginated.get("empresaCodigos") or []

    # Re-fetch paginated rows for normalization analysis
    async with httpx.AsyncClient() as http:
        page_params = {**base_params, "CHAVE": config.webposto_api_key}
        ultimo = None
        for _ in range(50):
            pp = dict(page_params)
            if ultimo is not None:
                pp["ultimoCodigo"] = ultimo
            resp = await http.get(
                f"{config.webposto_base_url}{EXPENSE_ENDPOINTS['despesas_financeiro_rede']}",
                params=pp,
                timeout=90,
            )
            if resp.status_code != 200:
                break
            payload = resp.json()
            batch = _rows(payload)
            raw_rows.extend(batch)
            if not isinstance(payload, dict):
                break
            novo = payload.get("ultimoCodigo")
            if novo is None or novo == ultimo or not batch:
                break
            ultimo = novo

    normalized = [n for r in raw_rows if (n := normalize_expense_like_backend(r))]
    dropped_no_normalize = len(raw_rows) - len(normalized)
    deduped = dedupe_like_backend(normalized)
    dropped_dedupe = len(normalized) - len(deduped)

    result["camadas"]["normalizacao"] = {
        "raw_registros": len(raw_rows),
        "apos_normalizar": len(normalized),
        "descartados_normalizacao": dropped_no_normalize,
        "apos_dedupe": len(deduped),
        "descartados_dedupe": dropped_dedupe,
        "valorTotal_normalizado": str(sum(_to_decimal(r["valor"]) or Decimal("0") for r in deduped).quantize(Decimal("0.01"))),
    }

    # Single page vs paginated gap
    pag = raw_paginated.get("registros", 0)
    single = result["camadas"].get("api_bruta_pagina_unica", {}).get("registros", 0)
    backend = result["camadas"].get("backend_logos", {}).get("registros", 0)
    norm = len(deduped)

    if pag > single:
        result["diagnostico"].append(
            {
                "causa": "paginacao_incompleta",
                "severidade": "P0",
                "detalhe": f"API paginada={pag} vs pagina unica={single}. Backend usa pagina unica (_fetch_despesas sem ultimoCodigo).",
            }
        )

    if pag > backend:
        result["diagnostico"].append(
            {
                "causa": "backend_perde_registros",
                "severidade": "P0",
                "detalhe": f"API paginada={pag} vs backend LOGOS={backend}.",
            }
        )

    if dropped_no_normalize > 0:
        result["diagnostico"].append(
            {
                "causa": "normalizacao_descarta",
                "severidade": "P1",
                "detalhe": f"{dropped_no_normalize} registros sem data+valor validos descartados em _normalize_expense.",
            }
        )

    if dropped_dedupe > 0:
        result["diagnostico"].append(
            {
                "causa": "deduplicacao",
                "severidade": "P2",
                "detalhe": f"{dropped_dedupe} registros removidos por _dedupe_rows.",
            }
        )

    if empresa_codigo is not None:
        sp = await fetch_single_page_like_backend(
            wp,
            FinancialOverviewFilters(data_inicial=data_inicial, data_final=data_final, empresa_codigo=empresa_codigo),
            empresa_codigo,
        )
        result["camadas"]["backend_fetch_simulado"] = sp
        if sp.get("hasUltimoCodigo"):
            result["diagnostico"].append(
                {
                    "causa": "ultimoCodigo_presente_ignorado",
                    "severidade": "P0",
                    "detalhe": f"Resposta contém ultimoCodigo={sp.get('ultimoCodigo')} mas backend não pagina.",
                }
            )

    result["comparacao"] = {
        "api_bruta_paginada": {"registros": pag, "valor": raw_paginated.get("valorTotal")},
        "api_bruta_pagina_unica": result["camadas"].get("api_bruta_pagina_unica", {}),
        "apos_normalizacao": {"registros": norm, "valor": result["camadas"]["normalizacao"]["valorTotal_normalizado"]},
        "backend_logos": result["camadas"].get("backend_logos", {}),
        "frontend_tabela": "equivale backend (fetchAllPages limit 500 x 40 paginas API LOGOS)",
        "export_csv_pdf": "equivale linhas visiveis filtradas na tabela (sortedRows)",
    }

    result["registrosPerdidos"] = {
        "paginacao": max(0, pag - single),
        "backend_vs_api": max(0, pag - backend),
        "normalizacao": dropped_no_normalize,
        "dedupe": dropped_dedupe,
    }

    return result


def write_report(data: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    comp = data.get("comparacao", {})
    diag = data.get("diagnostico", [])
    lines = [
        "# Audit Expenses WebPosto — Resultado",
        "",
        f"**Gerado:** {data.get('generatedAt')}",
        f"**Período:** {data['periodo']['dataInicial']} .. {data['periodo']['dataFinal']}",
        f"**Empresa:** {data['periodo'].get('empresaCodigo') or 'TODAS'}",
        "",
        "## Comparação",
        "",
        "| Fonte | Registros | Valor Total | Observação |",
        "|---|---:|---:|---|",
    ]

    def row(name: str, block: dict, obs: str = ""):
        reg = block.get("registros", block.get("registros", "—"))
        val = block.get("valorTotal") or block.get("valor") or "—"
        lines.append(f"| {name} | {reg} | {val} | {obs} |")

    row("API bruta (paginada ultimoCodigo)", comp.get("api_bruta_paginada", {}), "Referência máxima")
    row("API bruta (página única)", comp.get("api_bruta_pagina_unica", {}), "Como backend hoje")
    row("Após normalização+dedupe", comp.get("apos_normalizacao", {}), "Simulação backend")
    bl = comp.get("backend_logos", {})
    lines.append(f"| Backend LOGOS | {bl.get('registros', '—')} | {bl.get('valorTotal', '—')} | total API={bl.get('total_api')} |")
    lines.append("| Frontend tabela | = Backend | — | fetchAllPages sobre /v1/financial/expenses |")
    lines.append("| Export CSV/PDF | = Tabela filtrada | — | sortedRows em export.js |")

    lines.extend(["", "## Diagnóstico", ""])
    for item in diag:
        lines.append(f"- **[{item.get('severidade')}]** {item.get('causa')}: {item.get('detalhe')}")

    lines.extend(["", "## Registros perdidos", ""])
    lost = data.get("registrosPerdidos", {})
    for k, v in lost.items():
        lines.append(f"- {k}: **{v}**")

    lines.extend(["", "## Correção recomendada", ""])
    if any(d.get("causa") == "paginacao_incompleta" for d in diag):
        lines.append("1. Implementar `_collect_with_cursor` em `_fetch_despesas` (espelhar vendas).")
    if any(d.get("causa") == "normalizacao_descarta" for d in diag):
        lines.append("2. Auditar campos `dataCompetencia` / `dataMovimento` rejeitados.")
    lines.append("3. Validar token por filial (5256, 5333, etc.).")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-inicial", default=DEFAULT_INI)
    parser.add_argument("--data-final", default=DEFAULT_FIM)
    parser.add_argument("--empresa-codigo", type=int, default=DEFAULT_EMPRESA)
    parser.add_argument("--todas-empresas", action="store_true")
    args = parser.parse_args()

    empresa = None if args.todas_empresas else args.empresa_codigo
    data = await run_audit(args.data_inicial, args.data_final, empresa)

    out_json = ROOT / "audit_expenses_webposto_result.json"
    out_md = ROOT / "audit_expenses_webposto_report.md"
    write_report(data, out_json, out_md)
    print(f"JSON: {out_json}")
    print(f"MD:   {out_md}")
    print(json.dumps(data.get("comparacao"), ensure_ascii=False, indent=2))
    print("Diagnóstico:", len(data.get("diagnostico", [])))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
