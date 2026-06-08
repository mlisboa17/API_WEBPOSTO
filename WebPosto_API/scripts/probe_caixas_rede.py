import asyncio
import sys
from pathlib import Path
import httpx
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.gateway.webposto_client import WebPostoClient

async def probe_all_caixa_rede():
    client = WebPostoClient()
    
    # Let's define the ranges to make sure we don't miss records if they exist somewhere
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    date_ranges = [
        {"dataInicial": yesterday, "dataFinal": yesterday},
        {"dataInicial": "2026-06-01", "dataFinal": "2026-06-07"},
        {"dataInicial": "2026-04-09", "dataFinal": "2026-04-09"},
    ]
    
    # Base candidates
    paths_to_verify = [
        # UPPERCASE variations (WebPosto classical)
        "/INTEGRACAO/CAIXA_REDE",
        "/INTEGRACAO/CONSULTAR_CAIXA_REDE",
        "/INTEGRACAO/CAIXA_REDE/RETORNO-PAGINADO",
        "/INTEGRACAO/CAIXA_APRESENTADO_REDE",
        "/INTEGRACAO/CONSULTAR_CAIXA_APRESENTADO_REDE",
        "/INTEGRACAO/CAIXA_APRESENTADO_REDE/RETORNO-PAGINADO",
        
        # LOWERCASE / MIXED CASE variations
        "/integracao/caixa_rede",
        "/integracao/caixa_rede/retorno-paginado",
        "/integracao/caixa_apresentado_rede",
        "/integracao/caixa_apresentado_rede/retorno-paginado",
        
        # Other potential aliases just in case
        "/INTEGRACAO/CONSULTAR_CAIXA_APRESENTADO",
        "/INTEGRACAO/CONSULTAR_CAIXA"
    ]
    
    print("="*80)
    print("PROBING INTEGRATION ENDPOINTS FOR CAIXA REDE AND CAIXA APRESENTADO REDE")
    print("="*80)
    
    results = []
    
    for path in paths_to_verify:
        print(f"\nPath: {path}")
        for dr in date_ranges:
            final_params = client._with_key(dr)
            baseUrl = client.config.webposto_base_url
            try:
                # We try both case-sensitive paths on the API
                async with httpx.AsyncClient(base_url=baseUrl, timeout=15.0) as http_client:
                    # Let's clean path manually to match exact input
                    response = await http_client.get(path, params=final_params)
                    status = response.status_code
                    print(f"  [{dr['dataInicial']}] HTTP Status: {status}")
                    
                    if status == 200:
                        try:
                            payload = response.json()
                            rows = client._extract_rows(payload)
                            print(f"  -> SUCCESS! Rows count: {len(rows)}")
                            
                            # Log companies
                            companies = set()
                            for r in rows:
                                if not isinstance(r, dict):
                                    continue
                                for key in ["empresaCodigo", "empresa", "codigoEmpresa", "filial", "empresa_codigo", "codEmpresa"]:
                                    val = r.get(key)
                                    if isinstance(val, int) or (isinstance(val, str) and val.isdigit()):
                                        companies.add(int(val))
                            
                            results.append({
                                "path": path,
                                "date_range": dr,
                                "status": status,
                                "rows_count": len(rows),
                                "companies": list(companies),
                                "sample": rows[0] if rows else None,
                                "success": True
                            })
                            
                            # Imprime os detalhes de todos os registros
                            print(f"  Rows detailed: ")
                            for idx, r in enumerate(rows):
                                print(f"    Row #{idx+1}: {r}")
                            
                        except Exception as je:
                            print(f"  -> SUCCESS (Non-JSON or parse error): {je}")
                            results.append({
                                "path": path,
                                "date_range": dr,
                                "status": status,
                                "rows_count": 0,
                                "success": True,
                                "notes": "Response text snippet: " + response.text[:200]
                            })
                    elif status in (401, 403, 404):
                        # Don't flood output for 404/401 unless we want to, but keep record
                        results.append({
                            "path": path,
                            "date_range": dr,
                            "status": status,
                            "rows_count": 0,
                            "success": False
                        })
                    else:
                        print(f"  -> ERROR HTTP {status}: {response.text[:200]}")
                        results.append({
                            "path": path,
                            "date_range": dr,
                            "status": status,
                            "rows_count": 0,
                            "success": False
                        })
            except Exception as e:
                print(f"  -> Connection Exception: {e}")
                results.append({
                    "path": path,
                    "date_range": dr,
                    "status": 0,
                    "rows_count": 0,
                    "success": False,
                    "error": str(e)
                })
                
    # Filter interesting ones
    success_endpoints = [r for r in results if r["status"] == 200]
    print("\n" + "="*80)
    print("SUCCESSFUL ENDPOINTS DISCOVERED:")
    print("="*80)
    for s in success_endpoints:
        print(f"Path: {s['path']} | Date: {s['date_range']['dataInicial']} | Rows: {s['rows_count']} | Companies: {s['companies']}")

if __name__ == "__main__":
    asyncio.run(probe_all_caixa_rede())
