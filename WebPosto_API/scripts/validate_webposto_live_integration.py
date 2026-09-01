"""Validação de integração real webPosto — produção/homologação.

Executa:
1) WebPostoIntegrationService (tanques + vendas) por filial
2) Rotas LOGOS /realtime-bundle e /inventory-prediction (se API local disponível)

Não imprime tokens/segredos.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

import httpx

FILIAIS = [
    {"codigo": 5555, "nome": "Casa Caiada"},
    {"codigo": 11495, "nome": "VIP (licenciado)"},
    {"codigo": 6666, "nome": "VIP (alias settings)"},
    {"codigo": 74014, "nome": "Real Doze Filial II"},
]

API_BASE = "http://127.0.0.1:8040"


def _sample_tanks(tanques: list[dict[str, Any]], n: int = 2) -> list[dict[str, Any]]:
    out = []
    for t in tanques[:n]:
        out.append(
            {
                "tanque_codigo": t.get("tanque_codigo"),
                "produto_nome": t.get("produto_nome"),
                "volume_atual_litros": t.get("volume_atual_litros"),
                "capacidade_litros": t.get("capacidade_litros"),
                "ocupacao_pct": t.get("ocupacao_pct"),
            }
        )
    return out


def _sample_sales(sales: dict[str, Any]) -> dict[str, Any]:
    produtos = sales.get("por_produto") or []
    return {
        "litros_total": sales.get("litros_total"),
        "faturamento_rs": sales.get("faturamento_rs"),
        "qtd_abastecimentos": sales.get("qtd_abastecimentos"),
        "top_produtos": [
            {
                "produto_nome": p.get("produto_nome"),
                "litros": p.get("litros"),
                "faturamento_rs": p.get("faturamento_rs"),
            }
            for p in produtos[:3]
        ],
        "fonte": sales.get("fonte"),
        "mensagem": sales.get("mensagem"),
        "sucesso": sales.get("sucesso"),
    }


async def test_integration_service() -> list[dict[str, Any]]:
    from src.core.config import load_core_config
    from src.services.webposto_integration_service import get_webposto_integration_service

    cfg = load_core_config()
    print("=" * 72)
    print("CONFIG WEBPOSTO (sem segredos)")
    print(f"  base_url     = {cfg.webposto_base_url}")
    print(f"  keys_count   = {len(cfg.webposto_api_keys)}")
    print(f"  has_primary  = {bool(cfg.webposto_api_key)}")
    print(f"  timeout_s    = {cfg.timeout_seconds}")
    print("=" * 72)

    svc = get_webposto_integration_service()
    results: list[dict[str, Any]] = []

    for filial in FILIAIS:
        codigo = filial["codigo"]
        nome = filial["nome"]
        print(f"\n--- Serviço Integration | {nome} ({codigo}) ---")
        t0 = time.perf_counter()
        try:
            tanks = await svc.get_tank_levels(codigo)
            sales = await svc.get_realtime_sales(codigo)
            elapsed = round((time.perf_counter() - t0) * 1000)
            row = {
                "filial": nome,
                "empresa_codigo": codigo,
                "elapsed_ms": elapsed,
                "tanques": {
                    "sucesso": tanks.sucesso,
                    "qtd": len(tanks.tanques),
                    "mensagem": tanks.mensagem,
                    "fonte": tanks.fonte,
                    "amostra": _sample_tanks(tanks.tanques),
                },
                "vendas": _sample_sales(asdict(sales) if hasattr(sales, "__dataclass_fields__") else {
                    "litros_total": sales.litros_total,
                    "faturamento_rs": sales.faturamento_rs,
                    "qtd_abastecimentos": sales.qtd_abastecimentos,
                    "por_produto": sales.por_produto,
                    "fonte": sales.fonte,
                    "mensagem": sales.mensagem,
                    "sucesso": sales.sucesso,
                }),
                "auth_ok": tanks.sucesso or sales.sucesso,
                "has_live_data": (len(tanks.tanques) > 0) or (sales.qtd_abastecimentos > 0) or (sales.litros_total > 0),
            }
            status = "OK" if row["auth_ok"] else "FALHA"
            print(f"  status={status} elapsed={elapsed}ms")
            print(f"  tanques: sucesso={tanks.sucesso} qtd={len(tanks.tanques)} msg={tanks.mensagem}")
            print(f"  amostra_tanques={json.dumps(row['tanques']['amostra'], ensure_ascii=False)}")
            print(
                f"  vendas: sucesso={sales.sucesso} litros={sales.litros_total} "
                f"fat={sales.faturamento_rs} qtd={sales.qtd_abastecimentos} msg={sales.mensagem}"
            )
            print(f"  amostra_vendas={json.dumps(row['vendas'], ensure_ascii=False)}")
            results.append(row)
        except Exception as exc:
            elapsed = round((time.perf_counter() - t0) * 1000)
            print(f"  status=EXCEPTION elapsed={elapsed}ms err={exc}")
            results.append(
                {
                    "filial": nome,
                    "empresa_codigo": codigo,
                    "elapsed_ms": elapsed,
                    "auth_ok": False,
                    "has_live_data": False,
                    "error": str(exc),
                }
            )
    return results


async def test_http_routes() -> list[dict[str, Any]]:
    print("\n" + "=" * 72)
    print("ROTAS LOGOS (HTTP local)")
    print("=" * 72)
    results: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        # health/docs
        try:
            docs = await client.get(f"{API_BASE}/docs")
            print(f"  GET /docs -> HTTP {docs.status_code}")
            if docs.status_code >= 400:
                print("  API local indisponível — pulando rotas HTTP")
                return [{"skipped": True, "reason": f"/docs HTTP {docs.status_code}"}]
        except Exception as exc:
            print(f"  API local indisponível: {exc}")
            return [{"skipped": True, "reason": str(exc)}]

        for filial in FILIAIS:
            codigo = filial["codigo"]
            nome = filial["nome"]
            print(f"\n--- Rotas HTTP | {nome} ({codigo}) ---")
            for path in (
                f"/api/v1/operational/realtime-bundle?empresaCodigo={codigo}",
                f"/api/v1/operational/inventory-prediction?empresaCodigo={codigo}",
            ):
                url = f"{API_BASE}{path}"
                t0 = time.perf_counter()
                try:
                    resp = await client.get(url)
                    elapsed = round((time.perf_counter() - t0) * 1000)
                    body: Any
                    try:
                        body = resp.json()
                    except Exception:
                        body = {"raw": (resp.text or "")[:300]}

                    sample: dict[str, Any] = {"http_status": resp.status_code, "elapsed_ms": elapsed}
                    if "realtime-bundle" in path:
                        data = (body or {}).get("data") or {}
                        vendas = data.get("vendas_dia") or {}
                        tanques = data.get("tanques") or {}
                        sample.update(
                            {
                                "success": (body or {}).get("success"),
                                "vendas_sucesso": vendas.get("sucesso"),
                                "vendas_litros": vendas.get("litros_total"),
                                "vendas_fat": vendas.get("faturamento_rs"),
                                "tanques_sucesso": tanques.get("sucesso"),
                                "tanques_qtd": len(tanques.get("itens") or []),
                                "amostra_tanque": (tanques.get("itens") or [None])[0],
                                "auth_error": resp.status_code in (401, 403),
                            }
                        )
                    else:
                        sample.update(
                            {
                                "success": (body or {}).get("success", True),
                                "predicoes_qtd": len((body or {}).get("predicoes") or []),
                                "tanques_alerta": (body or {}).get("tanques_com_alerta"),
                                "empresa_nome": (body or {}).get("empresa_nome"),
                                "obs": ((body or {}).get("observacoes") or [])[:2],
                                "auth_error": resp.status_code in (401, 403),
                            }
                        )

                    print(f"  GET {path}")
                    print(f"    HTTP {resp.status_code} ({elapsed}ms)")
                    print(f"    sample={json.dumps(sample, ensure_ascii=False, default=str)[:900]}")
                    results.append({"filial": nome, "empresa_codigo": codigo, "path": path, **sample})
                except Exception as exc:
                    elapsed = round((time.perf_counter() - t0) * 1000)
                    print(f"  GET {path} EXCEPTION ({elapsed}ms): {exc}")
                    results.append(
                        {
                            "filial": nome,
                            "empresa_codigo": codigo,
                            "path": path,
                            "error": str(exc),
                            "elapsed_ms": elapsed,
                        }
                    )
    return results


async def main() -> int:
    print(f"VALIDAÇÃO INTEGRAÇÃO REAL — {datetime.now(timezone.utc).isoformat()}")
    svc_results = await test_integration_service()
    http_results = await test_http_routes()

    print("\n" + "=" * 72)
    print("RESUMO")
    print("=" * 72)
    live_ok = [r for r in svc_results if r.get("has_live_data")]
    auth_ok = [r for r in svc_results if r.get("auth_ok")]
    print(f"  Filiais com auth_ok: {len(auth_ok)}/{len(svc_results)}")
    print(f"  Filiais com dados vivos: {len(live_ok)}/{len(svc_results)}")
    http_auth_errors = [r for r in http_results if r.get("auth_error")]
    http_ok = [r for r in http_results if r.get("http_status") == 200]
    if http_results and not http_results[0].get("skipped"):
        print(f"  Rotas HTTP 200: {len(http_ok)}/{len(http_results)}")
        print(f"  Rotas com 401/403: {len(http_auth_errors)}")
    else:
        print("  Rotas HTTP: não testadas (API local down)")

    # Critério: pelo menos as 3 filiais oficiais (5555, 11495, 74014) com auth_ok
    oficiais = {5555, 11495, 74014}
    oficiais_ok = {r["empresa_codigo"] for r in auth_ok if r.get("empresa_codigo") in oficiais}
    print(f"  Oficiais OK: {sorted(oficiais_ok)}")
    return 0 if oficiais.issubset(oficiais_ok) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
