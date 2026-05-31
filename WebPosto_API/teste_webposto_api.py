"""
WebPosto API - Script de Teste e Mapeamento
============================================
Base URL: https://web.qualityautomacao.com.br
Auth: Query param CHAVE=<api_key>
Swagger UI: https://web.qualityautomacao.com.br/webjars/swagger-ui/index.html?configUrl=/v3/api-docs/swagger-config

Como rodar:
  pip install requests
  python teste_webposto_api.py
"""

import requests
import json
from datetime import datetime, timedelta

# ─── CONFIGURAÇÃO ─────────────────────────────────────────────────────────────
import os

# API key is read from environment when available (use .env or export WEBPOSTO_API_KEY)
API_KEY = os.getenv("WEBPOSTO_API_KEY", "$WEBPOSTO_CHAVE")
BASE_URL = os.getenv("WEBPOSTO_BASE_URL", "https://web.qualityautomacao.com.br")

# Datas para testes (últimos 7 dias)
HOJE = datetime.now().strftime("%Y-%m-%d")
SEMANA_ANT = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")


# ─── HELPER ───────────────────────────────────────────────────────────────────
def chamar(endpoint: str, params: dict = None, metodo: str = "GET") -> dict:
    """Executa uma chamada à API e retorna resultado padronizado."""
    params = params or {}
    params["CHAVE"] = API_KEY

    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    try:
        r = requests.request(metodo, url, params=params, timeout=15)
        return {
            "endpoint": endpoint,
            "status": r.status_code,
            "ok": r.status_code in (200, 201),
            "body": (
                r.json()
                if r.headers.get("content-type", "").startswith("application/json")
                else r.text[:500]
            ),
        }
    except Exception as e:
        return {"endpoint": endpoint, "status": "ERRO", "ok": False, "body": str(e)}


def imprimir(resultado: dict):
    status = resultado["status"]
    ok_str = "✅" if resultado["ok"] else "❌"
    print(f"\n{ok_str} [{status}] {resultado['endpoint']}")
    body = resultado["body"]
    if isinstance(body, (dict, list)):
        print(json.dumps(body, ensure_ascii=False, indent=2)[:1000])
    else:
        print(str(body)[:500])


# ─── STEP 1: CHECAR SWAGGER / API-DOCS ───────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 1 — Swagger & API Docs")
print("=" * 60)

endpoints_meta = [
    "v3/api-docs",
    "v3/api-docs/swagger-config",
    "swagger-ui/index.html",
    "api-docs",
]
for ep in endpoints_meta:
    r = chamar(ep)
    imprimir(r)


# ─── STEP 2: ENDPOINTS DE INTEGRAÇÃO CONHECIDOS ──────────────────────────────
print("\n" + "=" * 60)
print("STEP 2 — Endpoints de Integração (documentados)")
print("=" * 60)

endpoints_integracao = [
    # Abastecimento (combustíveis)
    ("INTEGRACAO/ABASTECIMENTO", {"dataInicial": SEMANA_ANT, "dataFinal": HOJE}),
    # Vendas (conveniência)
    ("INTEGRACAO/VENDAS", {"dataInicial": SEMANA_ANT, "dataFinal": HOJE}),
    # Produtos
    ("INTEGRACAO/PRODUTOS", {}),
    # Clientes / Fidelidade
    ("INTEGRACAO/CLIENTES", {}),
    ("INTEGRACAO/FIDELIDADE", {"dataInicial": SEMANA_ANT, "dataFinal": HOJE}),
    # Financeiro
    ("INTEGRACAO/FINANCEIRO", {"dataInicial": SEMANA_ANT, "dataFinal": HOJE}),
    ("INTEGRACAO/CAIXAS", {"dataInicial": SEMANA_ANT, "dataFinal": HOJE}),
    # Estoque
    ("INTEGRACAO/ESTOQUE", {}),
    ("INTEGRACAO/MOVIMENTACAO", {"dataInicial": SEMANA_ANT, "dataFinal": HOJE}),
    # Funcionários / Turnos
    ("INTEGRACAO/FUNCIONARIOS", {}),
    ("INTEGRACAO/TURNOS", {"dataInicial": SEMANA_ANT, "dataFinal": HOJE}),
    # Preços
    ("INTEGRACAO/PRECOS", {}),
    ("INTEGRACAO/TANQUES", {}),
]

resultados = []
for ep, params in endpoints_integracao:
    r = chamar(ep, params)
    resultados.append(r)
    imprimir(r)


# ─── STEP 3: VARIAÇÕES DE PATH ───────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 3 — Variações de path (api/ prefix, v1, etc.)")
print("=" * 60)

prefixos = ["api/", "api/v1/", "rest/", "webposto/api/", ""]
for prefixo in prefixos:
    ep = f"{prefixo}INTEGRACAO/ABASTECIMENTO"
    r = chamar(ep, {"dataInicial": SEMANA_ANT, "dataFinal": HOJE})
    imprimir(r)


# ─── RESUMO ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("RESUMO — Endpoints que responderam com sucesso (2xx)")
print("=" * 60)
sucesso = [r for r in resultados if r["ok"]]
if sucesso:
    for r in sucesso:
        print(f"  ✅ {r['endpoint']}")
else:
    print("  Nenhum endpoint retornou 2xx — verifique:")
    print("  1. Se a chave está ativa (contato: suporte@webposto.com.br)")
    print("  2. Se seu IP está liberado (APIs às vezes exigem whitelist)")
    print(
        "  3. Acesse o Swagger: https://web.qualityautomacao.com.br/webjars/swagger-ui/index.html?configUrl=/v3/api-docs/swagger-config"
    )

print("\nSwagger completo disponível em:")
print(
    "  https://web.qualityautomacao.com.br/webjars/swagger-ui/index.html?configUrl=/v3/api-docs/swagger-config"
)

