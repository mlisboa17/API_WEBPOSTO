"""
Testes unitários do WebPostoClient.
"""

import pytest
import responses as responses_lib
from datetime import date
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from webposto import WebPostoClient, WebPostoConfig
from webposto.exceptions import AuthError, ServerError


CHAVE_TESTE = "CHAVE_TESTE_123"
BASE_URL = "http://web.qualityautomacao.com.br"


@pytest.fixture
def config():
    return WebPostoConfig(chave=CHAVE_TESTE, base_url=BASE_URL)


@pytest.fixture
def client(config):
    return WebPostoClient(config)


# ── CONFIG ────────────────────────────────────────────────────────────────────


def test_config_chave_vazia_levanta_excecao():
    with pytest.raises(ValueError):
        WebPostoClient(WebPostoConfig(chave=""))


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("WEBPOSTO_CHAVE", "env_chave_123")
    monkeypatch.setenv("WEBPOSTO_EMPRESA_CODIGO", "5")
    config = WebPostoConfig.from_env()
    assert config.chave == "env_chave_123"
    assert config.empresa_codigo == 5


def test_config_from_env_sem_chave_levanta_excecao(monkeypatch):
    monkeypatch.delenv("WEBPOSTO_CHAVE", raising=False)
    monkeypatch.delenv("WEBPOSTO_API_KEY", raising=False)
    with pytest.raises(ValueError, match="WEBPOSTO"):
        WebPostoConfig.from_env()


# ── HTTP / AUTENTICAÇÃO ───────────────────────────────────────────────────────


@responses_lib.activate
def test_chave_incluida_em_todos_requests(client):
    responses_lib.add(
        responses_lib.GET,
        f"{BASE_URL}/INTEGRACAO/FILIAL",
        json=[{"codigo": 1, "nome": "Filial 1"}],
        status=200,
    )
    client.integracoes.listar_filiais()
    assert f"CHAVE={CHAVE_TESTE}" in responses_lib.calls[0].request.url


@responses_lib.activate
def test_erro_401_lanca_auth_error(client):
    responses_lib.add(
        responses_lib.GET,
        f"{BASE_URL}/INTEGRACAO/FILIAL",
        json={"error": "Unauthorized"},
        status=401,
    )
    with pytest.raises(AuthError):
        client.integracoes.listar_filiais()


@responses_lib.activate
def test_erro_500_lanca_server_error(client):
    responses_lib.add(
        responses_lib.GET,
        f"{BASE_URL}/INTEGRACAO/ABASTECIMENTO",
        json={"error": "Internal Server Error"},
        status=500,
    )
    with pytest.raises(ServerError):
        client.abastecimento.listar(date(2025, 1, 1), date(2025, 1, 31))


@responses_lib.activate
def test_resposta_204_retorna_none(client):
    responses_lib.add(
        responses_lib.PUT,
        f"{BASE_URL}/INTEGRACAO/RECEBER_TITULO",
        status=204,
    )
    resultado = client.financeiro.receber_titulo({"tituloCodigo": 1})
    assert resultado is None


# ── ABASTECIMENTO ────────────────────────────────────────────────────────────


@responses_lib.activate
def test_listar_abastecimentos_com_filtro_data(client):
    mock_data = [{"id": 1, "volume": 50.0, "produto": "GASOLINA"}]
    responses_lib.add(
        responses_lib.GET,
        f"{BASE_URL}/INTEGRACAO/ABASTECIMENTO",
        json=mock_data,
        status=200,
    )
    resultado = client.abastecimento.listar(
        data_inicial=date(2025, 1, 1),
        data_final=date(2025, 1, 31),
    )
    assert resultado == mock_data
    req_url = responses_lib.calls[0].request.url
    assert "dataInicial=2025-01-01" in req_url
    assert "dataFinal=2025-01-31" in req_url


# ── FINANCEIRO ────────────────────────────────────────────────────────────────


@responses_lib.activate
def test_listar_titulos_receber_com_situacao(client):
    mock_data = [{"id": 10, "valor": 1500.00, "situacao": "ABERTO"}]
    responses_lib.add(
        responses_lib.GET,
        f"{BASE_URL}/INTEGRACAO/TITULO_RECEBER",
        json=mock_data,
        status=200,
    )
    resultado = client.financeiro.listar_titulos_receber(
        data_inicial=date(2025, 1, 1),
        data_final=date(2025, 12, 31),
        situacao="ABERTO",
    )
    assert resultado == mock_data
    assert "situacaoReceber=ABERTO" in responses_lib.calls[0].request.url
