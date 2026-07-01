"""
Script de Teste: Business Analyst Endpoints
Valida as rotas do módulo de análise executiva
"""

import httpx
import asyncio
from datetime import date


BACKEND_URL = "http://127.0.0.1:8040"


async def test_endpoints():
    """Testa todos os endpoints do Business Analyst"""
    
    print("="*80)
    print(" TESTE: BUSINESS ANALYST MODULE")
    print("="*80)
    
    async with httpx.AsyncClient() as client:
        # 1. Health Check
        print("\n[1/4] Verificando backend...")
        try:
            r = await client.get(f"{BACKEND_URL}/health", timeout=5.0)
            if r.status_code == 200:
                print("  [OK] Backend online")
            else:
                print(f"  [ERRO] Status {r.status_code}")
                return
        except Exception as e:
            print(f"  [ERRO] Backend offline: {e}")
            return
        
        # 2. Daily Report
        print("\n[2/4] Testando Daily Report...")
        try:
            r = await client.get(
                f"{BACKEND_URL}/v1/business-analyst/daily",
                timeout=30.0
            )
            print(f"  Status: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                print(f"  Success: {data.get('success')}")
                print(f"  Tenant: {data.get('tenant')}")
                print(f"  Health Score: {data.get('health_score', {}).get('overall_score')}")
                print(f"  Classification: {data.get('health_score', {}).get('classification')}")
                print(f"  Risks: {len(data.get('risks', []))}")
                print(f"  Opportunities: {len(data.get('opportunities', []))}")
        except Exception as e:
            print(f"  [ERRO] {e}")
        
        # 3. Health Score
        print("\n[3/4] Testando Health Score...")
        try:
            r = await client.get(
                f"{BACKEND_URL}/v1/business-analyst/health-score",
                timeout=10.0
            )
            print(f"  Status: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                print(f"  Score: {data.get('overall_score')}/100")
                print(f"  Classification: {data.get('classification')}")
                components = data.get('components', {})
                print(f"  Components:")
                for key, value in components.items():
                    print(f"    - {key}: {value}")
        except Exception as e:
            print(f"  [ERRO] {e}")
        
        # 4. Payloads
        print("\n[4/4] Testando Payloads...")
        try:
            r = await client.get(
                f"{BACKEND_URL}/v1/business-analyst/payloads",
                timeout=30.0
            )
            print(f"  Status: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                payloads = data.get('payloads', {})
                print(f"  Telegram: {len(payloads.get('telegram', {}).get('content', ''))} chars")
                print(f"  Discord: {len(str(payloads.get('discord', {}).get('content', '')))} chars")
                print(f"  Email: {len(payloads.get('email', {}).get('content', ''))} chars")
        except Exception as e:
            print(f"  [ERRO] {e}")
    
    print("\n" + "="*80)
    print(" RESUMO")
    print("="*80)
    print("\nEndpoints testados:")
    print("  - GET /v1/business-analyst/daily")
    print("  - GET /v1/business-analyst/health-score")
    print("  - GET /v1/business-analyst/payloads")
    print("\nValidar manualmente no navegador:")
    print("  http://127.0.0.1:8040/v1/business-analyst/daily")
    print("  http://127.0.0.1:8040/v1/business-analyst/health-score")


if __name__ == "__main__":
    asyncio.run(test_endpoints())
