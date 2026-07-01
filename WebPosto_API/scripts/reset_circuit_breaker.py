"""
Script para Resetar Circuit Breaker via API Admin
Usa endpoint existente: POST /api/v1/admin/circuit-breaker/reset
"""

import httpx
import json
import sys

BACKEND_URL = "http://127.0.0.1:8040"

def check_health():
    """Verifica se o backend está rodando"""
    print("\n[HEALTH] Verificando se backend esta rodando...")
    try:
        response = httpx.get(f"{BACKEND_URL}/health", timeout=5.0)
        print(f"[OK] Backend esta ONLINE (Status: {response.status_code})")
        return True
    except Exception as e:
        print(f"[ERRO] Backend NAO esta rodando: {e}")
        print(f"\nInicie o backend com:")
        print(f"  python -m uvicorn src.main:app --host 127.0.0.1 --port 8040 --reload")
        return False

def get_circuit_status():
    """Busca status atual do circuit breaker"""
    print("\n[STATUS] Buscando status do Circuit Breaker...")
    try:
        response = httpx.get(f"{BACKEND_URL}/api/v1/admin/circuit-breaker/status", timeout=5.0)
        data = response.json()
        
        if data.get("success"):
            status = data.get("data", {})
            endpoints = status.get("endpoints", {})
            summary = status.get("summary", {})
            
            print(f"\n[CIRCUIT BREAKER STATUS]")
            print(f"  Total de endpoints rastreados: {len(endpoints)}")
            
            # Mostrar apenas endpoints com problemas
            open_endpoints = {k: v for k, v in endpoints.items() if v == "OPEN"}
            half_open_endpoints = {k: v for k, v in endpoints.items() if v == "HALF_OPEN"}
            
            if open_endpoints:
                print(f"\n  [OPEN] Endpoints BLOQUEADOS: {len(open_endpoints)}")
                for ep, state in open_endpoints.items():
                    print(f"    - {ep}: {state}")
            
            if half_open_endpoints:
                print(f"\n  [HALF_OPEN] Endpoints em RECUPERACAO: {len(half_open_endpoints)}")
                for ep, state in half_open_endpoints.items():
                    print(f"    - {ep}: {state}")
            
            if not open_endpoints and not half_open_endpoints:
                print(f"  [OK] Todos os endpoints estao FECHADOS (funcionando normalmente)")
            
            print(f"\n  [SUMMARY]")
            for scope, counts in summary.items():
                print(f"    {scope}: {json.dumps(counts)}")
            
            return status
        else:
            print(f"[ERRO] Falha ao buscar status: {data.get('error')}")
            return None
    except Exception as e:
        print(f"[ERRO] Falha ao conectar: {e}")
        return None

def reset_circuit_breaker(scope="global"):
    """Reseta o circuit breaker"""
    print(f"\n[RESET] Resetando Circuit Breaker (scope: {scope})...")
    try:
        response = httpx.post(
            f"{BACKEND_URL}/api/v1/admin/circuit-breaker/reset",
            json={"scope": scope},
            timeout=5.0
        )
        data = response.json()
        
        if data.get("success"):
            result = data.get("data", {})
            endpoints = result.get("endpoints", [])
            print(f"[OK] Circuit Breaker resetado com SUCESSO!")
            print(f"  Scope: {result.get('scope')}")
            print(f"  Endpoints resetados: {len(endpoints)}")
            if endpoints:
                print(f"  Lista: {', '.join(endpoints[:10])}{'...' if len(endpoints) > 10 else ''}")
            return True
        else:
            error = data.get("error", {})
            print(f"[ERRO] Falha ao resetar: {error.get('message')}")
            return False
    except Exception as e:
        print(f"[ERRO] Falha ao conectar: {e}")
        return False

def main():
    print("="*80)
    print(" FERRAMENTA DE RESET DO CIRCUIT BREAKER")
    print("="*80)
    print(f"\nBackend URL: {BACKEND_URL}")
    
    # 1. Verificar se backend está rodando
    if not check_health():
        sys.exit(1)
    
    # 2. Mostrar status atual
    status_before = get_circuit_status()
    
    # 3. Perguntar se quer resetar
    print("\n" + "="*80)
    scope = "global"
    
    if len(sys.argv) > 1:
        scope = sys.argv[1]
        print(f"Resetando scope: {scope}")
    else:
        print("Use: python scripts/reset_circuit_breaker.py [scope]")
        print("  Scopes disponiveis: global, financial, sales, stock, products, operations")
        print("  Padrao: global (reseta TODOS os endpoints)")
    
    # 4. Resetar
    success = reset_circuit_breaker(scope)
    
    if success:
        # 5. Mostrar status depois
        print("\n" + "="*80)
        get_circuit_status()
        
        print("\n" + "="*80)
        print("[SUCESSO] Circuit Breaker resetado!")
        print("\nProximos passos:")
        print("  1. Testar endpoints financeiros:")
        print("     curl http://127.0.0.1:8040/v1/financial/overview")
        print("     curl http://127.0.0.1:8040/v1/financial/expenses")
        print("  2. Verificar frontend:")
        print("     http://127.0.0.1:8040/app/financial")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
