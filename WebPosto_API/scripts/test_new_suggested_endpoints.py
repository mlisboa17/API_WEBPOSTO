import asyncio
import sys
from pathlib import Path
from datetime import date, timedelta
import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.gateway.webposto_client import WebPostoClient

async def test_candidate_endpoints():
    client = WebPostoClient()
    
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    today = date.today().isoformat()
    
    date_ranges = [
        {"dataInicial": yesterday, "dataFinal": yesterday},
        {"dataInicial": "2026-06-01", "dataFinal": "2026-06-07"},
        {"dataInicial": "2026-04-09", "dataFinal": "2026-04-09"},
    ]
    
    endpoints = {
        "TITULO_PAGAR (Individual)": "/INTEGRACAO/TITULO_PAGAR",
        "CONSULTAR_TITULO_PAGAR_REDE": "/INTEGRACAO/CONSULTAR_TITULO_PAGAR_REDE",
        "CAIXA_APRESENTADO (Individual)": "/INTEGRACAO/CAIXA_APRESENTADO",
        "CONSULTAR_CAIXA_APRESENTADO_REDE": "/INTEGRACAO/CONSULTAR_CAIXA_APRESENTADO_REDE"
    }
    
    for name, path in endpoints.items():
        print(f"\n===== Testing {name} ({path}) =====")
        for dr in date_ranges:
            print(f"Testing date range: {dr['dataInicial']} to {dr['dataFinal']}...")
            final_params = client._with_key(dr)
            
            try:
                async with httpx.AsyncClient(base_url=client.config.webposto_base_url, timeout=20.0) as http_client:
                    response = await http_client.get(path, params=final_params)
                    status = response.status_code
                    print(f"  HTTP Status: {status}")
                    
                    if status == 200:
                        try:
                            payload = response.json()
                            rows = client._extract_rows(payload)
                            print(f"  Total rows: {len(rows)}")
                            if rows:
                                print(f"  Sample row: {rows[0]}")
                                companies = set()
                                for r in rows:
                                    if not isinstance(r, dict):
                                        continue
                                    for key in ["empresaCodigo", "empresa", "codigoEmpresa", "filial", "empresa_codigo", "codEmpresa"]:
                                        val = r.get(key)
                                        if isinstance(val, int) or (isinstance(val, str) and val.isdigit()):
                                            companies.add(int(val))
                                print(f"  Unique companies: {list(companies)}")
                        except Exception as json_err:
                            print(f"  Failed to parse JSON: {json_err}. Snippet: {response.text[:200]}")
                    else:
                        print(f"  Non-200. Snippet: {response.text[:200]}")
            except Exception as conn_err:
                print(f"  Connection error: {conn_err}")

if __name__ == "__main__":
    asyncio.run(test_candidate_endpoints())
