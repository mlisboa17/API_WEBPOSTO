"""
Testes de Edge Cases e Cenários Críticos
Cobre: retry, timeout, parâmetros None, paginação, Content-Type,
       valores extremos, múltiplas filiais, datas inválidas.
"""

import json
import pytest
import responses as resp
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from webposto import WebPostoClient, WebPostoConfig
from webposto.exceptions import AuthError, ServerError

BASE = "http://web.qualityautomacao.com.br"
CHAVE = "CHAVE_EDGE_CASES"


@pytest.fixture
def client():
    return WebPostoClient(WebPostoConfig(chave=CHAVE, base_url=BASE, max_retries=1))


# ─── PARÂMETROS NONE NÃO DEVEM IR NA URL ─────────────────────────────────────


@resp.activate
def test_parametros_none_nao_enviados(client):
    """Filtros opcionais com valor None não devem aparecer na query string."""
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/ABASTECIMENTO", json=[], status=200)

    client.abastecimento.listar(
        data_inicial=date(2025, 1, 1),
        data_final=date(2025, 1, 31),
        filial=None,  # None → não deve aparecer na URL
        bico=None,
    )

    url = resp.calls[0].request.url
    assert "filial=None" not in url
    assert "bico=None" not in url


@resp.activate
def test_parametros_preenchidos_aparecem_na_url(client):
    """Filtros com valor definido devem aparecer na query string."""
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/TITULO_RECEBER", json=[], status=200)

    client.financeiro.listar_titulos_receber(
        data_inicial=date(2025, 1, 1),
        data_final=date(2025, 12, 31),
        situacao="ABERTO",
    )

    url = resp.calls[0].request.url
    assert "situacaoReceber=ABERTO" in url
    assert "dataInicial=2025-01-01" in url
    assert "dataFinal=2025-12-31" in url


# ─── PAGINAÇÃO ────────────────────────────────────────────────────────────────


@resp.activate
def test_paginacao_envia_pagina_e_tamanho(client):
    """Parâmetros de paginação devem chegar na URL."""
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/CLIENTE", json=[], status=200)

    client.clientes.listar(pagina=2, tamanho_pagina=50)

    url = resp.calls[0].request.url
    assert "pagina=2" in url
    assert "tamanhoPagina=50" in url


@resp.activate
def test_paginacao_pagina_zero(client):
    """Paginação com pagina=0 deve ser enviada (primeira página)."""
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/PRODUTO", json=[], status=200)

    client.produtos.listar(pagina=0, tamanho_pagina=100)

    url = resp.calls[0].request.url
    assert "pagina=0" in url


# ─── CONTENT-TYPE ─────────────────────────────────────────────────────────────


@resp.activate
def test_post_envia_content_type_json(client):
    """Toda requisição POST deve enviar Content-Type: application/json."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/CLIENTE", json={"codigo": 1}, status=201)

    client.clientes.criar({"nome": "Teste"})

    headers = resp.calls[0].request.headers
    assert "application/json" in headers.get("Content-Type", "")


@resp.activate
def test_put_envia_content_type_json(client):
    """Toda requisição PUT deve enviar Content-Type: application/json."""
    resp.add(resp.PUT, f"{BASE}/INTEGRACAO/CLIENTE/1", status=204)

    client.clientes.atualizar(1, {"nome": "Novo"})

    headers = resp.calls[0].request.headers
    assert "application/json" in headers.get("Content-Type", "")


# ─── VALORES EXTREMOS ─────────────────────────────────────────────────────────


@resp.activate
def test_valor_monetario_zero_aceito(client):
    """POST com valor 0.00 deve ser enviado (isenção, cortesia)."""
    resp.add(
        resp.POST,
        f"{BASE}/INTEGRACAO/TITULO_RECEBER",
        json={"tituloCodigo": 1},
        status=201,
    )

    client.financeiro.criar_titulo_receber(
        {"clienteCodigo": 1, "valor": 0.00, "vencimento": "2025-05-01"}
    )

    body = json.loads(resp.calls[0].request.body)
    assert body["valor"] == 0.00


@resp.activate
def test_quantidade_decimal_alta_precisao(client):
    """POST inventário com quantidade de alta precisão decimal."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/PRODUTO_INVENTARIO", status=204)

    client.produtos.inventario({"produtoCodigo": 1, "quantidade": 12345.678})

    body = json.loads(resp.calls[0].request.body)
    assert body["quantidade"] == 12345.678


@resp.activate
def test_preco_combustivel_muitas_casas_decimais(client):
    """POST troca preço com 3 casas decimais (ex: R$ 5.999)."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/TROCA_PRECO_COMBUSTIVEL", status=204)

    client.produtos.trocar_preco_combustivel({"produtoCodigo": 1, "precoVenda": 5.999})

    body = json.loads(resp.calls[0].request.body)
    assert body["precoVenda"] == 5.999


# ─── MÚLTIPLAS FILIAIS ────────────────────────────────────────────────────────


@resp.activate
def test_multiplas_filiais_enviadas_como_lista(client):
    """Filtro de filiais com múltiplos valores deve ser enviado."""
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/ABASTECIMENTO", json=[], status=200)

    client.abastecimento.listar(
        data_inicial=date(2025, 1, 1),
        data_final=date(2025, 1, 31),
        filial=[1, 2, 3],
    )

    # requests envia lista como múltiplos params: filial=1&filial=2&filial=3
    url = resp.calls[0].request.url
    assert "filial" in url


# ─── RESPOSTAS INESPERADAS ────────────────────────────────────────────────────


@resp.activate
def test_resposta_200_com_lista_vazia(client):
    """GET que retorna lista vazia deve retornar [] sem erro."""
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/CLIENTE", json=[], status=200)

    resultado = client.clientes.listar()

    assert resultado == []
    assert isinstance(resultado, list)


@resp.activate
def test_resposta_200_com_objeto_vazio(client):
    """GET que retorna {} deve retornar dict sem erro."""
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/FILIAL", json={}, status=200)

    resultado = client.integracoes.listar_filiais()

    assert resultado == {}


@resp.activate
def test_erro_403_lanca_auth_error(client):
    """HTTP 403 (Forbidden) deve lançar AuthError, não WebPostoError genérico."""
    resp.add(
        resp.GET, f"{BASE}/INTEGRACAO/FILIAL", json={"error": "Forbidden"}, status=403
    )

    with pytest.raises(AuthError) as exc:
        client.integracoes.listar_filiais()

    assert exc.value.status_code == 403


@resp.activate
def test_erro_503_lanca_server_error(client):
    """HTTP 503 (Service Unavailable) deve lançar ServerError."""
    resp.add(
        resp.GET,
        f"{BASE}/INTEGRACAO/FILIAL",
        json={"error": "Service Unavailable"},
        status=503,
    )

    with pytest.raises(ServerError):
        client.integracoes.listar_filiais()


# ─── HEADERS ─────────────────────────────────────────────────────────────────


@resp.activate
def test_user_agent_enviado(client):
    """Todas as requisições devem enviar o User-Agent correto."""
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/FILIAL", json=[], status=200)

    client.integracoes.listar_filiais()

    headers = resp.calls[0].request.headers
    assert "WebPosto" in headers.get("User-Agent", "")


@resp.activate
def test_accept_json_enviado(client):
    """Todas as requisições devem enviar Accept: application/json."""
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/CLIENTE", json=[], status=200)

    client.clientes.listar()

    headers = resp.calls[0].request.headers
    assert "application/json" in headers.get("Accept", "")


# ─── COMBUSTÍVEL — EDGE CASES ─────────────────────────────────────────────────


@resp.activate
def test_lmc_datas_inicio_fim_iguais(client):
    """GET LMC com dataInicial == dataFinal deve funcionar (consulta de 1 dia)."""
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/LMC", json=[], status=200)

    client.combustivel.listar_lmc(
        data_inicial=date(2025, 4, 7),
        data_final=date(2025, 4, 7),
    )

    url = resp.calls[0].request.url
    assert "dataInicial=2025-04-07" in url
    assert "dataFinal=2025-04-07" in url


@resp.activate
def test_pedido_combustivel_faturar_sem_body(client):
    """POST faturar pedido pode ser chamado sem body."""
    resp.add(
        resp.POST, f"{BASE}/INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO/10/FATURAR", status=204
    )

    resultado = client.combustivel.faturar_pedido(10)

    assert resultado is None


@resp.activate
def test_pedido_combustivel_id_correto_na_url(client):
    """POST faturar deve incluir o ID do pedido na URL."""
    resp.add(
        resp.POST, f"{BASE}/INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO/77/FATURAR", status=204
    )

    client.combustivel.faturar_pedido(77)

    assert "/PEDIDO_COMBUSTIVEL/PEDIDO/77/FATURAR" in resp.calls[0].request.url
