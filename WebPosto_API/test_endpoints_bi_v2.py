import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from webposto.config import WebPostoConfig
from webposto.client import WebPostoClient
from datetime import timedelta, date

config = WebPostoConfig(
    chave="<WEBPOSTO_API_KEY_DEV>",
    base_url="http://web.qualityautomacao.com.br",
    timeout=30,
)

client = WebPostoClient(config)

# Gera datas corretamente (como date objects)
hoje = date.today()
ontem = hoje - timedelta(days=1)

endpoints = [
    ("clientes.listar()", lambda: client.clientes.listar()),
    ("produtos.listar()", lambda: client.produtos.listar()),
    (
        f"abastecimento.listar({ontem}, {hoje})",
        lambda: client.abastecimento.listar(ontem, hoje),
    ),
    (
        f"relatorios.vendas_produto({ontem}, {hoje})",
        lambda: client.relatorios.vendas_produto(ontem, hoje),
    ),
    (
        f"relatorios.vendas_combustivel({ontem}, {hoje})",
        lambda: client.relatorios.vendas_combustivel(ontem, hoje),
    ),
    (
        f"relatorios.resumo_vendas({ontem}, {hoje})",
        lambda: client.relatorios.resumo_vendas(ontem, hoje),
    ),
    ("relatorios.estoque()", lambda: client.relatorios.estoque()),
]

print("\n" + "=" * 70)
print("TESTANDO ENDPOINTS COM CHAVE BI (v2 - datas corretas)")
print("=" * 70 + "\n")

passed = 0
failed = 0

for name, endpoint in endpoints:
    try:
        print(f"[{endpoints.index((name, endpoint))+1}/{len(endpoints)}] {name}")
        result = endpoint()
        print("  ✓ Sucesso!")
        if isinstance(result, list):
            print(f"    Resposta: list ({len(result)} items)")
        elif isinstance(result, dict):
            print(f"    Resposta: dict (chaves: {list(result.keys())[:3]}...)")
        elif result is None:
            print("    Resposta: None (204 No Content)")
        else:
            print(f"    Resposta: {type(result).__name__}")
        passed += 1
    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg:
            print("  ✗ HTTP 403 - Chave BI sem permissão para este endpoint")
        elif "401" in error_msg:
            print("  ✗ HTTP 401 - Chave inválida/expirada")
        elif "400" in error_msg:
            print("  ✗ HTTP 400 - Parâmetros inválidos")
        elif "404" in error_msg:
            print("  ✗ HTTP 404 - Endpoint não existe")
        else:
            print(f"  ✗ {error_msg[:70]}")
        failed += 1
    print()

print("=" * 70)
print(f"RESULTADO: {passed} passou | {failed} falhou")
if failed == len(endpoints):
    print("\n⚠️  NENHUM ENDPOINT FUNCIONOU")
    print("A chave BI pode:")
    print("  - Não estar ativada no contrato")
    print("  - Não ter permissão configurada")
    print("  - Estar expirada ou revogada")
print("=" * 70 + "\n")
