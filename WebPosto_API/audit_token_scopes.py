import os
import json
import httpx
import asyncio

# Carregar arquivo .env
def load_env():
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")

load_env()

BASE_URL = os.getenv("WEBPOSTO_BASE_URL", "https://web.qualityautomacao.com.br")
CHAVE = os.getenv("WEBPOSTO_API_KEY", "").strip()
if not CHAVE:
    raise SystemExit("WEBPOSTO_API_KEY não definida. Copie .env.example para .env e configure a chave.")

# Empresas a serem testadas (conforme solicitação)
EMPRESAS_TESTE = [5256, 5333, 5555, 5556, 5557, 5559, 5560, 11495, 46433, 74014]

# Datas de teste onde sabemos que há dados de movimentação no Posto VIP
DATA_INI = "2026-06-05"
DATA_FIM = "2026-06-05"

# Endpoints a serem testados
ENDPOINTS_MAPPING = {
    "DESPESAS_REDE": "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
    "VENDA_ITEM": "/INTEGRACAO/VENDA_ITEM",
    "VENDA_ITEM_REDE": "/INTEGRACAO/CONSULTAR_VENDA_ITEM_REDE",
    "VENDA_REDE": "/INTEGRACAO/VENDA_REDE",
    "CAIXA_REDE": "/INTEGRACAO/CONSULTAR_CAIXA_REDE",
    "CAIXA_APRESENTADO_REDE": "/INTEGRACAO/CONSULTAR_CAIXA_APRESENTADO_REDE",
    "PRODUTO_ESTOQUE": "/INTEGRACAO/PRODUTO_ESTOQUE",
    "PRODUTO_EMPRESA": "/INTEGRACAO/PRODUTO_EMPRESA",
    "ABASTECIMENTO": "/INTEGRACAO/ABASTECIMENTO",
    "LMC_REDE": "/INTEGRACAO/LMC_REDE"
}

# Alguns endpoints podem ser _REDE mas aceitam empresaCodigo como filtro opcional.
# Alguns são específicos por filial e exigem obrigatoriamente empresaCodigo.
# Vamos passar o empresaCodigo como query parameter em todos e ver como a API se comporta.

async def test_endpoint(client, name, path, emp_cod):
    # Definir parâmetros base
    params = {
        "CHAVE": CHAVE,
        "empresaCodigo": emp_cod,
    }
    
    # Endpoints que usam intervalo de datas
    if name in ["DESPESAS_REDE", "VENDA_ITEM", "VENDA_ITEM_REDE", "VENDA_REDE", "CAIXA_REDE", "CAIXA_APRESENTADO_REDE", "PRODUTO_ESTOQUE", "ABASTECIMENTO", "LMC_REDE"]:
        params["dataInicial"] = DATA_INI
        params["dataFinal"] = DATA_FIM
        
    url = f"{BASE_URL}{path}"
    
    try:
        r = await client.get(url, params=params, timeout=15.0)
        status = r.status_code
        
        # Mapeando resposta do WebPosto redirecionamento ou erro
        if status != 200:
            return {
                "endpoint": name,
                "empresaCodigo": emp_cod,
                "httpStatus": status,
                "registros": 0,
                "possuiDados": False,
                "observacao": f"HTTP {status} - Acesso negado ou erro no endpoint."
            }
            
        try:
            body = r.json()
        except Exception:
            return {
                "endpoint": name,
                "empresaCodigo": emp_cod,
                "httpStatus": status,
                "registros": 0,
                "possuiDados": False,
                "observacao": "HTTP 200, mas corpo não é um JSON válido."
            }
            
        # Contar registros
        records = []
        if isinstance(body, list):
            records = body
        elif isinstance(body, dict):
            # Tenta pegar das chaves conhecidas do WebPosto
            records = body.get("resultados") or body.get("data") or body.get("venda_item") or []
            if not isinstance(records, list):
                # Se não for uma lista direta, tenta verificar se o dicionário em si tem conteúdo
                records = [body] if body else []
                
        # Filtrar registros que de fato pertençam à empresa testada para o caso de endpoints de REDE que trazem tudo,
        # ou se o endpoint respeitou o filtro de empresaCodigo.
        # No entanto, a pergunta quer saber se conseguimos extrair registros daquela empresa específica por aquele endpoint.
        registros_totais = len(records)
        possui_dados = registros_totais > 0
        
        # Vamos analisar os dados retornados para ver se de fato pertencem à empresa testada.
        from_target_emp = 0
        if possui_dados:
            for item in records:
                if isinstance(item, dict):
                    item_emp = item.get("empresaCodigo") or item.get("empresa_codigo") or item.get("filialCodigo")
                    if item_emp is not None and int(item_emp) == emp_cod:
                        from_target_emp += 1
                        
        obs = ""
        if possui_dados:
            if from_target_emp > 0:
                obs = f"Retornou {registros_totais} registros no total, sendo {from_target_emp} específicos da empresa {emp_cod}."
            else:
                # Se for endpoint de REDE, talvez traga registros de outras empresas, mas não da nossa empresa query
                distinct_eps = set()
                for item in records:
                    if isinstance(item, dict):
                        e_cod = item.get("empresaCodigo")
                        if e_cod: distinct_eps.add(e_cod)
                distinct_eps_list = list(distinct_eps)[:5]
                obs = f"Retornou {registros_totais} registros no total, mas nenhum pertence à empresa {emp_cod}. Empresas no retorno: {distinct_eps_list}."
                # Para fins da matriz por empresa, se o endpoint trouxe dados de rede mas NENHUM da empresa solicitada,
                # ou se a lista veio cheia de outras empresas, vamos registrar o count correspondente da empresa alvo.
                # A pergunta é: "consegue acessar vendas, estoque e caixa dessas mesmas filiais?"
                possui_dados = (from_target_emp > 0)
        else:
            obs = "Lista vazia retornada para o período."

        return {
            "endpoint": name,
            "empresaCodigo": emp_cod,
            "httpStatus": status,
            "registros": from_target_emp if possui_dados else 0,
            "possuiDados": possui_dados,
            "observacao": obs
        }
        
    except httpx.TimeoutException:
        return {
            "endpoint": name,
            "empresaCodigo": emp_cod,
            "httpStatus": 408,
            "registros": 0,
            "possuiDados": False,
            "observacao": "TIMEOUT ao conectar com a API."
        }
    except Exception as e:
        return {
            "endpoint": name,
            "empresaCodigo": emp_cod,
            "httpStatus": 500,
            "registros": 0,
            "possuiDados": False,
            "observacao": f"Erro interno durante teste: {str(e)[:150]}"
        }

async def main():
    print(f"Iniciando auditoria de Token WebPosto para {len(EMPRESAS_TESTE)} empresas...")
    
    async with httpx.AsyncClient(verify=False) as client:
        resultados_finais = []
        
        # Vamos rodar em lotes ou sequencialmente para não estourar limites
        for emp_cod in EMPRESAS_TESTE:
            print(f"\n--- AUDITANDO EMPRESA {emp_cod} ---")
            for name, path in ENDPOINTS_MAPPING.items():
                res = await test_endpoint(client, name, path, emp_cod)
                resultados_finais.append(res)
                print(f"  [{res['endpoint']}] HTTP {res['httpStatus']} | registros={res['registros']} | possuiDados={res['possuiDados']}")
                
        # Salvar resultados
        os.makedirs("docs", exist_ok=True)
        with open("docs/audit_token_scopes_detailed.json", "w", encoding="utf-8") as f:
            json.dump(resultados_finais, f, indent=2, ensure_ascii=False)
            
        print("\nPronto! Resultados gravados em docs/audit_token_scopes_detailed.json")

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    asyncio.run(main())
