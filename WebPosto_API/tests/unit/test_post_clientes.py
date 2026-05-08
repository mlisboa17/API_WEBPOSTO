"""
Testes POST — Clientes
Cobre: criação, grupos, frota, prazo, vínculo de unidade de negócio.
"""

import pytest
import responses as resp
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from webposto import WebPostoClient, WebPostoConfig
from webposto.exceptions import AuthError, BadRequestError, ServerError

BASE = "http://web.qualityautomacao.com.br"
CHAVE = "CHAVE_TESTE_POST_CLI"


@pytest.fixture
def client():
    return WebPostoClient(WebPostoConfig(chave=CHAVE, base_url=BASE))


# ─── POST /INTEGRACAO/CLIENTE ─────────────────────────────────────────────────


@resp.activate
def test_criar_cliente_retorna_dados(client):
    """POST cliente deve retornar o objeto criado com id."""
    payload = {
        "nome": "João Silva",
        "cpfCnpj": "123.456.789-00",
        "email": "joao@email.com",
    }
    mock_resp = {"codigo": 42, "nome": "João Silva"}
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/CLIENTE", json=mock_resp, status=201)

    resultado = client.clientes.criar(payload)

    assert resultado["codigo"] == 42
    assert resultado["nome"] == "João Silva"


@resp.activate
def test_criar_cliente_envia_body_correto(client):
    """POST cliente deve enviar exatamente o body informado."""
    import json

    payload = {"nome": "Maria Souza", "cpfCnpj": "987.654.321-00"}
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/CLIENTE", json={"codigo": 99}, status=201)

    client.clientes.criar(payload)

    body_enviado = json.loads(resp.calls[0].request.body)
    assert body_enviado["nome"] == "Maria Souza"
    assert body_enviado["cpfCnpj"] == "987.654.321-00"


@resp.activate
def test_criar_cliente_400_lanca_bad_request(client):
    """POST com dados inválidos deve lançar BadRequestError."""
    resp.add(
        resp.POST,
        f"{BASE}/INTEGRACAO/CLIENTE",
        json={"error": "CPF inválido"},
        status=400,
    )

    with pytest.raises(BadRequestError) as exc:
        client.clientes.criar({"cpfCnpj": "invalido"})

    assert exc.value.status_code == 400


@resp.activate
def test_criar_cliente_401_lanca_auth_error(client):
    """POST com chave inválida deve lançar AuthError."""
    resp.add(
        resp.POST,
        f"{BASE}/INTEGRACAO/CLIENTE",
        json={"error": "Unauthorized"},
        status=401,
    )

    with pytest.raises(AuthError):
        client.clientes.criar({"nome": "Teste"})


@resp.activate
def test_criar_cliente_chave_presente_no_post(client):
    """Chave deve estar na query string mesmo em POST."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/CLIENTE", json={"codigo": 1}, status=201)

    client.clientes.criar({"nome": "Teste"})

    assert f"CHAVE={CHAVE}" in resp.calls[0].request.url


# ─── POST /INTEGRACAO/GRUPO_CLIENTE ──────────────────────────────────────────


@resp.activate
def test_criar_grupo_cliente_retorna_dados(client):
    """POST grupo de clientes deve retornar id do grupo criado."""
    resp.add(
        resp.POST,
        f"{BASE}/INTEGRACAO/GRUPO_CLIENTE",
        json={"codigo": 7, "nome": "Frota Premium"},
        status=201,
    )

    resultado = client.clientes.criar_grupo({"nome": "Frota Premium"})

    assert resultado["codigo"] == 7


@resp.activate
def test_criar_grupo_cliente_500_lanca_server_error(client):
    """Erro interno no servidor deve lançar ServerError."""
    resp.add(
        resp.POST,
        f"{BASE}/INTEGRACAO/GRUPO_CLIENTE",
        json={"error": "Internal Error"},
        status=500,
    )

    with pytest.raises(ServerError):
        client.clientes.criar_grupo({"nome": "Grupo Teste"})


# ─── POST /INTEGRACAO/INTEGRACAO_CLIENTE_PRAZO ────────────────────────────────


@resp.activate
def test_integrar_prazo_cliente_sem_retorno(client):
    """POST prazo retorna 204 sem body."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/INTEGRACAO_CLIENTE_PRAZO", status=204)

    resultado = client.clientes.integrar_prazo({"clienteCodigo": 10, "prazo": 30})

    assert resultado is None


@resp.activate
def test_integrar_prazo_envia_campos_corretos(client):
    """POST prazo deve enviar clienteCodigo e prazo no body."""
    import json

    resp.add(resp.POST, f"{BASE}/INTEGRACAO/INTEGRACAO_CLIENTE_PRAZO", status=204)

    client.clientes.integrar_prazo({"clienteCodigo": 55, "prazo": 60})

    body = json.loads(resp.calls[0].request.body)
    assert body["clienteCodigo"] == 55
    assert body["prazo"] == 60


# ─── POST /INTEGRACAO/VINCULAR_CLIENTE_UNIDADE_NEGOCIO ───────────────────────


@resp.activate
def test_vincular_unidade_negocio_204(client):
    """POST vínculo deve aceitar 204."""
    resp.add(
        resp.POST, f"{BASE}/INTEGRACAO/VINCULAR_CLIENTE_UNIDADE_NEGOCIO", status=204
    )

    resultado = client.clientes.vincular_unidade_negocio(
        {"clienteCodigo": 1, "unidadeCodigo": 2}
    )

    assert resultado is None
