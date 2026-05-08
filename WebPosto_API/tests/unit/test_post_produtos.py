"""
Testes POST — Produtos, Preços, Estoque
Cobre: criar produto, trocar preço, inventário, ajuste de estoque, comissão.
"""

import json
import pytest
import responses as resp
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from webposto import WebPostoClient, WebPostoConfig
from webposto.exceptions import BadRequestError

BASE = "http://web.qualityautomacao.com.br"
CHAVE = "CHAVE_TESTE_POST_PROD"


@pytest.fixture
def client():
    return WebPostoClient(WebPostoConfig(chave=CHAVE, base_url=BASE))


# ─── POST /INTEGRACAO/PRODUTO ────────────────────────────────────────────────


@resp.activate
def test_criar_produto_retorna_codigo(client):
    """POST produto deve retornar o código do produto criado."""
    resp.add(
        resp.POST, f"{BASE}/INTEGRACAO/PRODUTO", json={"codProduto": 123}, status=201
    )

    resultado = client.produtos.criar({"nome": "GASOLINA COMUM", "unidade": "LT"})

    assert resultado["codProduto"] == 123


@resp.activate
def test_criar_produto_envia_body_correto(client):
    """POST produto deve transmitir nome e unidade corretamente."""
    resp.add(
        resp.POST, f"{BASE}/INTEGRACAO/PRODUTO", json={"codProduto": 5}, status=201
    )

    client.produtos.criar({"nome": "DIESEL S10", "unidade": "LT", "precoVenda": 6.49})

    body = json.loads(resp.calls[0].request.body)
    assert body["nome"] == "DIESEL S10"
    assert body["precoVenda"] == 6.49


@resp.activate
def test_criar_produto_400_bad_request(client):
    """POST produto sem campos obrigatórios deve retornar 400."""
    resp.add(
        resp.POST,
        f"{BASE}/INTEGRACAO/PRODUTO",
        json={"error": "Campo nome obrigatório"},
        status=400,
    )

    with pytest.raises(BadRequestError) as exc:
        client.produtos.criar({})

    assert exc.value.status_code == 400


# ─── POST /INTEGRACAO/TROCA_PRECO_COMBUSTIVEL ────────────────────────────────


@resp.activate
def test_trocar_preco_combustivel_retorna_none(client):
    """POST troca preço combustível retorna 204."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/TROCA_PRECO_COMBUSTIVEL", status=204)

    resultado = client.produtos.trocar_preco_combustivel(
        {"produtoCodigo": 1, "precoVenda": 5.89, "filialCodigo": 1}
    )

    assert resultado is None


@resp.activate
def test_trocar_preco_combustivel_envia_preco_correto(client):
    """POST troca preço deve enviar exatamente o preço informado."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/TROCA_PRECO_COMBUSTIVEL", status=204)

    client.produtos.trocar_preco_combustivel(
        {"produtoCodigo": 2, "precoVenda": 4.999, "filialCodigo": 3}
    )

    body = json.loads(resp.calls[0].request.body)
    assert body["precoVenda"] == 4.999
    assert body["produtoCodigo"] == 2


@resp.activate
def test_trocar_preco_combustivel_400_bad_request(client):
    """POST troca preço com filial inválida deve lançar BadRequestError."""
    resp.add(
        resp.POST,
        f"{BASE}/INTEGRACAO/TROCA_PRECO_COMBUSTIVEL",
        json={"error": "Filial não encontrada"},
        status=400,
    )

    with pytest.raises(BadRequestError):
        client.produtos.trocar_preco_combustivel(
            {"filialCodigo": 9999, "precoVenda": 5.0}
        )


# ─── POST /INTEGRACAO/TROCA_PRECO_PRODUTO ────────────────────────────────────


@resp.activate
def test_trocar_preco_produto_204(client):
    """POST troca preço produto retorna 204."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/TROCA_PRECO_PRODUTO", status=204)

    resultado = client.produtos.trocar_preco({"produtoCodigo": 10, "precoVenda": 12.90})

    assert resultado is None


@resp.activate
def test_trocar_preco_produto_envia_dados(client):
    """POST troca preço produto envia body completo."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/TROCA_PRECO_PRODUTO", status=204)

    client.produtos.trocar_preco(
        {"produtoCodigo": 10, "precoVenda": 12.90, "filialCodigo": 1}
    )

    body = json.loads(resp.calls[0].request.body)
    assert body["produtoCodigo"] == 10
    assert body["precoVenda"] == 12.90


# ─── POST /INTEGRACAO/PRODUTO_INVENTARIO ─────────────────────────────────────


@resp.activate
def test_inventario_produto_204(client):
    """POST inventário de produto retorna 204."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/PRODUTO_INVENTARIO", status=204)

    resultado = client.produtos.inventario(
        {"produtoCodigo": 5, "quantidade": 100.0, "filialCodigo": 1}
    )

    assert resultado is None


@resp.activate
def test_inventario_produto_envia_quantidade(client):
    """POST inventário deve enviar quantidade corretamente."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/PRODUTO_INVENTARIO", status=204)

    client.produtos.inventario({"produtoCodigo": 5, "quantidade": 250.5})

    body = json.loads(resp.calls[0].request.body)
    assert body["quantidade"] == 250.5


# ─── POST /INTEGRACAO/AJUSTE_ESTOQUE_PRODUTO ─────────────────────────────────


@resp.activate
def test_ajuste_estoque_204(client):
    """POST ajuste de estoque retorna 204."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/AJUSTE_ESTOQUE_PRODUTO", status=204)

    resultado = client.produtos.ajuste_estoque(
        {"produtoCodigo": 3, "quantidade": -10.0, "motivo": "Perda"}
    )

    assert resultado is None


@resp.activate
def test_ajuste_estoque_quantidade_negativa_aceita(client):
    """POST ajuste de estoque aceita quantidade negativa (baixa)."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/AJUSTE_ESTOQUE_PRODUTO", status=204)

    client.produtos.ajuste_estoque({"produtoCodigo": 3, "quantidade": -5.0})

    body = json.loads(resp.calls[0].request.body)
    assert body["quantidade"] == -5.0


# ─── POST /INTEGRACAO/REAJUSTAR_PRODUTO ──────────────────────────────────────


@resp.activate
def test_reajustar_produto_204(client):
    """POST reajuste de produto (percentual) retorna 204."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/REAJUSTAR_PRODUTO", status=204)

    resultado = client.produtos.reajustar(
        {"percentual": 5.0, "produtos": [1, 2, 3], "filialCodigo": 1}
    )

    assert resultado is None


@resp.activate
def test_reajustar_produto_envia_percentual(client):
    """POST reajuste deve enviar percentual corretamente."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/REAJUSTAR_PRODUTO", status=204)

    client.produtos.reajustar({"percentual": 8.5, "produtos": [10]})

    body = json.loads(resp.calls[0].request.body)
    assert body["percentual"] == 8.5
    assert 10 in body["produtos"]


# ─── POST /INTEGRACAO/PRODUTO_COMISSAO ───────────────────────────────────────


@resp.activate
def test_comissao_produto_204(client):
    """POST comissão de produto retorna 204."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/PRODUTO_COMISSAO", status=204)

    resultado = client.produtos.comissao(
        {"produtoCodigo": 7, "percentualComissao": 3.0}
    )

    assert resultado is None
