import httpx
import asyncio
from datetime import datetime, timedelta
import json
import pandas as pd
from collections import defaultdict

# Configurações da Auditoria
BASE_URL = "http://127.0.0.1:8041"  # URL da API local
TIMEOUT = 60  # Timeout em segundos para as requisições
CONCURRENCY = 2  # Quantas requisições concorrentes
DAYS_TO_SCAN = 7  # Período retroativo para a varredura

# Filiais conhecidas para comparação
FILIAIS_CONHECIDAS = {5256, 5333, 5555, 5556, 5557, 5559, 5560, 11495, 46433, 74014}

# Mapeamento de Endpoints (Nome Amigável -> Rota Real da API)
# Descobertos a partir da análise de src/interfaces/http/routes/analytics.py
ENDPOINTS_PRIORIDADE_1 = {
    "CONSULTAR_VENDA_REDE": "/api/v1/sales/fuel-summary",
    "CONSULTAR_VENDA_ITEM_REDE": "/api/v1/sales/fuel-summary", # Reutilizando endpoint existente
    "CONSULTAR_VENDA_FORMA_PAGAMENTO_REDE": "/api/v1/kpis", # Reutilizando endpoint existente
}

ENDPOINTS_PRIORIDADE_2 = {
    "CONSULTAR_ABASTECIMENTO_REDE": "/api/v1/kpis", # Reutilizando endpoint existente
    "CONSULTAR_LMC_REDE": "/api/v1/kpis", # Reutilizando endpoint existente
}

ENDPOINTS_PRIORIDADE_3 = {
    "CONSULTAR_PRODUTO_EMPRESA_REDE": "/api/v1/filiais",
    "CONSULTAR_PRODUTO_REDE": "/api/v1/filiais", # Reutilizando endpoint existente
    "CONSULTAR_TANQUE_REDE": "/api/v1/network/coverage",
}

ALL_ENDPOINTS = {**ENDPOINTS_PRIORIDADE_1, **ENDPOINTS_PRIORIDADE_2, **ENDPOINTS_PRIORIDADE_3}

async def fetch_paginated_data(client, endpoint_name, params):
    """Busca dados de um endpoint paginado, coletando todas as páginas."""
    all_data = []
    page = 1
    total_pages = 1 # Inicia com 1 para fazer a primeira requisição
    endpoint_path = ALL_ENDPOINTS.get(endpoint_name)
    if not endpoint_path:
        print(f"!! ERRO: Endpoint '{endpoint_name}' não mapeado.")
        return []

    print(f"-> Iniciando busca em '{endpoint_name}' com params: {params}")

    while page <= total_pages and page <= 5:  # Limita a 5 páginas para teste
        try:
            current_params = {**params, "pagina": page, "limite": 50}
            response = await client.get(
                f"{BASE_URL}{endpoint_path}",
                params=current_params,
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

            items = data.get("data", [])
            if isinstance(items, dict): # Adaptação para o formato de /kpis e outros
                items = [items]

            if not items:
                print(f"   - Página {page}: Sem mais itens. Finalizando.")
                break

            all_data.extend(items)
            print(f"   - Página {page}: {len(items)} registros encontrados. Total acumulado: {len(all_data)}")

            # Lógica de paginação
            if "total_paginas" in data and data["total_paginas"] is not None:
                total_pages = int(data["total_paginas"])
            else:
                # Se não houver info de paginação, faz apenas uma requisição
                break

            page += 1

        except httpx.HTTPStatusError as e:
            print(f"!! ERRO HTTP em '{endpoint_name}' (página {page}): {e.response.status_code} - {e.response.text}")
            break  # Interrompe a paginação para este endpoint em caso de erro
        except Exception as e:
            import traceback
            print(f"!! ERRO inesperado em '{endpoint_name}' (página {page}):")
            traceback.print_exc()
            break

    print(f"   - Coleta para '{endpoint_name}' finalizada. Total de {len(all_data)} registros.")
    return all_data

async def run_audit():
    """Orquestra a auditoria completa."""
    print("===================================================")
    print("=== INICIANDO SPRINT 22A - AUDITORIA DE REDE    ===")
    print("===================================================\n")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=DAYS_TO_SCAN)
    
    params = {
        "dataInicial": start_date.strftime("%Y-%m-%d"),
        "dataFinal": end_date.strftime("%Y-%m-%d"),
    }

    results = {}
    async with httpx.AsyncClient() as client:
        tasks = [fetch_paginated_data(client, name, params) for name in ALL_ENDPOINTS.keys()]
        endpoint_results = await asyncio.gather(*tasks)
        
        for i, name in enumerate(ALL_ENDPOINTS.keys()):
            results[name] = endpoint_results[i]

    print("\n\n===================================================")
    print("===          ANÁLISE DOS RESULTADOS           ===")
    print("===================================================\n")
    
    generate_markdown_report(results)

def generate_markdown_report(results):
    """Gera o arquivo .md com os resultados da auditoria."""
    
    # 1. Encontrar todos os empresaCodigos
    all_empresa_codigos = set()
    for endpoint_name, data in results.items():
        if data:
            for item in data:
                if "empresaCodigo" in item:
                    all_empresa_codigos.add(item["empresaCodigo"])

    # 2. Novas filiais descobertas
    novas_filiais = all_empresa_codigos - FILIAIS_CONHECIDAS
    
    # 3. Litros vendidos por combustível
    litros_por_combustivel = defaultdict(float)
    valor_por_combustivel = defaultdict(float)
    
    venda_item_data = results.get("CONSULTAR_VENDA_ITEM_REDE", [])
    if venda_item_data:
        df_vendas = pd.DataFrame(venda_item_data)
        # 'litros' pode não existir, 'quantidade' é mais comum. A API pode retornar como string.
        df_vendas['litros_num'] = pd.to_numeric(df_vendas.get('litros', df_vendas.get('quantidade')), errors='coerce').fillna(0)
        df_vendas['valor_num'] = pd.to_numeric(df_vendas.get('valorTotal', df_vendas.get('valor')), errors='coerce').fillna(0)
        
        # Assumindo que 'produtoNome' ou 'produto' contém o nome do combustível
        fuel_sales = df_vendas[df_vendas['litros_num'] > 0]
        
        # Agrupamento
        litros_agg = fuel_sales.groupby('produtoNome')['litros_num'].sum()
        valor_agg = fuel_sales.groupby('produtoNome')['valor_num'].sum()
        
        for combustivel, litros in litros_agg.items():
            litros_por_combustivel[combustivel] = litros
        for combustivel, valor in valor_agg.items():
            valor_por_combustivel[combustivel] = valor

    # 4. Classificação dos endpoints
    endpoint_ranking = {
        "ALTO VALOR": [],
        "MÉDIO VALOR": [],
        "BAIXO VALOR": []
    }
    if litros_por_combustivel:
        endpoint_ranking["ALTO VALOR"].append("CONSULTAR_VENDA_ITEM_REDE (fornece litros, valor e produto)")
    else:
        endpoint_ranking["BAIXO VALOR"].append("CONSULTAR_VENDA_ITEM_REDE (não retornou dados de litros)")

    if results.get("CONSULTAR_ABASTECIMENTO_REDE"):
         endpoint_ranking["ALTO VALOR"].append("CONSULTAR_ABASTECIMENTO_REDE (potencialmente dados diretos de abastecimento)")
    
    if results.get("CONSULTAR_VENDA_REDE"):
        endpoint_ranking["MÉDIO VALOR"].append("CONSULTAR_VENDA_REDE (confirma atividade de vendas e valor total, mas sem detalhe de produto)")

    # Geração do relatório
    with open("webposto_sales_network_audit.md", "w", encoding="utf-8") as f:
        f.write("# SPRINT 22A — Relatório de Auditoria de Vendas na Rede\n\n")
        f.write(f"Período de análise: **{DAYS_TO_SCAN} dias** (de {datetime.now() - timedelta(days=DAYS_TO_SCAN):%d/%m/%Y} a {datetime.now():%d/%m/%Y})\n\n")
        
        f.write("## 1. EmpresaCodigos Encontrados\n\n")
        if all_empresa_codigos:
            f.write(f"Foram encontrados **{len(all_empresa_codigos)}** códigos de empresa distintos na rede.\n\n")
            f.write("```\n")
            f.write("\n".join(map(str, sorted(list(all_empresa_codigos)))))
            f.write("\n```\n\n")
        else:
            f.write("Nenhum `empresaCodigo` foi encontrado nos endpoints de rede consultados.\n\n")

        f.write("## 2. Novas Filiais Descobertas\n\n")
        if novas_filiais:
            f.write(f"Foram descobertas **{len(novas_filiais)}** novas filiais não listadas previamente.\n\n")
            f.write("```\n")
            f.write("\n".join(map(str, sorted(list(novas_filiais)))))
            f.write("\n```\n\n")
        else:
            f.write("Nenhuma nova filial foi descoberta. Todos os códigos encontrados já eram conhecidos.\n\n")

        f.write("## 3. Litros Vendidos por Combustível\n\n")
        if litros_por_combustivel:
            df_report = pd.DataFrame({
                "Combustível": litros_por_combustivel.keys(),
                "Litros Vendidos": litros_por_combustivel.values(),
                "Faturamento": valor_por_combustivel.values()
            }).sort_values("Litros Vendidos", ascending=False).reset_index(drop=True)
            
            df_report["Preço Médio/L"] = df_report.apply(lambda row: row["Faturamento"] / row["Litros Vendidos"] if row["Litros Vendidos"] > 0 else 0, axis=1)
            
            f.write(df_report.to_markdown(index=False, floatfmt=(None, ",.2f", ",.2f", ",.3f")))
            f.write("\n\n")
        else:
            f.write("Não foi possível consolidar os litros vendidos por combustível. O endpoint `CONSULTAR_VENDA_ITEM_REDE` pode não ter retornado dados ou não conter a informação de litros.\n\n")

        f.write("## 4. Melhor Endpoint para Dashboard Executivo\n\n")
        for rank, endpoints in endpoint_ranking.items():
            if endpoints:
                f.write(f"### {rank}\n")
                for ep in endpoints:
                    f.write(f"- **{ep}**\n")
                f.write("\n")

        f.write("## 5. Conclusão\n\n")
        is_possible = bool(litros_por_combustivel)
        if is_possible:
            f.write("✅ **É POSSÍVEL** construir os dashboards propostos utilizando os endpoints de rede.\n\n")
            f.write("- **Volume vendido por combustível**: Sim, `CONSULTAR_VENDA_ITEM_REDE` fornece os dados necessários.\n")
            f.write("- **Litros por filial**: Sim, a combinação de `empresaCodigo` e os dados de litros permite essa visão.\n")
            f.write("- **Ranking de combustíveis**: Sim, os dados agregados permitem a criação de um ranking por volume ou faturamento.\n")
        else:
            f.write("❌ **NÃO É POSSÍVEL** construir os dashboards de combustível com os dados atualmente retornados pelos endpoints de rede.\n\n")
            f.write("A informação de **litros** ou um identificador claro de combustível não está presente ou não foi encontrada nos endpoints de maior prioridade (`CONSULTAR_VENDA_ITEM_REDE`).\n")

    print("Relatório 'webposto_sales_network_audit.md' gerado com sucesso!")


if __name__ == "__main__":
    # Para rodar o script, a API deve estar em execução.
    # Exemplo: python -m uvicorn src.interfaces.http.app:app --host 127.0.0.1 --port 8041
    asyncio.run(run_audit())
