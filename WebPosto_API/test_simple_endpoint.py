import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from webposto.config import WebPostoConfig
from webposto.client import WebPostoClient

config = WebPostoConfig(
    chave="<WEBPOSTO_API_TOKEN>",
    base_url="http://web.qualityautomacao.com.br",
    timeout=30,
)

client = WebPostoClient(config)

# Tenta o endpoint mais simples: listar clientes (sem parâmetros obrigatórios)
try:
    print("Tentando: client.clientes.listar()")
    result = client.clientes.listar()
    print("✓ FUNCIONOU!")
    print(f"Tipo: {type(result)}")
    print(f"Conteúdo: {result}")
except Exception as e:
    print(f"✗ Erro: {e}")
    print(f"Tipo do erro: {type(e).__name__}")
