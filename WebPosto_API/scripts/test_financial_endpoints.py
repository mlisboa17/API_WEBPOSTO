"""
Teste Simplificado dos Endpoints Financeiros
"""

import httpx
import json
import sys

BACKEND_URL = "http://127.0.0.1:8040"

def test_endpoint(path, timeout=120):
    """Testa um endpoint com timeout configurável"""
    url = f"{BACKEND_URL}{path}"
    print(f"\n{'='*80}")
    print(f"Testando: {path}")
    print(f"{'='*80}")
    print(f"URL: {url}")
    print(f"Timeout: {timeout}s")
    print(f"\n[INFO] Fazendo requisicao...")
    
    try:
        response = httpx.get(url, timeout=timeout)
        print(f"\n[RESPOSTA]")
        print(f"  Status: {response.status_code}")
        print(f"  Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"\n[OK] Resposta recebida!")
                print(f"  Success: {data.get('success')}")
                print(f"  Error: {data.get('error')}")
                
                if data.get('error'):
                    error = data['error']
                    print(f"\n[ERRO DETECTADO]")
                    print(f"  Type: {error.get('type')}")
                    print(f"  Message: {error.get('message')}")
                else:
                    print(f"\n[DADOS]")
                    data_obj = data.get('data', {})
                    if isinstance(data_obj, dict):
                        for key in list(data_obj.keys())[:10]:
                            val = data_obj[key]
                            if isinstance(val, (list, dict)):
                                print(f"  {key}: {type(val).__name__} (len={len(val) if hasattr(val, '__len__') else 'N/A'})")
                            else:
                                print(f"  {key}: {val}")
                    else:
                        print(f"  Tipo: {type(data_obj).__name__}")
                        print(f"  Conteudo: {str(data_obj)[:200]}")
                
                print(f"\n[JSON COMPLETO (primeiros 1000 chars)]")
                print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
                
            except Exception as e:
                print(f"\n[ERRO] Falha ao parsear JSON: {e}")
                print(f"  Raw: {response.text[:500]}")
        else:
            print(f"\n[ERRO] Status nao-200")
            print(f"  Response: {response.text[:500]}")
            
    except httpx.TimeoutException:
        print(f"\n[TIMEOUT] Requisicao excedeu {timeout}s")
        print(f"  Possivel causa: Endpoint muito lento ou WebPosto indisponivel")
        return False
    except Exception as e:
        print(f"\n[ERRO] Falha na requisicao: {type(e).__name__}: {e}")
        return False
    
    return True

def main():
    print("="*80)
    print(" TESTE DOS ENDPOINTS FINANCEIROS")
    print("="*80)
    
    # Testar health primeiro
    print(f"\n[HEALTH] Testando conectividade...")
    try:
        response = httpx.get(f"{BACKEND_URL}/health", timeout=5.0)
        if response.status_code == 200:
            print(f"[OK] Backend esta ONLINE")
        else:
            print(f"[ERRO] Backend retornou status {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"[ERRO] Backend NAO esta rodando: {e}")
        sys.exit(1)
    
    # Testar endpoints
    endpoints = [
        "/v1/financial/overview",
        "/v1/financial/expenses",
    ]
    
    for endpoint in endpoints:
        test_endpoint(endpoint, timeout=120)
    
    print(f"\n{'='*80}")
    print(" FIM DOS TESTES")
    print("="*80)

if __name__ == "__main__":
    main()
