"""
Teste Completo: Endpoints WebPosto com Requisitos de Data
Valida endpoints COM e SEM parâmetros de data
"""

import asyncio
import httpx
from datetime import date
from typing import Any

# Importar contratos (se disponível)
try:
    import sys
    sys.path.insert(0, ".")
    from src.gateway.webposto_endpoint_contracts import (
        get_endpoints_by_date_requirement,
        WEBPOSTO_ENDPOINT_CONTRACTS,
    )
    CONTRACTS_AVAILABLE = True
except ImportError:
    CONTRACTS_AVAILABLE = False
    print("[WARN] Não foi possível importar contratos. Usando lista hardcoded.")

# Fallback se não conseguir importar
ENDPOINTS_REQUIRING_DATES_FALLBACK = {
    "abastecimento",
    "financeiro",
    "titulo_receber",
    "movimento_conta",
    "transferencia_bancaria",
    "caixa",
    "caixa_apresentado",
    "caixa_rede",
    "caixa_apresentado_rede",
    "despesas_financeiro_rede",
    "venda",
    "venda_item",
    "venda_item_rede",
    "venda_forma_pagamento",
    "venda_forma_pagamento_rede",
    "nfce",
    "produto_estoque",
    "estoque_periodo",
    "lmc_rede",
}

ENDPOINTS_WITHOUT_DATES_FALLBACK = {
    "empresas",
    "conta",
    "produto",
    "produto_empresa",
    "produto_rede",
    "produto_empresa_rede",
    "produto_combustivel",
    "tanque",
    "funcionario",
    "analise_vendas_combustivel",
}

def get_endpoint_lists():
    """Retorna listas de endpoints que exigem e não exigem datas"""
    if CONTRACTS_AVAILABLE:
        try:
            requires, not_requires = get_endpoints_by_date_requirement()
            return requires, not_requires
        except Exception:
            pass
    return ENDPOINTS_REQUIRING_DATES_FALLBACK, ENDPOINTS_WITHOUT_DATES_FALLBACK


async def test_backend_endpoint(
    client: httpx.AsyncClient,
    endpoint_path: str,
    params: dict[str, Any],
    description: str,
) -> tuple[int, dict[str, Any] | None, str]:
    """
    Testa um endpoint do backend FastAPI.
    Retorna: (status_code, response_data, error_message)
    """
    try:
        url = f"http://127.0.0.1:8040{endpoint_path}"
        response = await client.get(url, params=params, timeout=60.0)
        
        try:
            data = response.json()
        except Exception:
            data = {"raw": response.text[:200]}
        
        return response.status_code, data, ""
    
    except httpx.TimeoutException:
        return 0, None, "TIMEOUT (>60s)"
    except Exception as e:
        return 0, None, f"{type(e).__name__}: {str(e)[:100]}"


async def main():
    print("="*80)
    print(" TESTE COMPLETO: ENDPOINTS WEBPOSTO - REQUISITOS DE DATA")
    print("="*80)
    
    today = date.today().isoformat()
    endpoints_with_dates, endpoints_without_dates = get_endpoint_lists()
    
    print(f"\nData de teste: {today}")
    print(f"\nEndpoints que EXIGEM datas: {len(endpoints_with_dates)}")
    print(f"Endpoints que NAO exigem datas: {len(endpoints_without_dates)}")
    
    # Verificar se backend está rodando
    async with httpx.AsyncClient() as client:
        print(f"\n[HEALTH CHECK]")
        try:
            response = await client.get("http://127.0.0.1:8040/health", timeout=5.0)
            if response.status_code == 200:
                print(f"  [OK] Backend ONLINE")
            else:
                print(f"  [ERRO] Backend retornou {response.status_code}")
                print(f"\nInicie o backend:")
                print(f"  python src/main.py")
                return
        except Exception as e:
            print(f"  [ERRO] Backend NAO esta rodando: {e}")
            print(f"\nInicie o backend:")
            print(f"  python src/main.py")
            return
        
        # Teste 1: Endpoints financeiros principais
        print(f"\n{'='*80}")
        print(" TESTE 1: ENDPOINTS FINANCEIROS PRINCIPAIS")
        print("="*80)
        
        financial_tests = [
            ("/v1/financial/overview", "Financial Overview"),
            ("/v1/financial/expenses", "Financial Expenses"),
        ]
        
        for endpoint_path, desc in financial_tests:
            print(f"\n[{desc}]")
            print(f"  Endpoint: {endpoint_path}")
            
            # Com datas
            params_with_dates = {"dataInicial": today, "dataFinal": today}
            status, data, error = await test_backend_endpoint(
                client, endpoint_path, params_with_dates, desc
            )
            
            print(f"  Status: {status}")
            
            if status == 200:
                print(f"  [OK] Sucesso!")
                if data:
                    success = data.get("success")
                    error_obj = data.get("error")
                    print(f"  Response.success: {success}")
                    if error_obj:
                        print(f"  Response.error.type: {error_obj.get('type')}")
                        print(f"  Response.error.message: {error_obj.get('message')[:100]}")
                    else:
                        data_obj = data.get("data")
                        if isinstance(data_obj, dict):
                            print(f"  Response.data keys: {list(data_obj.keys())[:10]}")
                        elif isinstance(data_obj, list):
                            print(f"  Response.data: array com {len(data_obj)} itens")
            elif status == 422:
                print(f"  [ERRO] Validation Error (422)")
                if data and "detail" in data:
                    for detail in data["detail"][:3]:
                        print(f"    - {detail}")
            elif status == 0:
                print(f"  [ERRO] {error}")
            else:
                print(f"  [ERRO] Status nao esperado")
                if data:
                    print(f"  Response: {str(data)[:200]}")
        
        # Teste 2: WebPosto API diretamente (via backend snapshot)
        print(f"\n{'='*80}")
        print(" TESTE 2: CATEGORIZAÇÃO DOS ENDPOINTS")
        print("="*80)
        
        print(f"\n[ENDPOINTS QUE EXIGEM DATAS] ({len(endpoints_with_dates)} total)")
        for ep in sorted(endpoints_with_dates):
            contract = WEBPOSTO_ENDPOINT_CONTRACTS.get(ep) if CONTRACTS_AVAILABLE else None
            desc = contract.description if contract else "N/A"
            print(f"  - {ep:30s} | {desc}")
        
        print(f"\n[ENDPOINTS QUE NAO EXIGEM DATAS] ({len(endpoints_without_dates)} total)")
        for ep in sorted(endpoints_without_dates):
            contract = WEBPOSTO_ENDPOINT_CONTRACTS.get(ep) if CONTRACTS_AVAILABLE else None
            desc = contract.description if contract else "N/A"
            print(f"  - {ep:30s} | {desc}")
        
        # Teste 3: Circuit Breaker Status
        print(f"\n{'='*80}")
        print(" TESTE 3: CIRCUIT BREAKER STATUS")
        print("="*80)
        
        try:
            response = await client.get(
                "http://127.0.0.1:8040/api/v1/admin/circuit-breaker/status",
                timeout=5.0
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    status_data = data.get("data", {})
                    endpoints_status = status_data.get("endpoints", {})
                    summary = status_data.get("summary", {})
                    
                    open_endpoints = {k: v for k, v in endpoints_status.items() if v == "OPEN"}
                    half_open_endpoints = {k: v for k, v in endpoints_status.items() if v == "HALF_OPEN"}
                    
                    print(f"\n[OK] Circuit Breaker operacional")
                    print(f"  Total de endpoints rastreados: {len(endpoints_status)}")
                    
                    if open_endpoints:
                        print(f"\n  [ALERTA] Endpoints BLOQUEADOS: {len(open_endpoints)}")
                        for ep in list(open_endpoints.keys())[:5]:
                            print(f"    - {ep}")
                    else:
                        print(f"  [OK] Nenhum endpoint bloqueado")
                    
                    if half_open_endpoints:
                        print(f"\n  [WARN] Endpoints em RECUPERACAO: {len(half_open_endpoints)}")
                        for ep in list(half_open_endpoints.keys())[:5]:
                            print(f"    - {ep}")
                    
                    print(f"\n  [SUMMARY]")
                    for scope, counts in summary.items():
                        print(f"    {scope:15s}: {counts}")
                else:
                    print(f"  [ERRO] {data.get('error')}")
            else:
                print(f"  [ERRO] Status {response.status_code}")
        except Exception as e:
            print(f"  [ERRO] Falha ao consultar circuit breaker: {e}")
    
    # Resumo Final
    print(f"\n{'='*80}")
    print(" RESUMO FINAL")
    print("="*80)
    print(f"\nEndpoints catalogados:")
    print(f"  - Exigem datas: {len(endpoints_with_dates)}")
    print(f"  - Nao exigem datas: {len(endpoints_without_dates)}")
    print(f"\nProximos passos:")
    print(f"  1. Se endpoints retornaram CIRCUIT_OPEN:")
    print(f"     python scripts/reset_circuit_breaker.py")
    print(f"  2. Validar frontend:")
    print(f"     http://127.0.0.1:8040/app/financial")


if __name__ == "__main__":
    asyncio.run(main())
