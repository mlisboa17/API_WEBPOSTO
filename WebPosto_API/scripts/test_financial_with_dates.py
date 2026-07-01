"""
Teste dos Endpoints Financeiros COM Datas
"""

import httpx
import json
from datetime import date, timedelta

BACKEND_URL = "http://127.0.0.1:8040"

def test_with_dates(path):
    """Testa endpoint com dataInicial e dataFinal"""
    url = f"{BACKEND_URL}{path}"
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    
    print(f"\n{'='*80}")
    print(f"Endpoint: {path}")
    print(f"{'='*80}")
    
    # Teste 1: Datas de hoje
    print(f"\n[TESTE 1] dataInicial={today}, dataFinal={today}")
    try:
        response = httpx.get(
            url,
            params={"dataInicial": today, "dataFinal": today},
            timeout=120.0
        )
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Success: {data.get('success')}")
            error = data.get('error')
            
            if error:
                print(f"  [ERRO] Type: {error.get('type')}")
                print(f"  [ERRO] Message: {error.get('message')}")
            else:
                print(f"  [OK] Dados recebidos!")
                data_obj = data.get('data', {})
                print(f"  [INFO] Tipo de data: {type(data_obj).__name__}")
                
                if isinstance(data_obj, dict):
                    print(f"  [INFO] Chaves ({len(data_obj)}):")
                    for key in list(data_obj.keys())[:15]:
                        val = data_obj[key]
                        if isinstance(val, list):
                            print(f"    - {key}: list com {len(val)} itens")
                        elif isinstance(val, dict):
                            print(f"    - {key}: dict com {len(val)} chaves")
                        else:
                            val_str = str(val)
                            if len(val_str) > 50:
                                val_str = val_str[:50] + "..."
                            print(f"    - {key}: {val_str}")
                elif isinstance(data_obj, list):
                    print(f"  [INFO] Array com {len(data_obj)} itens")
                
                # Mostrar JSON resumido
                json_str = json.dumps(data, indent=2, ensure_ascii=False)
                if len(json_str) > 1500:
                    print(f"\n[JSON] Primeiros 1500 caracteres:")
                    print(json_str[:1500] + "\n...")
                else:
                    print(f"\n[JSON] Completo:")
                    print(json_str)
        else:
            print(f"  [ERRO] Resposta:")
            print(f"  {response.text[:500]}")
    
    except httpx.TimeoutException:
        print(f"  [TIMEOUT] Excedeu 120s")
    except Exception as e:
        print(f"  [ERRO] {type(e).__name__}: {e}")

def main():
    print("="*80)
    print(" TESTE DOS ENDPOINTS FINANCEIROS COM DATAS")
    print("="*80)
    print(f"\nData de hoje: {date.today().isoformat()}")
    
    # Verificar se backend está rodando
    try:
        response = httpx.get(f"{BACKEND_URL}/health", timeout=5.0)
        if response.status_code == 200:
            print(f"[OK] Backend ONLINE")
        else:
            print(f"[ERRO] Backend retornou {response.status_code}")
            return
    except Exception as e:
        print(f"[ERRO] Backend NAO esta rodando: {e}")
        return
    
    # Testar endpoints
    test_with_dates("/v1/financial/overview")
    test_with_dates("/v1/financial/expenses")
    
    print(f"\n{'='*80}")
    print(" FIM DOS TESTES")
    print("="*80)

if __name__ == "__main__":
    main()
