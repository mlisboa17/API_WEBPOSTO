"""
Script para inspecionar a API webPosto real.
Salva todos os endpoints, parametros e exemplos em RESULTADO_API.json
"""

import httpx
import json
import asyncio
from datetime import datetime, timedelta

BASE_URL = "http://web.qualityautomacao.com.br"
API_KEY = "<WEBPOSTO_API_TOKEN>"
HOJE = datetime.now().strftime("%Y-%m-%d")
ONTEM = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

resultados = {}


async def get(client, nome, path, params=None):
    p = params or {}
    p["CHAVE"] = API_KEY
    try:
        r = await client.get(path, params=p, timeout=15)
        resultados[nome] = {
            "url": str(r.url),
            "status": r.status_code,
            "body": r.text[:2000],
        }
        status = "✅" if r.status_code < 400 else "❌"
        print(f"{status} [{r.status_code}] {nome}")
        if r.status_code < 400:
            print(f"   Preview: {r.text[:300]}")
    except Exception as e:
        resultados[nome] = {"erro": str(e)}
        print(f"💥 {nome}: {e}")


async def main():
    print(f"\n{'='*60}")
    print("  Inspecionando API webPosto")
    print(f"  Base URL: {BASE_URL}")
    print(f"  API Key:  {API_KEY}")
    print(f"{'='*60}\n")

    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    async with httpx.AsyncClient(base_url=BASE_URL, headers=headers) as c:

        # --- Swagger / OpenAPI ---
        await get(c, "swagger-config", "/v3/api-docs/swagger-config")
        await get(c, "swagger-api-docs", "/v3/api-docs")

        # --- Endpoints com CHAVE como query param ---
        await get(
            c,
            "INTEGRACAO/ABASTECIMENTO",
            "/INTEGRACAO/ABASTECIMENTO",
            {"dataInicial": ONTEM, "dataFinal": HOJE},
        )

        await get(
            c,
            "INTEGRACAO/FINANCEIRO",
            "/INTEGRACAO/FINANCEIRO",
            {"dataInicial": ONTEM, "dataFinal": HOJE},
        )

        await get(
            c,
            "INTEGRACAO/CAIXA",
            "/INTEGRACAO/CAIXA",
            {"dataInicial": ONTEM, "dataFinal": HOJE},
        )

        await get(
            c,
            "INTEGRACAO/TITULOS",
            "/INTEGRACAO/TITULOS",
            {"dataInicial": ONTEM, "dataFinal": HOJE},
        )

        await get(
            c,
            "INTEGRACAO/VENDAS",
            "/INTEGRACAO/VENDAS",
            {"dataInicial": ONTEM, "dataFinal": HOJE},
        )

        await get(
            c,
            "INTEGRACAO/PRODUTOS",
            "/INTEGRACAO/PRODUTOS",
            {"dataInicial": ONTEM, "dataFinal": HOJE},
        )

        # --- Tentar com Authorization Header ---
        c.headers.update({"Authorization": f"Bearer {API_KEY}"})
        await get(
            c,
            "api/financeiro (Bearer)",
            "/api/financeiro",
            {"dataInicial": ONTEM, "dataFinal": HOJE},
        )

        await get(
            c,
            "api/caixa (Bearer)",
            "/api/caixa",
            {"dataInicial": ONTEM, "dataFinal": HOJE},
        )

        # --- Tentar root para ver o que responde ---
        await get(c, "root /", "/")
        await get(c, "health", "/health")
        await get(c, "actuator", "/actuator")
        await get(c, "actuator/health", "/actuator/health")

    # Salvar resultado completo
    with open("RESULTADO_API.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print("  Resultado salvo em RESULTADO_API.json")
    print(f"{'='*60}\n")

    # Resumo
    ok = [k for k, v in resultados.items() if v.get("status", 999) < 400]
    err = [k for k, v in resultados.items() if v.get("status", 999) >= 400]

    print(f"✅ Sucesso ({len(ok)}): {ok}")
    print(f"❌ Falha  ({len(err)}): {err}")


asyncio.run(main())
