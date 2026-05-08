import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from webposto.config import WebPostoConfig
from webposto.client import WebPostoClient
from datetime import date, timedelta

# Nova chave
config = WebPostoConfig(
    chave="4d6bbe21-92b2-4052-bcb5-a82c86858fd7",
    base_url="http://web.qualityautomacao.com.br",
    timeout=30,
)

client = WebPostoClient(config)

# Gera datas
hoje = date.today()
ontem = hoje - timedelta(days=1)

endpoints = [
    ("clientes.listar()", lambda: client.clientes.listar()),
    ("produtos.listar()", lambda: client.produtos.listar()),
    (
        "abastecimento.listar(ontem, hoje)",
        lambda: client.abastecimento.listar(ontem, hoje),
    ),
    (
        "relatorios.vendas_produto(ontem, hoje)",
        lambda: client.relatorios.vendas_produto(ontem, hoje),
    ),
    ("relatorios.estoque()", lambda: client.relatorios.estoque()),
]

print("\n" + "=" * 70)
print("TESTANDO COM NOVA CHAVE: 4d6bbe21-92b2-4052-bcb5-a82c86858fd7")
print("=" * 70 + "\n")

passed = 0
failed = 0

for name, endpoint in endpoints:
    try:
        print(f"[{endpoints.index((name, endpoint))+1}/{len(endpoints)}] {name}")
        result = endpoint()
        print("  ✓ SUCESSO!")
        if isinstance(result, list):
            print(f"    Resposta: list ({len(result)} registros)")
        elif isinstance(result, dict):
            print("    Resposta: dict")
        else:
            print(f"    Resposta: {type(result).__name__}")
        passed += 1
    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg:
            print("  ✗ HTTP 403 - Sem permissão")
        elif "401" in error_msg:
            print("  ✗ HTTP 401 - Chave inválida")
        else:
            print(f"  ✗ {error_msg[:70]}")
        failed += 1
    print()

print("=" * 70)
print(f"RESULTADO: {passed} passou | {failed} falhou")
print("=" * 70 + "\n")
