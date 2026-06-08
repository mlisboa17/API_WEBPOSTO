import sys
import asyncio
from pathlib import Path
from decimal import Decimal

# Add src package root to python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.gateway.webposto_client import WebPostoClient
from src.services.network_financial_overview_service import NetworkFinancialOverviewService, FinancialOverviewFilters

async def main():
    client = WebPostoClient()
    service = NetworkFinancialOverviewService(client)
    
    # 1. Test GET COMPANIES
    print("=== TESTANDO /INTEGRACAO/EMPRESAS ===")
    companies_resp = await service.get_companies()
    if not companies_resp.success:
        print(f"Erro ao obter empresas: {companies_resp.error}")
        return
        
    companies = companies_resp.data.get("data", [])
    print(f"Total de empresas reconhecidas: {len(companies)}")
    
    # Get raw empresas
    raw_empresas = []
    resp = await client.call_endpoint("empresas", params={})
    if resp.success:
        raw_empresas = resp.data
        if isinstance(raw_empresas, dict):
            raw_empresas = raw_empresas.get("resultados") or raw_empresas.get("data") or []
    
    raw_codes = {int(x.get("empresaCodigo") or x.get("codigo")) for x in raw_empresas if (x.get("empresaCodigo") or x.get("codigo")) is not None}
    print(f"Códigos retornados na API real (/INTEGRACAO/EMPRESAS): {raw_codes}")
    
    # Filters periods
    filters = FinancialOverviewFilters(
        data_inicial="2026-06-06",
        data_final="2026-06-06"
    )
    
    # 2. Test Endpoints for each company/overall
    print("\n=== ANALISANDO COBERTURA DE DADOS OPERACIONAIS (Data 2026-06-06) ===")
    
    # Fetch lists
    exp_resp = await service.get_financial_expenses(filters, page=1, limit=500)
    acc_resp = await service.get_accounts_payable(filters, page=1, limit=500)
    sales_resp = await service.get_sales(filters, page=1, limit=500)
    stock_resp = await service.get_stock(filters, page=1, limit=500)
    
    expenses_rows = exp_resp.data.get("data", []) if exp_resp.success else []
    accounts_rows = acc_resp.data.get("data", []) if acc_resp.success else []
    sales_rows = sales_resp.data.get("data", []) if sales_resp.success else []
    stock_rows = stock_resp.data.get("data", []) if stock_resp.success else []
    
    print(f"Total despesas: {len(expenses_rows)}")
    print(f"Total contas a pagar: {len(accounts_rows)}")
    print(f"Total vendas: {len(sales_rows)}")
    print(f"Total estoque: {len(stock_rows)}")
    
    # Collect which empresas appear in each
    emp_expenses = {int(r["empresaCodigo"]) for r in expenses_rows if r.get("empresaCodigo")}
    emp_accounts = {int(r["empresaCodigo"]) for r in accounts_rows if r.get("empresaCodigo")}
    emp_sales = {int(r["empresaCodigo"]) for r in sales_rows if r.get("empresaCodigo")}
    emp_stock = {int(r["empresaCodigo"]) for r in stock_rows if r.get("empresaCodigo")}
    
    print("\nCódigos por endpoint:")
    print(f"Aparecem em DESPESAS: {emp_expenses}")
    print(f"Aparecem em CONTAS_PAGAR: {emp_accounts}")
    print(f"Aparecem em VENDA: {emp_sales}")
    print(f"Aparecem em ESTOQUE: {emp_stock}")
    
    companies_dict = {
        5256: "POSTO BR SHOPPING",
        5333: "POSTO JANGA",
        5556: "POSTO CIDADE PATRIMONIO",
        5555: "AP CASA CAIADA",
        5557: "POSTO ENSEADA DO NORTE",
        5560: "POSTO SERTA",
        7: "POSTO REAL",
        5559: "POSTO RJ",
        9: "AUTO POSTO GLOBO",
        11495: "POSTO VIP",
        46433: "POSTO DOZE",
        74014: "POSTO DOZE FILIAL II",
    }
    
    print("\n=== TABELA FINAL DE COBERTURA ===")
    print(f"{'Filial':<25} | {'Código':<10} | {'Dados Encontrados?':<18} | {'Token Cobre?':<12}")
    print("-" * 75)
    for code, name in companies_dict.items():
        token_cobre = "Sim" if code in raw_codes else "Não"
        has_data = "Não"
        if code in emp_expenses or code in emp_accounts or code in emp_sales or code in emp_stock:
            has_data = "Sim"
        print(f"{name:<25} | {code:<10} | {has_data:<18} | {token_cobre:<12}")

if __name__ == "__main__":
    asyncio.run(main())
