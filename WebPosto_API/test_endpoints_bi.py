import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from webposto.config import WebPostoConfig
from webposto.client import WebPostoClient
from datetime import datetime, timedelta

config = WebPostoConfig(
    chave="<WEBPOSTO_API_KEY_DEV>",
    base_url="http://web.qualityautomacao.com.br",
    timeout=30,
)

client = WebPostoClient(config)

# Gera datas para testes
hoje = datetime.now()
ontem = hoje - timedelta(days=1)
data_ini = ontem.strftime("%Y-%m-%d")
data_fim = hoje.strftime("%Y-%m-%d")

endpoints = [
    ("clientes.listar()", lambda: client.clientes.listar()),
    ("produtos.listar()", lambda: client.produtos.listar()),
    (
        "abastecimento.listar(data_ini, data_fim)",
        lambda: client.abastecimento.listar(data_ini, data_fim),
    ),
    (
        f"relatorios.vendas_produto('{data_ini}', '{data_fim}')",
        lambda: client.relatorios.vendas_produto(data_ini, data_fim),
    ),
    (
        f"relatorios.vendas_combustivel('{data_ini}', '{data_fim}')",
        lambda: client.relatorios.vendas_combustivel(data_ini, data_fim),
    ),
    (
        f"relatorios.resumo_vendas('{data_ini}', '{data_fim}')",
        lambda: client.relatorios.resumo_vendas(data_ini, data_fim),
    ),
    ("relatorios.estoque()", lambda: client.relatorios.estoque()),
]

print("\n" + "=" * 70)
print("TESTANDO ENDPOINTS COM CHAVE BI")
print("=" * 70 + "\n")

passed = 0
failed = 0

for name, endpoint in endpoints:
    try:
        print(f"[{endpoints.index((name, endpoint))+1}/{len(endpoints)}] {name}")
        result = endpoint()
        print("  ✓ Sucesso!")
        if isinstance(result, list):
            print(f"    Tipo: list ({len(result)} items)")
        elif isinstance(result, dict):
            print(f"    Tipo: dict (chaves: {list(result.keys())[:3]}...)")
        else:
            print(f"    Tipo: {type(result).__name__}")
        passed += 1
    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg:
            print("  ✗ HTTP 403 - Sem permissão")
        elif "401" in error_msg:
            print("  ✗ HTTP 401 - Chave inválida")
        else:
            print(f"  ✗ {error_msg[:60]}")
        failed += 1
    print()

print("=" * 70)
print(f"RESULTADO: {passed} passou | {failed} falhou")
print("=" * 70 + "\n")
