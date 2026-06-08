import os
import json
import httpx
import asyncio
from datetime import datetime

# Carregar arquivo .env se existir
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
CHAVE = os.getenv("WEBPOSTO_API_KEY", "<WEBPOSTO_API_TOKEN>")

# Filiais da Tabela Mestra Corporativa
FILIAIS_MAPPING = {
    5256: "POSTO BR SHOPPING",
    5333: "POSTO JANGA",
    5555: "AP CASA CAIADA",
    5556: "POSTO CIDADE PATRIMONIO",
    5557: "POSTO ENSEADA DO NORTE",
    5559: "POSTO RJ",
    5560: "POSTO SERTÃ",
    11495: "POSTO VIP",
    46433: "POSTO DOZE",
    74014: "POSTO DOZE FILIAL II"
}

# Períodos de teste solicitados
PERIODOS = [
    {"rotulo": "06/06/2026", "ini": "2026-06-06", "fim": "2026-06-06"},
    {"rotulo": "01/06/2026 a 07/06/2026", "ini": "2026-06-01", "fim": "2026-06-07"},
    {"rotulo": "01/05/2026 a 31/05/2026", "ini": "2026-05-01", "fim": "2026-05-31"}
]

# Endpoints solicitados a auditar
ENDPOINTS = [
    "/INTEGRACAO/ABASTECIMENTO_REDE",
    "/INTEGRACAO/CONSULTAR_ABASTECIMENTO_REDE",
    "/INTEGRACAO/LMC_REDE",
    "/INTEGRACAO/CONSULTAR_LMC_REDE",
    "/INTEGRACAO/PRODUTO_EMPRESA_REDE",
    "/INTEGRACAO/CONSULTAR_PRODUTO_EMPRESA_REDE",
    "/INTEGRACAO/EMPRESAS_REDE",
    "/INTEGRACAO/CONSULTAR_EMPRESAS_REDE",
    "/INTEGRACAO/PRODUTO_COMBUSTIVEL"
]

# Função para classificar o combustível com base na descrição ou outros campos
def classificar_combustivel(descricao):
    if not descricao:
        return "OUTRO"
    desc_upper = str(descricao).upper().strip()
    
    if "GASOLINA" in desc_upper or "GAS." in desc_upper or "GAS " in desc_upper:
        if "ADIT" in desc_upper or "GRID" in desc_upper or "V-POWER" in desc_upper or "PODIUM" in desc_upper:
            return "GASOLINA ADITIVADA"
        return "GASOLINA COMUM"
    elif "ETANOL" in desc_upper or "ALCOOL" in desc_upper or "ALC." in desc_upper:
        return "ETANOL"
    elif "DIESEL" in desc_upper or "OLEO D" in desc_upper or "D10" in desc_upper or "S10" in desc_upper or "S-10" in desc_upper:
        if "S10" in desc_upper or "S-10" in desc_upper:
            return "DIESEL S10"
        return "DIESEL S500"
    elif "ARLA" in desc_upper:
        return "ARLA"
    elif "GNV" in desc_upper or "GAS NATURAL" in desc_upper:
        return "GNV"
    return "OUTRO"

async def test_endpoint(client, endpoint, ini, fim):
    params = {
        "CHAVE": CHAVE,
        "dataInicial": ini,
        "dataFinal": fim
    }
    
    url = f"{BASE_URL}{endpoint}"
    
    try:
        r = await client.get(url, params=params, timeout=15.0)
        status = r.status_code
        
        if status != 200:
            return {
                "endpoint": endpoint,
                "httpStatus": status,
                "quantidadeRegistros": 0,
                "empresaCodigosEncontrados": [],
                "produtoCodigosEncontrados": [],
                "camposDisponiveis": [],
                "possuiEmpresaCodigo": False,
                "possuiProdutoCodigo": False,
                "possuiQuantidade": False,
                "possuiLitros": False,
                "possuiValor": False,
                "candidatoDashboardCombustivel": False,
                "error": f"HTTP {status}"
            }
            
        try:
            body = r.json()
        except:
            return {
                "endpoint": endpoint,
                "httpStatus": status,
                "quantidadeRegistros": 0,
                "empresaCodigosEncontrados": [],
                "produtoCodigosEncontrados": [],
                "camposDisponiveis": [],
                "possuiEmpresaCodigo": False,
                "possuiProdutoCodigo": False,
                "possuiQuantidade": False,
                "possuiLitros": False,
                "possuiValor": False,
                "candidatoDashboardCombustivel": False,
                "error": "Nao e JSON"
            }
            
        records = []
        if isinstance(body, list):
            records = body
        elif isinstance(body, dict):
            records = body.get("resultados") or body.get("data") or body.get("venda_item") or []
            if not isinstance(records, list):
                records = [body] if body else []
                
        qty = len(records)
        
        emp_codes = set()
        prod_codes = set()
        campos = set()
        
        possui_empresa_codigo = False
        possui_produto_codigo = False
        possui_quantidade = False
        possui_litros = False
        possui_valor = False
        
        for item in records:
            if isinstance(item, dict):
                campos.update(item.keys())
                
                # Identificar empresaCodigo
                for k in ["empresaCodigo", "empresa_codigo", "filialCodigo", "codEmpresa"]:
                    if k in item and item[k] is not None:
                        try:
                            emp_codes.add(int(item[k]))
                            possui_empresa_codigo = True
                        except:
                            pass
                            
                # Identificar produtoCodigo
                for k in ["produtoCodigo", "produto_codigo", "codigoProduto", "codProduto"]:
                    if k in item and item[k] is not None:
                        try:
                            prod_codes.add(int(item[k]))
                            possui_produto_codigo = True
                        except:
                            pass
                            
                # Quantidade
                for k in ["quantidade", "qtd"]:
                    if k in item and item[k] is not None:
                        possui_quantidade = True
                        
                # Litros
                for k in ["litros", "volume", "litrosVendidos"]:
                    if k in item and item[k] is not None:
                        possui_litros = True
                        
                # Valor
                for k in ["valor", "valorTotal", "totalVenda", "total"]:
                    if k in item and item[k] is not None:
                        possui_valor = True
                        
        emp_codes_list = sorted(list(emp_codes))
        prod_codes_list = sorted(list(prod_codes))
        campos_list = sorted(list(campos))
        
        # Um endpoint é um bom candidato se tem quantidade ou litros, produtoCodigo e empresaCodigo.
        candidato = (possui_quantidade or possui_litros) and possui_produto_codigo and possui_empresa_codigo
        
        return {
            "endpoint": endpoint,
            "httpStatus": status,
            "quantidadeRegistros": qty,
            "empresaCodigosEncontrados": emp_codes_list,
            "produtoCodigosEncontrados": prod_codes_list,
            "camposDisponiveis": campos_list,
            "possuiEmpresaCodigo": possui_empresa_codigo,
            "possuiProdutoCodigo": possui_produto_codigo,
            "possuiQuantidade": possui_quantidade,
            "possuiLitros": possui_litros,
            "possuiValor": possui_valor,
            "candidatoDashboardCombustivel": candidato,
            "raw_records": records[:5] if qty > 0 else [] # Amostra para auditoria detalhada
        }
        
    except Exception as e:
        return {
            "endpoint": endpoint,
            "httpStatus": 500,
            "quantidadeRegistros": 0,
            "empresaCodigosEncontrados": [],
            "produtoCodigosEncontrados": [],
            "camposDisponiveis": [],
            "possuiEmpresaCodigo": False,
            "possuiProdutoCodigo": False,
            "possuiQuantidade": False,
            "possuiLitros": False,
            "possuiValor": False,
            "candidatoDashboardCombustivel": False,
            "error": str(e)
        }

async def audit_sub_produtos(client):
    """
    Tenta obter dados de produtos e combustíveis para mapear.
    Usamos o endpoint produto com a empresa 11495 e 5555.
    """
    produtos_mapeados = []
    
    for emp_cod in [11495, 5555]:
        url = f"{BASE_URL}/INTEGRACAO/PRODUTO"
        params = {"CHAVE": CHAVE, "empresaCodigo": emp_cod}
        try:
            r = await client.get(url, params=params, timeout=15.0)
            if r.status_code == 200:
                body = r.json()
                records = body.get("resultados") or body.get("data") or []
                if isinstance(records, list):
                    for item in records:
                        if isinstance(item, dict):
                            prod_cod = item.get("produtoCodigo") or item.get("codigo")
                            nome = item.get("nome") or item.get("descricao") or ""
                            combustivel = item.get("combustivel") or False
                            tipo_prod = item.get("tipoProduto") or ""
                            grupo = item.get("grupoCodigo") or ""
                            
                            if prod_cod is not None:
                                p_data = {
                                    "produtoCodigo": int(prod_cod),
                                    "descricao": str(nome).strip(),
                                    "combustivel": combustivel or (tipo_prod == "C") or any(k in str(nome).upper() for k in ["GASOLINA", "ETANOL", "DIESEL"]),
                                    "grupo": str(grupo),
                                    "tipo": str(tipo_prod)
                                }
                                # Evitar duplicados
                                if not any(px["produtoCodigo"] == p_data["produtoCodigo"] for px in produtos_mapeados):
                                    p_data["classificacao"] = classificar_combustivel(p_data["descricao"]) if p_data["combustivel"] else "OUTRO"
                                    produtos_mapeados.append(p_data)
        except Exception as e:
            print(f"Erro ao buscar sub-produtos para empresa {emp_cod}: {e}")
            
    return produtos_mapeados

async def main():
    print("Iniciando SPRINT 22A — Auditoria de Volumes de Combustíveis na Rede...")
    
    async with httpx.AsyncClient(verify=False) as client:
        # Obter produtos para a descoberta de combustíveis
        print("\nColetando cadastro de produtos para descoberta de combustíveis...")
        lista_produtos = await audit_sub_produtos(client)
        print(f"Total de produtos únicos encontrados/mapeados: {len(lista_produtos)}")
        
        # Rodar os testes de auditoria de endpoints para cada período
        auditorias_por_periodo = {}
        for p in PERIODOS:
            print(f"\n--- Testando Período: {p['rotulo']} ({p['ini']} a {p['fim']}) ---")
            period_results = []
            for ep in ENDPOINTS:
                print(f"  Testando endpoint: {ep}")
                res = await test_endpoint(client, ep, p["ini"], p["fim"])
                period_results.append(res)
            auditorias_por_periodo[p["rotulo"]] = period_results
            
        # Processar a descoberta de empresaCodigo
        todas_empresas_descobertas = set()
        for rotulo, results in auditorias_por_periodo.items():
            for res in results:
                todas_empresas_descobertas.update(res["empresaCodigosEncontrados"])
                
        resumo_empresas = []
        for emp_cod in FILIAIS_MAPPING.keys():
            if emp_cod in todas_empresas_descobertas:
                resumo_empresas.append({
                    "empresaCodigo": emp_cod,
                    "nome": FILIAIS_MAPPING[emp_cod],
                    "status": "CONFIRMADO_NA_API"
                })
            else:
                resumo_empresas.append({
                    "empresaCodigo": emp_cod,
                    "nome": FILIAIS_MAPPING[emp_cod],
                    "status": "NAO_CONFIRMADO"
                })
                
        for emp_cod in todas_empresas_descobertas:
            if emp_cod not in FILIAIS_MAPPING:
                resumo_empresas.append({
                    "empresaCodigo": emp_cod,
                    "nome": f"EMPRESA DESCONHECIDA ({emp_cod})",
                    "status": "NOVO_EMPRESACODIGO_DESCOBERTO"
                })
                
        # Consolidar estrutura do JSON de saída do teste
        output_results = {
            "auditorias_por_periodo": auditorias_por_periodo,
            "descoberta_empresas": resumo_empresas,
            "descoberta_combustiveis": lista_produtos
        }
        
        with open("fuel_network_audit_result.json", "w", encoding="utf-8") as f:
            json.dump(output_results, f, indent=2, ensure_ascii=False)
            
        print("\nSessão de auditoria concluída!")
        print("Resultados gravados em fuel_network_audit_result.json")

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    asyncio.run(main())
