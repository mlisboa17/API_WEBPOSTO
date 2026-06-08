import asyncio
import httpx
import json
from datetime import datetime, timedelta

# --- Configuração ---
API_BASE_URL = "http://127.0.0.1:8000"  # Assumindo que a API roda localmente na porta 8000
ENDPOINT = "/v1/financial/overview"

def get_default_period():
    """Retorna um período de 30 dias atrás até hoje."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

async def validate_overview(start_date: str, end_date: str):
    """Chama o endpoint de overview e imprime os resultados."""
    params = {
        "dataInicial": start_date,
        "dataFinal": end_date,
    }
    
    print(f"🚀 Chamando endpoint: {ENDPOINT}")
    print(f"   - Período: {start_date} a {end_date}")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(f"{API_BASE_URL}{ENDPOINT}", params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get("success"):
                print("❌ A API retornou um erro:")
                print(json.dumps(data.get("error"), indent=2))
                return

            overview_data = data.get("data", {})
            postos = overview_data.get("postos", [])
            consolidado = overview_data.get("consolidado", {})

            print("\n--- ✅ Resultados por Filial ---")
            print(f"{'Filial':<30} | {'Empresa Cod.':<15} | {'Total Despesas':>20} | {'Total a Pagar':>20}")
            print("-" * 95)

            if not postos:
                print("Nenhuma filial encontrada para o período.")
            else:
                for posto in sorted(postos, key=lambda p: p.get("nome")):
                    print(
                        f"{posto.get('nome', 'N/A'):<30} | "
                        f"{str(posto.get('empresaCodigo', 'N/A')):<15} | "
                        f"{'R$ ' + posto.get('total_despesas', '0.00'):>20} | "
                        f"{'R$ ' + posto.get('total_a_pagar', '0.00'):>20}"
                    )

            print("\n" + "-" * 95)
            print("\n--- 📈 Total Geral da Rede (Consolidado) ---")
            print(f"  - Total Despesas: R$ {consolidado.get('total_despesas', '0.00')}")
            print(f"  - Total a Pagar:  R$ {consolidado.get('total_a_pagar', '0.00')}")
            
            # Validação: Soma das linhas vs Total geral
            soma_despesas = sum(float(p.get('total_despesas', 0)) for p in postos)
            soma_a_pagar = sum(float(p.get('total_a_pagar', 0)) for p in postos)
            
            print("\n--- 🔍 Verificação da Soma ---")
            print(f"Soma Despesas (Linhas): R$ {soma_despesas:.2f}")
            print(f"Soma a Pagar (Linhas):  R$ {soma_a_pagar:.2f}")
            
            despesas_ok = abs(soma_despesas - float(consolidado.get('total_despesas', 0))) < 0.01
            pagar_ok = abs(soma_a_pagar - float(consolidado.get('total_a_pagar', 0))) < 0.01
            
            print(f"\n[ {'✅' if despesas_ok else '❌'} ] Soma de despesas bate com o total consolidado.")
            print(f"[ {'✅' if pagar_ok else '❌'} ] Soma de contas a pagar bate com o total consolidado.")


    except httpx.RequestError as e:
        print(f"❌ Erro de conexão ao tentar chamar a API em {e.request.url}.")
        print("   - Verifique se a API está rodando e acessível na URL configurada.")
    except Exception as e:
        print(f"❌ Ocorreu um erro inesperado: {e}")

async def main():
    data_inicial, data_final = get_default_period()
    await validate_overview(data_inicial, data_final)

if __name__ == "__main__":
    asyncio.run(main())
