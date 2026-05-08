import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from webposto.config import WebPostoConfig
from webposto.client import WebPostoClient

# Force a chave BI
config = WebPostoConfig(
    chave="03afc3f0-590b-44cf-99a1-e4dd74ac7478",
    base_url="http://web.qualityautomacao.com.br",
    timeout=30,
)

client = WebPostoClient(config)

# Testa relatório de vendas por produto
try:
    print("Tentando: relatorios.vendas_produto()")
    result = client.relatorios.vendas_produto()
    print(f"✓ Sucesso! Tipo: {type(result)}")
    print(f"Conteúdo: {result}")
except Exception as e:
    print(f"✗ Erro: {e}")

# Testa relatório de estoque
try:
    print("\nTentando: relatorios.estoque()")
    result = client.relatorios.estoque()
    print(f"✓ Sucesso! Tipo: {type(result)}")
    print(f"Conteúdo: {result}")
except Exception as e:
    print(f"✗ Erro: {e}")
