"""
Script de Teste Direto da API WebPosto
Testa endpoint de despesas sem passar pelo Circuit Breaker
"""

import asyncio
import httpx
import os
from dotenv import load_dotenv
from datetime import date
import json

load_dotenv()

WEBPOSTO_BASE_URL = os.getenv("WEBPOSTO_BASE_URL", "https://api.quality.inf.br")
WEBPOSTO_API_KEY = os.getenv("WEBPOSTO_API_KEY")

# Endpoints a testar
ENDPOINTS_TO_TEST = {
    "despesas_financeiro_rede": "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
    "titulo_pagar": "/INTEGRACAO/TITULO_PAGAR",
    "venda": "/INTEGRACAO/VENDA",
}

async def test_endpoint(endpoint_name: str, endpoint_path: str):
    """Testa um endpoint diretamente"""
    print(f"\n{'='*80}")
    print(f"Testando: {endpoint_name}")
    print(f"Path: {endpoint_path}")
    print(f"{'='*80}")
    
    if not WEBPOSTO_API_KEY:
        print("[ERRO] WEBPOSTO_API_KEY nao configurada no .env")
        return
    
    # Parâmetros com data de hoje
    today = date.today().isoformat()
    params = {
        "CHAVE": WEBPOSTO_API_KEY,
        "dataInicial": today,
        "dataFinal": today,
    }
    
    # Para endpoint de despesas, remover data (endpoint analítico)
    if "despesas_financeiro_rede" in endpoint_name.lower():
        params = {"CHAVE": WEBPOSTO_API_KEY}
    
    url = f"{WEBPOSTO_BASE_URL}{endpoint_path}"
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            print(f"[INFO] Fazendo requisicao...")
            print(f"   URL: {url}")
            print(f"   Params: {{{', '.join([f'{k}: ...' if k == 'CHAVE' else f'{k}: {v}' for k, v in params.items()])}}}")
            
            response = await client.get(url, params=params)
            
            print(f"\n[RESPOSTA]:")
            print(f"   Status: {response.status_code}")
            print(f"   Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Tentar extrair dados
                    rows = []
                    if isinstance(data, list):
                        rows = data
                    elif isinstance(data, dict):
                        if "resultados" in data:
                            rows = data["resultados"]
                        elif "data" in data:
                            rows = data["data"]
                    
                    print(f"   [OK] SUCESSO!")
                    print(f"   Tipo de payload: {type(data).__name__}")
                    print(f"   Registros encontrados: {len(rows)}")
                    
                    if rows:
                        print(f"\n   [DATA] Exemplo de registro (primeiro):")
                        print(f"   {json.dumps(rows[0], indent=2, ensure_ascii=False)[:500]}...")
                    else:
                        print(f"   [WARN] Payload vazio (mas requisicao bem-sucedida)")
                        print(f"   Estrutura: {list(data.keys()) if isinstance(data, dict) else 'array'}")
                    
                except Exception as e:
                    print(f"   [WARN] Erro ao parsear JSON: {e}")
                    print(f"   Raw response: {response.text[:500]}")
            
            elif response.status_code == 401:
                print(f"   [ERRO] NAO AUTORIZADO")
                print(f"   Possivel causa: Chave API invalida ou sem permissao para este endpoint")
                print(f"   Response: {response.text[:500]}")
            
            elif response.status_code == 400:
                print(f"   [WARN] BAD REQUEST")
                print(f"   Possivel causa: Parametros invalidos")
                print(f"   Response: {response.text[:500]}")
            
            elif response.status_code == 500:
                print(f"   [ERRO] ERRO NO SERVIDOR WebPosto")
                print(f"   Response: {response.text[:500]}")
            
            else:
                print(f"   [ERRO] ERRO INESPERADO")
                print(f"   Response: {response.text[:500]}")
            
    except httpx.TimeoutException:
        print(f"   [ERRO] TIMEOUT (>60s)")
        print(f"   Endpoint pode estar lento ou indisponivel")
    
    except Exception as e:
        print(f"   [ERRO] ERRO DE REDE/CONEXAO")
        print(f"   Erro: {type(e).__name__}: {str(e)}")


async def main():
    print("\n" + "="*80)
    print(" TESTE DIRETO DA API WEBPOSTO")
    print("="*80)
    print(f"\nBase URL: {WEBPOSTO_BASE_URL}")
    print(f"Chave configurada: {'[OK] SIM' if WEBPOSTO_API_KEY else '[ERRO] NAO'}")
    
    if not WEBPOSTO_API_KEY:
        print("\n[ERRO] Configure WEBPOSTO_API_KEY no arquivo .env")
        return
    
    # Testar cada endpoint
    for name, path in ENDPOINTS_TO_TEST.items():
        await test_endpoint(name, path)
    
    print(f"\n{'='*80}")
    print(" RESUMO")
    print("="*80)
    print("\nSe todos os endpoints retornarem 200:")
    print("  -> O problema esta no Circuit Breaker do backend")
    print("  -> Solucao: Resetar o circuit breaker")
    print("\nSe algum endpoint retornar 401:")
    print("  -> O problema e de permissao/autenticacao")
    print("  -> Solucao: Verificar WEBPOSTO_API_KEY no .env")
    print("\nSe algum endpoint retornar timeout:")
    print("  -> O problema e de performance/disponibilidade")
    print("  -> Solucao: Aumentar timeout ou verificar WebPosto")


if __name__ == "__main__":
    asyncio.run(main())
