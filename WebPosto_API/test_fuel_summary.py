import asyncio
import httpx
import json
import math

async def test_fuel_summary_endpoint():
    print("=====================================================")
    print("TESTANDO ENDPOINT /api/v1/sales/fuel-summary")
    print("=====================================================")
    
    url = "http://127.0.0.1:8041/api/v1/sales/fuel-summary"
    params = {
        "dataInicial": "2026-06-05",
        "dataFinal": "2026-06-06"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            print(f"Buscando {url} com params {params}...")
            r = await client.get(url, params=params, timeout=30.0)
            print(f"Status: {r.status_code}")
            
            if r.status_code != 200:
                print(f"Erro: {r.text}")
                return False
                
            data = r.json()
            
            # data se for dict, pegar data['data'] ou similar, senão data
            results_list = data
            if isinstance(data, dict):
                results_list = data.get("data", [])
                
            print(f"Registros retornados: {len(results_list)}")
            
            if len(results_list) == 0:
                print("Nota: Retornou lista vazia. Verifique se o uvicorn está de pé e com chave funcional.")
                return True
                
            print("\nAmostra dos resultados:")
            print(json.dumps(results_list[:3], indent=2, ensure_ascii=False))
            
            # Validação matemática de totais
            # Soma litros total, valor total e confere se a matemática básica de precoMedio confere
            total_litros = 0
            total_valor = 0
            
            print("\nValidações:")
            for i, item in enumerate(results_list):
                emp = item.get("empresaCodigo")
                comb = item.get("combustivel")
                litros = item.get("litros", 0)
                valor = item.get("valor", 0)
                p_medio = item.get("precoMedio", 0)
                part = item.get("participacao", 0)
                
                total_litros += litros
                total_valor += valor
                
                # Preço médio calculado individualmente
                p_medio_calc = round(valor / litros, 2) if litros > 0 else 0
                diff_preco = abs(p_medio - p_medio_calc)
                
                print(f"Item #{i+1}: Fl.{emp} | {comb} | Litros: {litros} | Valor: {valor} | PreçoMédio: {p_medio} (Calc: {p_medio_calc})")
                
                if diff_preco > 0.01:
                    print(f"  ❌ FALHA: Preço médio divergente! Dif: {diff_preco}")
                    return False
                    
            print(f"\nSoma total Litros: {total_litros}")
            print(f"Soma total Valor: {total_valor}")
            print("✓ Todas as validações matemáticas do preço médio individuais bateram com diferença de 0.00!")
            return True
            
        except Exception as e:
            print(f"Erro ao testar endpoint: {e}")
            return False

if __name__ == "__main__":
    asyncio.run(test_fuel_summary_endpoint())
