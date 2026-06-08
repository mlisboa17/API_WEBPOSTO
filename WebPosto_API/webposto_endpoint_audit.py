# SPRINT 21.3 — AUDITORIA DE ENDPOINTS WEBPOSTO
# webposto_endpoint_audit.py

import asyncio
import time
import json
from typing import List, Dict, Any
import httpx

# Lista de endpoints para auditar
ENDPOINTS_PARA_AUDITAR = [
    # Auditoria
    "/auditoria/health",
    "/auditoria/despesas/real_01",
    "/auditoria/fechamentos/real_01",
    "/auditoria/resumo/real_01",
    # Clientes
    "/clientes/",
    "/clientes/1",
    # Expenses
    "/expenses/extract",
    # Health
    "/health",
    "/ready",
    # Metrics
    "/metrics/executive",
    "/metrics/stream",
    # Sync
    "/sync/clientes",
    "/sync/abastecimentos",
    "/sync/financeiro",
    "/sync/caixa",
    "/sync/full",
    # Auth
    "/auth/login",
    # WebPosto V1
    "/v1/financial/expenses",
    "/v1/financial/accounts-payable",
    "/v1/sales",
    "/v1/stock",
    "/v1/financial/overview",
    "/v1/companies",
    # API V1
    "/api/v1/kpis",
    "/api/v1/dre",
    "/api/v1/data-quality",
    "/api/v1/network-coverage",
    "/api/v1/filiais",
    # Endpoints Específicos
    "/EMPRESAS",
    "/VENDA",
    "/VENDA_ITEM",
    "/VENDA_FORMA_PAGAMENTO",
    "/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
    "/TITULO_PAGAR",
    "/TITULO_RECEBER",
    "/CONSULTAR_CAIXA_REDE",
    "/CONSULTAR_CAIXA_APRESENTADO_REDE",
    "/PRODUTO_EMPRESA",
    "/PRODUTO_ESTOQUE",
]

BASE_URL = "http://127.0.0.1:8041"

async def auditar_endpoint(client: httpx.AsyncClient, endpoint: str) -> Dict[str, Any]:
    """Audita um único endpoint."""
    start_time = time.time()
    try:
        # Para endpoints que requerem POST, podemos adicionar uma lógica aqui
        if endpoint in ["/expenses/extract", "/auth/login"] or endpoint.startswith("/sync"):
            response = await client.post(f"{BASE_URL}{endpoint}", json={}, timeout=10.0)
        else:
            response = await client.get(f"{BASE_URL}{endpoint}", timeout=10.0)
        
        tempo_resposta_ms = (time.time() - start_time) * 1000
        
        status = response.status_code
        possui_dados = False
        if status == 200:
            try:
                dados = response.json()
                if isinstance(dados, list) and len(dados) > 0:
                    possui_dados = True
                elif isinstance(dados, dict) and dados:
                    possui_dados = True
            except json.JSONDecodeError:
                possui_dados = len(response.content) > 0

        return {
            "endpoint": endpoint,
            "status": status,
            "possuiDados": possui_dados,
            "tempoRespostaMs": round(tempo_resposta_ms),
        }
    except httpx.TimeoutException:
        return {
            "endpoint": endpoint,
            "status": "timeout",
            "possuiDados": False,
            "tempoRespostaMs": round((time.time() - start_time) * 1000),
        }
    except httpx.RequestError as e:
        return {
            "endpoint": endpoint,
            "status": 500, # Ou um código de erro específico
            "error_details": str(e),
            "possuiDados": False,
            "tempoRespostaMs": round((time.time() - start_time) * 1000),
        }

def classificar_endpoint(resultado: Dict[str, Any]) -> str:
    """Classifica o endpoint com base no resultado da auditoria."""
    status = resultado["status"]
    
    if status == 200 and resultado["possuiDados"]:
        return "PRODUCAO"
    if status == 404 or status == "timeout":
        return "OBSOLETO"
    if status == 200 and not resultado["possuiDados"]:
        return "EXPERIMENTAL" # Responde mas não tem dados, pode ser experimental
    
    return "OBSOLETO" # Outros erros


async def main():
    """Função principal para executar a auditoria."""
    print("Iniciando auditoria de endpoints...")
    resultados = []
    async with httpx.AsyncClient() as client:
        tasks = [auditar_endpoint(client, ep) for ep in ENDPOINTS_PARA_AUDITAR]
        respostas = await asyncio.gather(*tasks)
        
        for r in respostas:
            r["categoria"] = classificar_endpoint(r)
            r["utilizadoPor"] = [] # Será preenchido após análise do frontend
            resultados.append(r)

    with open("webposto_endpoint_audit.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print("Auditoria concluída. Resultados salvos em webposto_endpoint_audit.json")
    
    # Gerar o .md
    with open("webposto_endpoint_catalog.md", "w", encoding="utf-8") as f:
        f.write("# Catálogo de Endpoints WebPosto\n\n")
        for categoria in ["PRODUCAO", "EXPERIMENTAL", "OBSOLETO"]:
            f.write(f"## {categoria}\n\n")
            for r in resultados:
                if r["categoria"] == categoria:
                    f.write(f"- `{r['endpoint']}`\n")
            f.write("\n")

    print("Catálogo gerado em webposto_endpoint_catalog.md")


if __name__ == "__main__":
    asyncio.run(main())
