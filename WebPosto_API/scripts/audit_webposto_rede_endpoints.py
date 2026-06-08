import sys
import asyncio
import json
from pathlib import Path
from datetime import date
from typing import Any, List, Dict

# Add src package root to python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.gateway.webposto_client import WebPostoClient
from src.services.network_financial_overview_service import NetworkFinancialOverviewService, FinancialOverviewFilters

# Additional red endpoints not yet explicitly mapped under ENDPOINTS but mentioned in context
# Mapping to their respective URL paths
REDE_ENDPOINTS = {
    "venda_item_rede": {
        "url": "/INTEGRACAO/CONSULTAR_VENDA_ITEM_REDE",
        "key": "venda_item_rede",
        "category": "Vendas"
    },
    "venda_forma_pagamento_rede": {
        "url": "/INTEGRACAO/CONSULTAR_VENDA_FORMA_PAGAMENTO_REDE",
        "key": "venda_forma_pagamento_rede",
        "category": "Vendas"
    },
    "venda_rede": {
        "url": "/INTEGRACAO/VENDA_REDE",
        "key": "vendas_rede_legada", # Let's try map to a custom key later
        "category": "Vendas"
    },
    "despesas_financeiro_rede": {
        "url": "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
        "key": "despesas_financeiro_rede",
        "category": "Financeiro"
    },
    "usuario_empresa_rede": {
        "url": "/INTEGRACAO/USUARIO_EMPRESA_REDE",
        "key": "usuario_empresa_rede",
        "category": "Vendas & NF"
    },
    "titulo_pagar_rede": {
        "url": "/INTEGRACAO/TITULO_PAGAR_REDE", # Check if this path exists or matches /INTEGRACAO/TITULO_PAGAR with network params
        "key": "titulo_pagar_rede",
        "category": "Financeiro"
    },
    "titulo_receber_rede": {
        "url": "/INTEGRACAO/TITULO_RECEBER_REDE",
        "key": "titulo_receber_rede",
        "category": "Financeiro"
    },
    "produto_empresa_rede": {
        "url": "/INTEGRACAO/PRODUTO_EMPRESA_REDE",
        "key": "produto_empresa_rede",
        "category": "Produtos"
    },
    "produto_estoque": {
        "url": "/INTEGRACAO/PRODUTO_ESTOQUE",
        "key": "produto_estoque",
        "category": "Produtos"
    },
    "tanque": {
        "url": "/INTEGRACAO/TANQUE",
        "key": "tanque",
        "category": "Produtos"
    },
    "vale_funcionario_rede": {
        "url": "/INTEGRACAO/VALE_FUNCIONARIO_REDE",
        "key": "vale_funcionario_rede",
        "category": "Financeiro"
    },
    "sat_rede": {
        "url": "/INTEGRACAO/SAT_REDE",
        "key": "sat_rede",
        "category": "Vendas & NF"
    },
    "produto_meta": {
        "url": "/INTEGRACAO/PRODUTO_META",
        "key": "produto_meta",
        "category": "Produtos"
    },
    "produto_lmc": {
        "url": "/INTEGRACAO/PRODUTO_LMC",
        "key": "produto_lmc",
        "category": "Produtos"
    },
    "codigo_barras": {
        "url": "/INTEGRACAO/CODIGO_BARRAS",
        "key": "codigo_barras",
        "category": "Produtos"
    },
    "consultar_caixa_rede": {
        "url": "/INTEGRACAO/CONSULTAR_CAIXA_REDE",
        "key": "consultar_caixa_rede",
        "category": "Financeiro"
    },
    "consultar_caixa_apresentado_rede": {
        "url": "/INTEGRACAO/CONSULTAR_CAIXA_APRESENTADO_REDE",
        "key": "consultar_caixa_apresentado_rede",
        "category": "Financeiro"
    }
}

async def probe_endpoint_directly(client: WebPostoClient, path: str, params: Dict[str, Any]) -> tuple[int, Any]:
    import httpx
    final_params = client._with_key(params)
    url_path = path if path.startswith("/") else f"/{path}"
    
    # We build an AsyncClient to test exactly raw path
    async with httpx.AsyncClient(base_url=client.config.webposto_base_url, timeout=20.0) as http_client:
        try:
            response = await http_client.get(url_path, params=final_params)
            status = response.status_code
            try:
                payload = response.json()
            except Exception:
                payload = response.text[:1000]
            return status, payload
        except Exception as e:
            return 0, str(e)

async def run_detailed_audit():
    client = WebPostoClient()
    service = NetworkFinancialOverviewService(client)
    
    print("="*60)
    print("LOGOS SPACE — SPRINT 20 AUDITORIA DE ENDPOINTS DE REDE WEBPOSTO")
    print("="*60)
    
    params = {
        "dataInicial": "2026-06-01",
        "dataFinal": "2026-06-07"
    }
    
    audit_results = []
    
    for nickname, info in REDE_ENDPOINTS.items():
        path = info["url"]
        print(f"\nProbing {nickname} at {path}...")
        
        # Test directly
        status, payload = await probe_endpoint_directly(client, path, params)
        print(f"HTTP Status: {status}")
        
        # Process rows and extract company list
        rows = []
        if status == 200:
            rows = client._extract_rows(payload)
            print(f"Total registros retornados: {len(rows)}")
        else:
            print(f"Failed or Non-200. Payload size/type: {type(payload)}")
            
        empresas_encontradas = set()
        possui_empresa_codigo = False
        possui_ultimo_codigo = False
        
        if status == 200 and isinstance(payload, dict):
            possui_ultimo_codigo = "ultimoCodigo" in payload
            
        for r in rows:
            if not isinstance(r, dict):
                continue
            # Search for company ID keys
            for key in ["empresaCodigo", "empresa", "codigoEmpresa", "filial", "empresa_codigo", "codEmpresa"]:
                val = r.get(key)
                if val is not None:
                    possui_empresa_codigo = True
                    try:
                        # Sometimes 'filial' could be string, but if integer we count
                        if isinstance(val, int) or (isinstance(val, str) and val.isdigit()):
                            empresas_encontradas.add(int(val))
                    except ValueError:
                        pass
        
        co_list = list(empresas_encontradas)
        contem_5256 = 5256 in co_list
        contem_9 = 9 in co_list
        contem_7 = 7 in co_list
        
        obs_text = ""
        if status == 200:
            if len(rows) > 0:
                obs_text = f"Sucesso! Retornou {len(rows)} linhas."
                if co_list:
                    obs_text += f" Contém filiais: {co_list}."
            else:
                obs_text = "Sucesso, mas retornou lista vazia no período."
        elif status in (401, 403):
            obs_text = "Sem autorização ou credenciais inválidas para esta rota (HTTP 401/403)."
        elif status == 404:
            obs_text = "Endpoint inexistente, não suportado ou desativado na API upstream."
        else:
            obs_text = f"Erro retornado pela API upstream (HTTP {status})."
            
        res = {
            "endpoint": path.replace("/INTEGRACAO/", ""),
            "path": path,
            "httpStatus": status,
            "totalRegistros": len(rows),
            "empresasEncontradas": co_list,
            "contem5256": contem_5256,
            "contem9": contem_9,
            "contem7": contem_7,
            "possuiEmpresaCodigo": possui_empresa_codigo,
            "possuiUltimoCodigo": possui_ultimo_codigo,
            "observacao": obs_text
        }
        
        audit_results.append(res)
        
    print("\n" + "="*60)
    print("AUDIT RESULTS CONSOLIDATED JSON:")
    print("="*60)
    print(json.dumps(audit_results, indent=2, ensure_ascii=False))
    
    # Let's save a temp results json so another python/or ourselves can easily check it
    with open("diagnostico_resultado_rede.json", "w", encoding="utf-8") as f:
        json.dump(audit_results, f, indent=2, ensure_ascii=False)
    print("\nSaved diagnostics to 'diagnostico_resultado_rede.json'")

if __name__ == "__main__":
    asyncio.run(run_detailed_audit())
