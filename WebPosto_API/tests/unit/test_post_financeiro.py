"""
Testes POST — Financeiro
Cobre: criar título a receber/pagar, transferência bancária,
       lançamento contábil, lote contábil, OFX.
"""

import json
import pytest
import responses as resp
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from webposto import WebPostoClient, WebPostoConfig
from webposto.exceptions import BadRequestError, ServerError

BASE = "http://web.qualityautomacao.com.br"
CHAVE = "CHAVE_TESTE_POST_FIN"


@pytest.fixture
def client():
    return WebPostoClient(WebPostoConfig(chave=CHAVE, base_url=BASE))


# ─── POST /INTEGRACAO/TITULO_RECEBER ─────────────────────────────────────────


@resp.activate
def test_criar_titulo_receber_retorna_dados(client):
    """POST título a receber deve retornar código e dados do título."""
    mock = {"tituloCodigo": 1001, "valor": 1500.00, "vencimento": "2025-05-10"}
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/TITULO_RECEBER", json=mock, status=201)

    resultado = client.financeiro.criar_titulo_receber(
        {"clienteCodigo": 10, "valor": 1500.00, "vencimento": "2025-05-10"}
    )

    assert resultado["tituloCodigo"] == 1001
    assert resultado["valor"] == 1500.00


@resp.activate
def test_criar_titulo_receber_envia_valor_correto(client):
    """POST título a receber deve enviar valor exato sem arredondamento."""
    resp.add(
        resp.POST,
        f"{BASE}/INTEGRACAO/TITULO_RECEBER",
        json={"tituloCodigo": 5},
        status=201,
    )

    client.financeiro.criar_titulo_receber(
        {"clienteCodigo": 20, "valor": 999.99, "vencimento": "2025-06-01"}
    )

    body = json.loads(resp.calls[0].request.body)
    assert body["valor"] == 999.99
    assert body["clienteCodigo"] == 20


@resp.activate
def test_criar_titulo_receber_400_campos_obrigatorios(client):
    """POST título sem cliente deve retornar 400."""
    resp.add(
        resp.POST,
        f"{BASE}/INTEGRACAO/TITULO_RECEBER",
        json={"error": "clienteCodigo obrigatório"},
        status=400,
    )

    with pytest.raises(BadRequestError) as exc:
        client.financeiro.criar_titulo_receber({"valor": 100.0})

    assert exc.value.status_code == 400


@resp.activate
def test_criar_titulo_receber_chave_na_url(client):
    """POST título a receber deve incluir CHAVE na URL."""
    resp.add(
        resp.POST,
        f"{BASE}/INTEGRACAO/TITULO_RECEBER",
        json={"tituloCodigo": 1},
        status=201,
    )

    client.financeiro.criar_titulo_receber({"clienteCodigo": 1, "valor": 100.0})

    assert f"CHAVE={CHAVE}" in resp.calls[0].request.url


# ─── POST /INTEGRACAO/TITULO_PAGAR ───────────────────────────────────────────


@resp.activate
def test_criar_titulo_pagar_retorna_dados(client):
    """POST título a pagar deve retornar código do título."""
    mock = {"tituloCodigo": 2002, "valor": 3200.00}
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/TITULO_PAGAR", json=mock, status=201)

    resultado = client.financeiro.criar_titulo_pagar(
        {"fornecedorCodigo": 5, "valor": 3200.00, "vencimento": "2025-05-20"}
    )

    assert resultado["tituloCodigo"] == 2002


@resp.activate
def test_criar_titulo_pagar_envia_fornecedor(client):
    """POST título a pagar deve enviar fornecedorCodigo no body."""
    resp.add(
        resp.POST,
        f"{BASE}/INTEGRACAO/TITULO_PAGAR",
        json={"tituloCodigo": 10},
        status=201,
    )

    client.financeiro.criar_titulo_pagar(
        {"fornecedorCodigo": 99, "valor": 500.00, "vencimento": "2025-07-01"}
    )

    body = json.loads(resp.calls[0].request.body)
    assert body["fornecedorCodigo"] == 99
    assert body["valor"] == 500.00


@resp.activate
def test_criar_titulo_pagar_500_lanca_server_error(client):
    """POST título a pagar com erro do servidor deve lançar ServerError."""
    resp.add(
        resp.POST,
        f"{BASE}/INTEGRACAO/TITULO_PAGAR",
        json={"error": "Database error"},
        status=500,
    )

    with pytest.raises(ServerError):
        client.financeiro.criar_titulo_pagar({"fornecedorCodigo": 1, "valor": 100.0})


# ─── POST /INTEGRACAO/TRANSFERENCIA_BANCARIA ─────────────────────────────────


@resp.activate
def test_criar_transferencia_bancaria_204(client):
    """POST transferência bancária retorna 204."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/TRANSFERENCIA_BANCARIA", status=204)

    resultado = client.financeiro.criar_transferencia(
        {"contaOrigem": 1, "contaDestino": 2, "valor": 5000.00, "data": "2025-04-07"}
    )

    assert resultado is None


@resp.activate
def test_criar_transferencia_envia_contas_corretamente(client):
    """POST transferência deve enviar contaOrigem e contaDestino corretos."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/TRANSFERENCIA_BANCARIA", status=204)

    client.financeiro.criar_transferencia(
        {"contaOrigem": 10, "contaDestino": 20, "valor": 1000.00}
    )

    body = json.loads(resp.calls[0].request.body)
    assert body["contaOrigem"] == 10
    assert body["contaDestino"] == 20
    assert body["valor"] == 1000.00


@resp.activate
def test_criar_transferencia_400_conta_invalida(client):
    """POST transferência com conta inválida deve lançar BadRequestError."""
    resp.add(
        resp.POST,
        f"{BASE}/INTEGRACAO/TRANSFERENCIA_BANCARIA",
        json={"error": "Conta não encontrada"},
        status=400,
    )

    with pytest.raises(BadRequestError):
        client.financeiro.criar_transferencia({"contaOrigem": 9999, "valor": 100.0})


# ─── POST /INTEGRACAO/INCLUIR_LANCAMENTO_CONTABIL ────────────────────────────


@resp.activate
def test_incluir_lancamento_contabil_retorna_dados(client):
    """POST lançamento contábil deve retornar loteContabil e referencia."""
    mock = {"loteContabil": 55, "referencia": 1}
    resp.add(
        resp.POST,
        f"{BASE}/INTEGRACAO/INCLUIR_LANCAMENTO_CONTABIL",
        json=mock,
        status=201,
    )

    resultado = client.financeiro.incluir_lancamento_contabil(
        {
            "data": "2025-04-07",
            "documento": "NF-001",
            "empresaCodigo": 1,
            "lancamentoContabil": [],
        }
    )

    assert resultado["loteContabil"] == 55
    assert resultado["referencia"] == 1


@resp.activate
def test_incluir_lancamento_envia_campos_obrigatorios(client):
    """POST lançamento deve enviar data, documento e empresaCodigo."""
    resp.add(
        resp.POST,
        f"{BASE}/INTEGRACAO/INCLUIR_LANCAMENTO_CONTABIL",
        json={"loteContabil": 1, "referencia": 1},
        status=201,
    )

    client.financeiro.incluir_lancamento_contabil(
        {
            "data": "2025-04-07",
            "documento": "DOC-123",
            "empresaCodigo": 2,
            "lancamentoContabil": [{"debito": 1000, "credito": 1000}],
        }
    )

    body = json.loads(resp.calls[0].request.body)
    assert body["data"] == "2025-04-07"
    assert body["documento"] == "DOC-123"
    assert body["empresaCodigo"] == 2


# ─── POST /INTEGRACAO/INCLUIR_LOTE_CONTABIL ──────────────────────────────────


@resp.activate
def test_incluir_lote_contabil_retorna_lote(client):
    """POST lote contábil deve retornar loteContabil."""
    resp.add(
        resp.POST,
        f"{BASE}/INTEGRACAO/INCLUIR_LOTE_CONTABIL",
        json={"loteContabil": 88, "referencia": 3},
        status=201,
    )

    resultado = client.financeiro.incluir_lote_contabil(
        {
            "data": "2025-04-07",
            "documento": "LOTE-01",
            "empresaCodigo": 1,
            "lancamentoContabil": [],
        }
    )

    assert resultado["loteContabil"] == 88


# ─── POST /INTEGRACAO/INCLUIR_OFX ────────────────────────────────────────────


@resp.activate
def test_incluir_ofx_204(client):
    """POST OFX retorna 204 sem body."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/INCLUIR_OFX", status=204)

    resultado = client.financeiro.incluir_ofx(
        {
            "cdConta": 1,
            "cdFilial": 1,
            "dataInicial": "2025-04-01",
            "opcaoImportacao": "IMPORTAR_APENAS_DIAS_INEXISTENTES_SISTEMA",
            "transacoes": [],
        }
    )

    assert resultado is None


@resp.activate
def test_incluir_ofx_envia_opcao_importacao(client):
    """POST OFX deve enviar opcaoImportacao corretamente."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/INCLUIR_OFX", status=204)

    client.financeiro.incluir_ofx(
        {
            "cdConta": 2,
            "cdFilial": 1,
            "dataInicial": "2025-04-01",
            "opcaoImportacao": "EXCLUIR_DIAS_SISTEMA",
            "transacoes": [
                {"valor": 100.0, "data": "2025-04-01", "descricao": "Teste"}
            ],
        }
    )

    body = json.loads(resp.calls[0].request.body)
    assert body["opcaoImportacao"] == "EXCLUIR_DIAS_SISTEMA"
    assert len(body["transacoes"]) == 1
