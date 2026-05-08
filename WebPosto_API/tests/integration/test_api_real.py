"""
Testes de Integração — Chamadas reais à API WebPosto
Requer: WEBPOSTO_CHAVE válida no .env
"""

import sys
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from webposto.config import WebPostoConfig
from webposto.client import WebPostoClient


def test_config_from_env():
    """Valida que a CHAVE foi carregada corretamente"""
    config = WebPostoConfig.from_env()
    assert config.chave, "CHAVE não foi carregada do .env"
    assert len(config.chave) > 10, "CHAVE parece inválida (muito curta)"
    print(f"✓ CHAVE carregada: {config.chave[:20]}...")


def test_healthcheck_api():
    """Testa se a API responde com a CHAVE"""
    config = WebPostoConfig.from_env()
    client = WebPostoClient(config)

    try:
        # Tenta listar abastecimentos (GET simples)
        result = client.abastecimento.listar()
        print("✓ API respondeu com sucesso")
        print(f"  Tipo de resposta: {type(result)}")
        return True
    except Exception as e:
        print(f"✗ Erro ao conectar: {e}")
        return False


def test_listar_clientes():
    """Testa se consegue listar clientes reais"""
    config = WebPostoConfig.from_env()
    client = WebPostoClient(config)

    try:
        result = client.clientes.listar()
        print(f"✓ Clientes listados: {type(result)}")
        if isinstance(result, list):
            print(f"  Total: {len(result)} registros")
        return True
    except Exception as e:
        print(f"✗ Erro ao listar clientes: {e}")
        return False


def test_listar_produtos():
    """Testa se consegue listar produtos reais"""
    config = WebPostoConfig.from_env()
    client = WebPostoClient(config)

    try:
        result = client.produtos.listar()
        print(f"✓ Produtos listados: {type(result)}")
        if isinstance(result, list):
            print(f"  Total: {len(result)} registros")
        return True
    except Exception as e:
        print(f"✗ Erro ao listar produtos: {e}")
        return False


def test_listar_abastecimentos():
    """Testa se consegue listar abastecimentos reais"""
    config = WebPostoConfig.from_env()
    client = WebPostoClient(config)

    try:
        result = client.abastecimento.listar()
        print(f"✓ Abastecimentos listados: {type(result)}")
        if isinstance(result, list):
            print(f"  Total: {len(result)} registros")
        return True
    except Exception as e:
        print(f"✗ Erro ao listar abastecimentos: {e}")
        return False


def test_listar_relatorios():
    """Testa se consegue gerar relatórios reais"""
    config = WebPostoConfig.from_env()
    client = WebPostoClient(config)

    try:
        result = client.relatorios.vendas_produto()
        print(f"✓ Relatório gerado: {type(result)}")
        return True
    except Exception as e:
        print(f"✗ Erro ao gerar relatório: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TESTES DE INTEGRAÇÃO — WebPosto API Real")
    print("=" * 60 + "\n")

    tests = [
        ("Carregar CHAVE", test_config_from_env),
        ("Healthcheck API", test_healthcheck_api),
        ("Listar Clientes", test_listar_clientes),
        ("Listar Produtos", test_listar_produtos),
        ("Listar Abastecimentos", test_listar_abastecimentos),
        ("Gerar Relatório", test_listar_relatorios),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(
            f"\n[{len([t for t in tests[:tests.index((name, test_func))]])+1}/{len(tests)}] {name}"
        )
        print("-" * 60)
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Exceção: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTADO: {passed} passou | {failed} falhou")
    print("=" * 60 + "\n")
