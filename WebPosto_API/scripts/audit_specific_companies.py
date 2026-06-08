import sys
import asyncio
from pathlib import Path
from decimal import Decimal

# Add src package root to python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.gateway.webposto_client import WebPostoClient
from src.services.network_financial_overview_service import NetworkFinancialOverviewService, FinancialOverviewFilters

async def run_audit():
    client = WebPostoClient()
    service = NetworkFinancialOverviewService(client)
    
    target_cods = {5256, 7, 9}
    
    print("=== STAGE 2: EMPRESAS ===")
    empresas_resp = await client.call_endpoint("empresas")
    if empresas_resp.success:
        data = empresas_resp.data
        rows = service._rows(data)
        found_in_empresas = []
        for r in rows:
            cod = r.get("empresaCodigo") or r.get("codigo")
            if cod is not None and int(cod) in target_cods:
                found_in_empresas.append(r)
        print(f"Target companies found in /INTEGRACAO/EMPRESAS: {found_in_empresas}")
        print(f"All codes in /INTEGRACAO/EMPRESAS: {[r.get('empresaCodigo') or r.get('codigo') for r in rows]}")
    else:
        print(f"Failed to fetch /INTEGRACAO/EMPRESAS: {empresas_resp.error}")

    # For the tests below, let's look at dates 2026-06-01 to 2026-06-07 (or some other wide period)
    dates = [("2026-06-01", "2026-06-07"), ("2026-04-09", "2026-04-09"), ("2026-06-06", "2026-06-06")]
    
    print("\n=== STAGE 3-6: QUERYING HISTORICAL PERIODS ===")
    for start, end in dates:
        print(f"\nEvaluating Period: {start} to {end}")
        filters = FinancialOverviewFilters(data_inicial=start, data_final=end)
        
        # Vendas
        # The service get_sales fetches sales per company in _resolve_empresas if they support it.
        # But wait! _resolve_empresas uses get_companies which returns ALL 12 (including stubs for stubs).
        # And then get_sales queries sales per empresa.
        # Let's inspect the outputs from get_sales for each target.
        for code in target_cods:
            comp_filter = FinancialOverviewFilters(data_inicial=start, data_final=end, empresa_codigo=code)
            
            # Vendas
            sales_resp = await service.get_sales(comp_filter, page=1, limit=500)
            sales_rows = sales_resp.data.get("data", []) if sales_resp.success else []
            
            # Despesas
            exp_resp = await service.get_financial_expenses(comp_filter, page=1, limit=500)
            exp_rows = exp_resp.data.get("data", []) if exp_resp.success else []
            
            # Contas a pagar
            acc_resp = await service.get_accounts_payable(comp_filter, page=1, limit=500)
            acc_rows = acc_resp.data.get("data", []) if acc_resp.success else []
            
            # Estoque
            stock_resp = await service.get_stock(comp_filter, page=1, limit=500)
            stock_rows = stock_resp.data.get("data", []) if stock_resp.success else []
            
            print(f"Company {code}:")
            print(f"  - Sales: {len(sales_rows)} rows (Success: {sales_resp.success})")
            if sales_rows:
                print(f"    Sample sale: {sales_rows[0]}")
            print(f"  - Expenses: {len(exp_rows)} rows (Success: {exp_resp.success})")
            if exp_rows:
                print(f"    Sample expense: {exp_rows[0]}")
            print(f"  - Accounts Payable: {len(acc_rows)} rows (Success: {acc_resp.success})")
            if acc_rows:
                print(f"    Sample account: {acc_rows[0]}")
            print(f"  - Stock: {len(stock_rows)} rows (Success: {stock_resp.success})")
            if stock_rows:
                print(f"    Sample stock: {stock_rows[0]}")

if __name__ == "__main__":
    asyncio.run(run_audit())
