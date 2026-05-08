"""
Testes PUT — Atualizar entidades e receber pagamentos
Cobre: atualizar cliente, produto, grupo, frota,
       receber título, cheque, cartão, reajustar estoque.
"""

import json
import pytest
import responses as resp
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from webposto import WebPostoClient, WebPostoConfig
from webposto.exceptions import BadRequestError, NotFoundError

BASE = "http://web.qualityautomacao.com.br"
CHAVE = "CHAVE_TESTE_PUT"


@pytest.fixture
def client():
    return WebPostoClient(WebPostoConfig(chave=CHAVE, base_url=BASE))


# ─── PUT /INTEGRACAO/CLIENTE/{id} ────────────────────────────────────────────


@resp.activate
def test_atualizar_cliente_retorna_none(client):
    """PUT cliente deve retornar 204 (sem body)."""
    resp.add(resp.PUT, f"{BASE}/INTEGRACAO/CLIENTE/42", status=204)

    resultado = client.clientes.atualizar(42, {"nome": "João Atualizado"})

    assert resultado is None


@resp.activate
def test_atualizar_cliente_usa_id_na_url(client):
    """PUT cliente deve incluir o ID na URL."""
    resp.add(resp.PUT, f"{BASE}/INTEGRACAO/CLIENTE/99", status=204)

    client.clientes.atualizar(99, {"nome": "Novo Nome"})

    assert "/INTEGRACAO/CLIENTE/99" in resp.calls[0].request.url


@resp.activate
def test_atualizar_cliente_envia_campos(client):
    """PUT cliente deve enviar todos os campos informados."""
    resp.add(resp.PUT, f"{BASE}/INTEGRACAO/CLIENTE/10", status=204)

    client.clientes.atualizar(10, {"nome": "Maria Silva", "email": "maria@email.com"})

    body = json.loads(resp.calls[0].request.body)
    assert body["nome"] == "Maria Silva"
    assert body["email"] == "maria@email.com"


@resp.activate
def test_atualizar_cliente_404_nao_encontrado(client):
    """PUT cliente inexistente deve lançar NotFoundError."""
    resp.add(
        resp.PUT,
        f"{BASE}/INTEGRACAO/CLIENTE/9999",
        json={"error": "Cliente não encontrado"},
        status=404,
    )

    with pytest.raises(NotFoundError):
        client.clientes.atualizar(9999, {"nome": "Fantasma"})


@resp.activate
def test_atualizar_cliente_400_dados_invalidos(client):
    """PUT cliente com CPF inválido deve lançar BadRequestError."""
    resp.add(
        resp.PUT,
        f"{BASE}/INTEGRACAO/CLIENTE/5",
        json={"error": "CPF inválido"},
        status=400,
    )

    with pytest.raises(BadRequestError):
        client.clientes.atualizar(5, {"cpfCnpj": "invalido"})


@resp.activate
def test_atualizar_cliente_chave_na_url(client):
    """PUT cliente deve incluir CHAVE na query string."""
    resp.add(resp.PUT, f"{BASE}/INTEGRACAO/CLIENTE/1", status=204)

    client.clientes.atualizar(1, {"nome": "Teste"})

    assert f"CHAVE={CHAVE}" in resp.calls[0].request.url


# ─── PUT /INTEGRACAO/GRUPO_CLIENTE/{id} ──────────────────────────────────────


@resp.activate
def test_atualizar_grupo_204(client):
    """PUT grupo de clientes retorna 204."""
    resp.add(resp.PUT, f"{BASE}/INTEGRACAO/GRUPO_CLIENTE/7", status=204)

    resultado = client.clientes.atualizar_grupo(7, {"nome": "Grupo VIP"})

    assert resultado is None


@resp.activate
def test_atualizar_grupo_id_correto_na_url(client):
    """PUT grupo deve usar o ID correto na URL."""
    resp.add(resp.PUT, f"{BASE}/INTEGRACAO/GRUPO_CLIENTE/15", status=204)

    client.clientes.atualizar_grupo(15, {"nome": "Grupo B"})

    assert "/INTEGRACAO/GRUPO_CLIENTE/15" in resp.calls[0].request.url


# ─── PUT /INTEGRACAO/ALTERAR_PRODUTO/{id} ────────────────────────────────────


@resp.activate
def test_atualizar_produto_204(client):
    """PUT produto retorna 204."""
    resp.add(resp.PUT, f"{BASE}/INTEGRACAO/ALTERAR_PRODUTO/3", status=204)

    resultado = client.produtos.atualizar(3, {"precoVenda": 7.99})

    assert resultado is None


@resp.activate
def test_atualizar_produto_envia_preco(client):
    """PUT produto deve enviar novo preço corretamente."""
    resp.add(resp.PUT, f"{BASE}/INTEGRACAO/ALTERAR_PRODUTO/3", status=204)

    client.produtos.atualizar(3, {"precoVenda": 8.49, "nome": "GASOLINA ADITIVADA"})

    body = json.loads(resp.calls[0].request.body)
    assert body["precoVenda"] == 8.49
    assert body["nome"] == "GASOLINA ADITIVADA"


@resp.activate
def test_atualizar_produto_404(client):
    """PUT produto inexistente deve lançar NotFoundError."""
    resp.add(
        resp.PUT,
        f"{BASE}/INTEGRACAO/ALTERAR_PRODUTO/9999",
        json={"error": "Produto não encontrado"},
        status=404,
    )

    with pytest.raises(NotFoundError):
        client.produtos.atualizar(9999, {"precoVenda": 5.0})


# ─── PUT /INTEGRACAO/RECEBER_TITULO ──────────────────────────────────────────


@resp.activate
def test_receber_titulo_204(client):
    """PUT receber título retorna 204."""
    resp.add(resp.PUT, f"{BASE}/INTEGRACAO/RECEBER_TITULO", status=204)

    resultado = client.financeiro.receber_titulo(
        {
            "tituloCodigo": 1001,
            "valorRecebido": 1500.00,
            "dataRecebimento": "2025-04-07",
        }
    )

    assert resultado is None


@resp.activate
def test_receber_titulo_envia_valor_e_data(client):
    """PUT receber título deve enviar valorRecebido e dataRecebimento."""
    resp.add(resp.PUT, f"{BASE}/INTEGRACAO/RECEBER_TITULO", status=204)

    client.financeiro.receber_titulo(
        {"tituloCodigo": 500, "valorRecebido": 750.00, "dataRecebimento": "2025-04-07"}
    )

    body = json.loads(resp.calls[0].request.body)
    assert body["tituloCodigo"] == 500
    assert body["valorRecebido"] == 750.00
    assert body["dataRecebimento"] == "2025-04-07"


@resp.activate
def test_receber_titulo_400_titulo_ja_recebido(client):
    """PUT receber título já recebido deve lançar BadRequestError."""
    resp.add(
        resp.PUT,
        f"{BASE}/INTEGRACAO/RECEBER_TITULO",
        json={"error": "Título já recebido"},
        status=400,
    )

    with pytest.raises(BadRequestError) as exc:
        client.financeiro.receber_titulo({"tituloCodigo": 1, "valorRecebido": 100.0})

    assert exc.value.status_code == 400


@resp.activate
def test_receber_titulo_convertido_204(client):
    """PUT receber título convertido retorna 204."""
    resp.add(resp.PUT, f"{BASE}/INTEGRACAO/RECEBER_TITULO_CONVERTIDO", status=204)

    resultado = client.financeiro.receber_titulo_convertido(
        {"tituloCodigo": 200, "valorRecebido": 300.00}
    )

    assert resultado is None


# ─── PUT /INTEGRACAO/RECEBER_CHEQUE ──────────────────────────────────────────


@resp.activate
def test_receber_cheque_204(client):
    """PUT receber cheque retorna 204."""
    resp.add(resp.PUT, f"{BASE}/INTEGRACAO/RECEBER_CHEQUE", status=204)

    resultado = client.financeiro.receber_cheque(
        {"tituloCodigo": 100, "numeroCheque": "12345", "banco": "001"}
    )

    assert resultado is None


@resp.activate
def test_receber_cheque_envia_numero_e_banco(client):
    """PUT receber cheque deve enviar numeroCheque e banco."""
    resp.add(resp.PUT, f"{BASE}/INTEGRACAO/RECEBER_CHEQUE", status=204)

    client.financeiro.receber_cheque(
        {"tituloCodigo": 88, "numeroCheque": "99999", "banco": "033"}
    )

    body = json.loads(resp.calls[0].request.body)
    assert body["numeroCheque"] == "99999"
    assert body["banco"] == "033"


@resp.activate
def test_receber_cheque_com_empresa_codigo(client):
    """PUT receber cheque aceita empresaCodigo como query param opcional."""
    resp.add(resp.PUT, f"{BASE}/INTEGRACAO/RECEBER_CHEQUE", status=204)

    client.financeiro.receber_cheque(
        {"tituloCodigo": 10, "numeroCheque": "111"}, empresa_codigo=2
    )

    assert "empresaCodigo=2" in resp.calls[0].request.url


# ─── PUT /INTEGRACAO/RECEBER_CARTAO ──────────────────────────────────────────


@resp.activate
def test_receber_cartao_204(client):
    """PUT receber cartão retorna 204."""
    resp.add(resp.PUT, f"{BASE}/INTEGRACAO/RECEBER_CARTAO", status=204)

    resultado = client.financeiro.receber_cartao(
        {"tituloCodigo": 300, "administradoraCodigo": 5, "valorRecebido": 500.00}
    )

    assert resultado is None


@resp.activate
def test_receber_cartao_envia_administradora(client):
    """PUT receber cartão deve enviar administradoraCodigo."""
    resp.add(resp.PUT, f"{BASE}/INTEGRACAO/RECEBER_CARTAO", status=204)

    client.financeiro.receber_cartao(
        {"tituloCodigo": 10, "administradoraCodigo": 3, "valorRecebido": 200.00}
    )

    body = json.loads(resp.calls[0].request.body)
    assert body["administradoraCodigo"] == 3


@resp.activate
def test_receber_cartao_400_administradora_invalida(client):
    """PUT receber cartão com administradora inválida lança BadRequestError."""
    resp.add(
        resp.PUT,
        f"{BASE}/INTEGRACAO/RECEBER_CARTAO",
        json={"error": "Administradora não encontrada"},
        status=400,
    )

    with pytest.raises(BadRequestError):
        client.financeiro.receber_cartao({"administradoraCodigo": 9999})


# ─── PUT /INTEGRACAO/REAJUSTAR_ESTOQUE_PRODUTO_COMBUSTIVEL ───────────────────


@resp.activate
def test_reajustar_estoque_combustivel_204(client):
    """PUT reajuste de estoque combustível retorna 204."""
    resp.add(
        resp.PUT, f"{BASE}/INTEGRACAO/REAJUSTAR_ESTOQUE_PRODUTO_COMBUSTIVEL", status=204
    )

    resultado = client.abastecimento.reajustar_estoque_combustivel(
        {"produtoCodigo": 1, "quantidade": 5000.0, "filialCodigo": 1}
    )

    assert resultado is None


@resp.activate
def test_reajustar_estoque_envia_quantidade(client):
    """PUT reajuste estoque deve enviar quantidade corretamente."""
    resp.add(
        resp.PUT, f"{BASE}/INTEGRACAO/REAJUSTAR_ESTOQUE_PRODUTO_COMBUSTIVEL", status=204
    )

    client.abastecimento.reajustar_estoque_combustivel(
        {"produtoCodigo": 2, "quantidade": 8000.5, "filialCodigo": 2}
    )

    body = json.loads(resp.calls[0].request.body)
    assert body["quantidade"] == 8000.5
    assert body["produtoCodigo"] == 2


# ─── PUT /INTEGRACAO/CLIENTE_FROTA_VEICULO/{clienteCodigo}/{clienteVeiculoCodigo}


@resp.activate
def test_atualizar_veiculo_frota_204(client):
    """PUT veículo de frota retorna 204."""
    resp.add(resp.PUT, f"{BASE}/INTEGRACAO/CLIENTE_FROTA_VEICULO/10/5", status=204)

    resultado = client.clientes.atualizar_veiculo_frota(10, 5, {"placa": "ABC-1234"})

    assert resultado is None


@resp.activate
def test_atualizar_veiculo_frota_ids_corretos_na_url(client):
    """PUT veículo deve usar clienteCodigo e clienteVeiculoCodigo na URL."""
    resp.add(resp.PUT, f"{BASE}/INTEGRACAO/CLIENTE_FROTA_VEICULO/20/8", status=204)

    client.clientes.atualizar_veiculo_frota(20, 8, {"placa": "XYZ-9999"})

    url = resp.calls[0].request.url
    assert "/CLIENTE_FROTA_VEICULO/20/8" in url


@resp.activate
def test_atualizar_veiculo_frota_envia_placa(client):
    """PUT veículo de frota deve enviar placa no body."""
    resp.add(resp.PUT, f"{BASE}/INTEGRACAO/CLIENTE_FROTA_VEICULO/1/1", status=204)

    client.clientes.atualizar_veiculo_frota(
        1, 1, {"placa": "DEF-5678", "modelo": "GOL"}
    )

    body = json.loads(resp.calls[0].request.body)
    assert body["placa"] == "DEF-5678"
    assert body["modelo"] == "GOL"
