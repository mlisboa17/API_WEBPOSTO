"""
Testes GET — Cobertura 100%
Cobre todos os métodos restantes:
abastecimento, clientes, combustivel, financeiro,
integracoes, produtos, relatorios.
"""

import json
import pytest
import responses as resp
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from webposto import WebPostoClient, WebPostoConfig
from webposto.exceptions import AuthError, NotFoundError, ServerError

BASE = "http://web.qualityautomacao.com.br"
CHAVE = "CHAVE_FULL_COVERAGE"


@pytest.fixture
def client():
    return WebPostoClient(WebPostoConfig(chave=CHAVE, base_url=BASE))


# ══════════════════════════════════════════════════════════════════
# ABASTECIMENTO
# ══════════════════════════════════════════════════════════════════


@resp.activate
def test_listar_encerrante_retorna_lista(client):
    """GET encerrante deve retornar lista de encerrantes."""
    mock = [{"id": 1, "bico": 3, "leitura": 120000.5}]
    resp.add(
        resp.GET, f"{BASE}/INTEGRACAO/ABASTECIMENTO_ENCERRANTE", json=mock, status=200
    )

    resultado = client.abastecimento.listar_encerrante(
        data_inicial=date(2025, 4, 1), data_final=date(2025, 4, 7)
    )

    assert resultado == mock
    url = resp.calls[0].request.url
    assert "dataInicial=2025-04-01" in url


@resp.activate
def test_listar_encerrante_com_filial(client):
    """GET encerrante deve aceitar filtro de filial."""
    resp.add(
        resp.GET, f"{BASE}/INTEGRACAO/ABASTECIMENTO_ENCERRANTE", json=[], status=200
    )

    client.abastecimento.listar_encerrante(
        data_inicial=date(2025, 4, 1), data_final=date(2025, 4, 7), filial=[1, 2]
    )

    assert "filial" in resp.calls[0].request.url


@resp.activate
def test_listar_divergencia_retorna_lista(client):
    """GET divergência de abastecimento deve retornar lista."""
    mock = [{"id": 5, "diferenca": 10.5}]
    resp.add(
        resp.GET, f"{BASE}/INTEGRACAO/ABASTECIMENTO_DIVERGENCIA", json=mock, status=200
    )

    resultado = client.abastecimento.listar_divergencia(
        data_inicial=date(2025, 4, 1), data_final=date(2025, 4, 7)
    )

    assert resultado[0]["diferenca"] == 10.5


@resp.activate
def test_listar_divergencia_404(client):
    """GET divergência com filial inválida deve lançar NotFoundError."""
    resp.add(
        resp.GET,
        f"{BASE}/INTEGRACAO/ABASTECIMENTO_DIVERGENCIA",
        json={"error": "Filial não encontrada"},
        status=404,
    )

    with pytest.raises(NotFoundError):
        client.abastecimento.listar_divergencia(
            data_inicial=date(2025, 4, 1), data_final=date(2025, 4, 7), filial=[9999]
        )


# ══════════════════════════════════════════════════════════════════
# CLIENTES — GET restantes
# ══════════════════════════════════════════════════════════════════


@resp.activate
def test_listar_frota_retorna_veiculos(client):
    """GET frota deve retornar lista de veículos."""
    mock = [{"placa": "ABC-1234", "modelo": "GOL", "clienteCodigo": 10}]
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/CLIENTE_FROTA", json=mock, status=200)

    resultado = client.clientes.listar_frota()

    assert resultado[0]["placa"] == "ABC-1234"


@resp.activate
def test_listar_frota_filtro_cliente(client):
    """GET frota com clienteCodigo deve enviar filtro na URL."""
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/CLIENTE_FROTA", json=[], status=200)

    client.clientes.listar_frota(cliente_codigo=42)

    assert "clienteCodigo=42" in resp.calls[0].request.url


@resp.activate
def test_listar_grupos_retorna_lista(client):
    """GET grupos de clientes deve retornar lista."""
    mock = [{"codigo": 1, "nome": "Frota A"}, {"codigo": 2, "nome": "Frota B"}]
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/GRUPO_CLIENTE", json=mock, status=200)

    resultado = client.clientes.listar_grupos()

    assert len(resultado) == 2
    assert resultado[0]["nome"] == "Frota A"


@resp.activate
def test_listar_prazos_clientes(client):
    """GET lista clientes com prazo configurado."""
    mock = [{"clienteCodigo": 5, "prazo": 30}]
    resp.add(
        resp.GET,
        f"{BASE}/INTEGRACAO/INTEGRACAO_LISTA_CLIENTE_PRAZO",
        json=mock,
        status=200,
    )

    resultado = client.clientes.listar_prazos()

    assert resultado[0]["prazo"] == 30


@resp.activate
def test_retorno_cadastro_cliente(client):
    """GET retorno cadastro cliente deve retornar dados."""
    mock = {"clienteCodigo": 10, "status": "ATIVO"}
    resp.add(
        resp.GET, f"{BASE}/INTEGRACAO/RETORNO_CADASTRO_CLIENTE", json=mock, status=200
    )

    resultado = client.clientes.retorno_cadastro({})

    assert resultado["status"] == "ATIVO"


@resp.activate
def test_centro_custo_cliente_204(client):
    """POST centro de custo retorna 204."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/CENTRO_CUSTO_CLIENTE", status=204)

    resultado = client.clientes.centro_custo(
        {"clienteCodigo": 1, "centroCustoCodigo": 5}
    )

    assert resultado is None


@resp.activate
def test_centro_custo_envia_dados(client):
    """POST centro de custo envia clienteCodigo e centroCustoCodigo."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/CENTRO_CUSTO_CLIENTE", status=204)

    client.clientes.centro_custo({"clienteCodigo": 3, "centroCustoCodigo": 7})

    body = json.loads(resp.calls[0].request.body)
    assert body["clienteCodigo"] == 3
    assert body["centroCustoCodigo"] == 7


# ══════════════════════════════════════════════════════════════════
# COMBUSTÍVEL — GET/POST restantes
# ══════════════════════════════════════════════════════════════════


@resp.activate
def test_criar_pedido_combustivel_retorna_dados(client):
    """POST pedido combustível deve retornar id do pedido criado."""
    mock = {"pedidoId": 77, "status": "PENDENTE"}
    resp.add(
        resp.POST, f"{BASE}/INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO", json=mock, status=201
    )

    resultado = client.combustivel.criar_pedido(
        {"produtoCodigo": 1, "quantidade": 10000.0, "filialCodigo": 1}
    )

    assert resultado["pedidoId"] == 77


@resp.activate
def test_criar_pedido_combustivel_envia_quantidade(client):
    """POST pedido combustível envia quantidade corretamente."""
    resp.add(
        resp.POST,
        f"{BASE}/INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO",
        json={"pedidoId": 1},
        status=201,
    )

    client.combustivel.criar_pedido({"produtoCodigo": 2, "quantidade": 15000.5})

    body = json.loads(resp.calls[0].request.body)
    assert body["quantidade"] == 15000.5


@resp.activate
def test_listar_pedidos_combustivel(client):
    """GET pedidos de combustível retorna lista."""
    mock = [
        {"pedidoId": 1, "status": "FATURADO"},
        {"pedidoId": 2, "status": "PENDENTE"},
    ]
    resp.add(
        resp.GET, f"{BASE}/INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO", json=mock, status=200
    )

    resultado = client.combustivel.listar_pedidos()

    assert len(resultado) == 2


@resp.activate
def test_listar_pedidos_com_datas(client):
    """GET pedidos deve aceitar filtro de datas."""
    resp.add(
        resp.GET, f"{BASE}/INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO", json=[], status=200
    )

    client.combustivel.listar_pedidos(
        data_inicial=date(2025, 4, 1), data_final=date(2025, 4, 7)
    )

    url = resp.calls[0].request.url
    assert "dataInicial=2025-04-01" in url


@resp.activate
def test_receber_titulo_cartao_pedido_204(client):
    """PUT receber título em cartão retorna 204."""
    resp.add(
        resp.PUT,
        f"{BASE}/INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO/10/RECEBER_TITULO_EM_CARTAO",
        status=204,
    )

    resultado = client.combustivel.receber_titulo_cartao(
        10, {"administradoraCodigo": 3}
    )

    assert resultado is None


@resp.activate
def test_receber_titulo_cartao_id_na_url(client):
    """PUT receber cartão deve incluir ID do pedido na URL."""
    resp.add(
        resp.PUT,
        f"{BASE}/INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO/55/RECEBER_TITULO_EM_CARTAO",
        status=204,
    )

    client.combustivel.receber_titulo_cartao(55, {"administradoraCodigo": 1})

    assert (
        "/PEDIDO_COMBUSTIVEL/PEDIDO/55/RECEBER_TITULO_EM_CARTAO"
        in resp.calls[0].request.url
    )


@resp.activate
def test_vincular_cliente_pedido_204(client):
    """POST vincular cliente a pedido retorna 204."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/PEDIDO_COMBUSTIVEL/CLIENTE", status=204)

    resultado = client.combustivel.vincular_cliente_pedido(
        {"clienteCodigo": 10, "pedidoId": 5}
    )

    assert resultado is None


@resp.activate
def test_listar_aprix_custo_retorna_lista(client):
    """GET APRIX custo retorna lista."""
    mock = [{"produto": "GASOLINA", "custo": 4.50}]
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/APRIX_CUSTO", json=mock, status=200)

    resultado = client.combustivel.listar_aprix_custo()

    assert resultado[0]["custo"] == 4.50


@resp.activate
def test_listar_distribuidoras_retorna_lista(client):
    """GET distribuidoras retorna lista."""
    mock = [{"codigo": 1, "nome": "Petrobras"}, {"codigo": 2, "nome": "Ipiranga"}]
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/DISTRIBUIDORA", json=mock, status=200)

    resultado = client.combustivel.listar_distribuidoras()

    assert len(resultado) == 2
    assert resultado[0]["nome"] == "Petrobras"


# ══════════════════════════════════════════════════════════════════
# FINANCEIRO — GET restantes
# ══════════════════════════════════════════════════════════════════


@resp.activate
def test_listar_titulos_pagar_retorna_lista(client):
    """GET títulos a pagar retorna lista."""
    mock = [{"tituloCodigo": 20, "valor": 800.00, "situacao": "ABERTO"}]
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/TITULO_PAGAR", json=mock, status=200)

    resultado = client.financeiro.listar_titulos_pagar(
        data_inicial=date(2025, 1, 1), data_final=date(2025, 12, 31)
    )

    assert resultado[0]["tituloCodigo"] == 20


@resp.activate
def test_listar_titulos_pagar_filtro_situacao(client):
    """GET títulos a pagar aceita filtro situacaoPagar."""
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/TITULO_PAGAR", json=[], status=200)

    client.financeiro.listar_titulos_pagar(
        data_inicial=date(2025, 1, 1), data_final=date(2025, 12, 31), situacao="PAGO"
    )

    assert "situacaoPagar=PAGO" in resp.calls[0].request.url


@resp.activate
def test_listar_movimentos_conta(client):
    """GET movimentos de conta bancária retorna lista."""
    mock = [{"data": "2025-04-07", "valor": 5000.00, "tipo": "CREDITO"}]
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/MOVIMENTO_CONTA", json=mock, status=200)

    resultado = client.financeiro.listar_movimentos_conta(
        data_inicial=date(2025, 4, 1), data_final=date(2025, 4, 7)
    )

    assert resultado[0]["tipo"] == "CREDITO"


@resp.activate
def test_listar_fechamento_caixa(client):
    """GET fechamento de caixa retorna lista."""
    mock = [{"data": "2025-04-06", "totalVendas": 12500.00, "filialCodigo": 1}]
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/FECHAMENTO_CAIXA", json=mock, status=200)

    resultado = client.financeiro.listar_fechamento_caixa(
        data_inicial=date(2025, 4, 1), data_final=date(2025, 4, 7)
    )

    assert resultado[0]["totalVendas"] == 12500.00


@resp.activate
def test_listar_fechamento_caixa_chave_na_url(client):
    """GET fechamento deve incluir CHAVE na URL."""
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/FECHAMENTO_CAIXA", json=[], status=200)

    client.financeiro.listar_fechamento_caixa(
        data_inicial=date(2025, 4, 1), data_final=date(2025, 4, 7)
    )

    assert f"CHAVE={CHAVE}" in resp.calls[0].request.url


@resp.activate
def test_listar_transferencias_bancarias(client):
    """GET transferências bancárias retorna lista."""
    mock = [{"de": 1, "para": 2, "valor": 2000.00}]
    resp.add(
        resp.GET, f"{BASE}/INTEGRACAO/TRANSFERENCIA_BANCARIA", json=mock, status=200
    )

    resultado = client.financeiro.listar_transferencias(
        data_inicial=date(2025, 4, 1), data_final=date(2025, 4, 7)
    )

    assert resultado[0]["valor"] == 2000.00


@resp.activate
def test_plano_de_contas_retorna_lista(client):
    """GET plano de contas retorna lista de contas."""
    mock = [{"codigo": "1.1.1", "nome": "Caixa Geral"}]
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/PLANO_DE_CONTAS", json=mock, status=200)

    resultado = client.financeiro.plano_de_contas()

    assert resultado[0]["codigo"] == "1.1.1"


@resp.activate
def test_financeiro_exclusao_retorna_lista(client):
    """GET exclusões financeiras retorna lista."""
    mock = [{"data": "2025-04-07", "valor": 100.00, "tipo": "DEBITO"}]
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/FINANCEIRO_EXCLUSAO", json=mock, status=200)

    resultado = client.financeiro.financeiro_exclusao(
        data_inicial=date(2025, 4, 1), data_final=date(2025, 4, 7)
    )

    assert resultado[0]["tipo"] == "DEBITO"


# ══════════════════════════════════════════════════════════════════
# INTEGRAÇÕES — GET/POST restantes
# ══════════════════════════════════════════════════════════════════


@resp.activate
def test_listar_vendas_retorna_lista(client):
    """GET vendas retorna lista."""
    mock = [{"vendaId": 1, "total": 350.00}, {"vendaId": 2, "total": 180.50}]
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/VENDA", json=mock, status=200)

    resultado = client.integracoes.listar_vendas(
        data_inicial=date(2025, 4, 1), data_final=date(2025, 4, 7)
    )

    assert len(resultado) == 2
    assert resultado[0]["total"] == 350.00


@resp.activate
def test_listar_vendas_envia_datas(client):
    """GET vendas deve enviar dataInicial e dataFinal."""
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/VENDA", json=[], status=200)

    client.integracoes.listar_vendas(
        data_inicial=date(2025, 4, 1), data_final=date(2025, 4, 7)
    )

    url = resp.calls[0].request.url
    assert "dataInicial=2025-04-01" in url
    assert "dataFinal=2025-04-07" in url


@resp.activate
def test_listar_vendas_rede(client):
    """GET vendas em rede retorna lista."""
    mock = [{"vendaId": 10, "filial": 1}, {"vendaId": 11, "filial": 2}]
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/VENDA_REDE", json=mock, status=200)

    resultado = client.integracoes.listar_vendas_rede(
        data_inicial=date(2025, 4, 1), data_final=date(2025, 4, 7)
    )

    assert len(resultado) == 2


@resp.activate
def test_listar_nf_entrada_retorna_lista(client):
    """GET NF de entrada retorna lista de notas."""
    mock = [{"numeroNF": "001234", "valor": 45000.00}]
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/NOTA_FISCAL_ENTRADA", json=mock, status=200)

    resultado = client.integracoes.listar_nf_entrada(
        data_inicial=date(2025, 4, 1), data_final=date(2025, 4, 7)
    )

    assert resultado[0]["numeroNF"] == "001234"


@resp.activate
def test_listar_nf_entrada_com_distribuidora(client):
    """GET NF entrada aceita filtro de distribuidora."""
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/NOTA_FISCAL_ENTRADA", json=[], status=200)

    client.integracoes.listar_nf_entrada(
        data_inicial=date(2025, 4, 1),
        data_final=date(2025, 4, 7),
        distribuidora="PETROBRAS",
    )

    assert "distribuidora=PETROBRAS" in resp.calls[0].request.url


@resp.activate
def test_listar_nf_saida_retorna_lista(client):
    """GET NF de saída retorna lista."""
    mock = [{"numeroNF": "000555", "valor": 1200.00}]
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/NOTA_FISCAL_SAIDA", json=mock, status=200)

    resultado = client.integracoes.listar_nf_saida(
        data_inicial=date(2025, 4, 1), data_final=date(2025, 4, 7)
    )

    assert resultado[0]["valor"] == 1200.00


@resp.activate
def test_listar_pedidos_compra(client):
    """GET pedidos de compra retorna lista."""
    mock = [{"pedidoId": 3, "fornecedor": "ABC Distribuidora"}]
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/PEDIDO_COMPRAS", json=mock, status=200)

    resultado = client.integracoes.listar_pedidos_compra()

    assert resultado[0]["pedidoId"] == 3


@resp.activate
def test_criar_pedido_compra_retorna_dados(client):
    """POST pedido de compra retorna id e status."""
    mock = {"pedidoId": 99, "status": "PENDENTE"}
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/PEDIDO_COMPRAS", json=mock, status=201)

    resultado = client.integracoes.criar_pedido_compra(
        {"fornecedorCodigo": 10, "itens": [{"produtoCodigo": 1, "quantidade": 100}]}
    )

    assert resultado["pedidoId"] == 99


@resp.activate
def test_criar_pedido_compra_envia_itens(client):
    """POST pedido de compra envia lista de itens."""
    resp.add(
        resp.POST, f"{BASE}/INTEGRACAO/PEDIDO_COMPRAS", json={"pedidoId": 1}, status=201
    )

    client.integracoes.criar_pedido_compra(
        {"fornecedorCodigo": 5, "itens": [{"produtoCodigo": 2, "quantidade": 500}]}
    )

    body = json.loads(resp.calls[0].request.body)
    assert len(body["itens"]) == 1
    assert body["itens"][0]["quantidade"] == 500


@resp.activate
def test_listar_usuarios(client):
    """GET usuários retorna lista."""
    mock = [{"codigo": 1, "nome": "Admin"}, {"codigo": 2, "nome": "Operador"}]
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/USUARIO", json=mock, status=200)

    resultado = client.integracoes.listar_usuarios()

    assert len(resultado) == 2


@resp.activate
def test_listar_administradoras(client):
    """GET administradoras retorna lista."""
    mock = [{"codigo": 1, "nome": "CIELO"}, {"codigo": 2, "nome": "REDE"}]
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/ADMINISTRADORA", json=mock, status=200)

    resultado = client.integracoes.listar_administradoras()

    assert resultado[0]["nome"] == "CIELO"


@resp.activate
def test_listar_veiculos(client):
    """GET veículos retorna lista."""
    mock = [{"placa": "XYZ-0001", "modelo": "CAMINHAO"}]
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/VEICULO", json=mock, status=200)

    resultado = client.integracoes.listar_veiculos()

    assert resultado[0]["placa"] == "XYZ-0001"


@resp.activate
def test_listar_adiantamento_fornecedor(client):
    """GET adiantamento fornecedor retorna lista."""
    mock = [{"fornecedorCodigo": 5, "valor": 2000.00}]
    resp.add(
        resp.GET, f"{BASE}/INTEGRACAO/ADIANTAMENTO_FORNECEDOR", json=mock, status=200
    )

    resultado = client.integracoes.listar_adiantamento_fornecedor(
        data_inicial=date(2025, 4, 1), data_final=date(2025, 4, 7)
    )

    assert resultado[0]["valor"] == 2000.00


@resp.activate
def test_listar_prazo_tabela_preco(client):
    """GET prazo tabela de preços retorna lista."""
    mock = [{"codigo": 1, "descricao": "Tabela A", "prazo": 30}]
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/PRAZO_TABELA_PRECO", json=mock, status=200)

    resultado = client.integracoes.listar_prazo_tabela_preco()

    assert resultado[0]["prazo"] == 30


@resp.activate
def test_criar_item_prazo_tabela_preco_204(client):
    """POST item em tabela de preço retorna 204."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/PRAZO_TABELA_PRECO/5/ITEM", status=204)

    resultado = client.integracoes.criar_item_prazo_tabela_preco(
        5, {"produtoCodigo": 1, "preco": 5.89}
    )

    assert resultado is None


@resp.activate
def test_criar_item_prazo_id_correto_na_url(client):
    """POST item prazo usa ID da tabela na URL."""
    resp.add(resp.POST, f"{BASE}/INTEGRACAO/PRAZO_TABELA_PRECO/12/ITEM", status=204)

    client.integracoes.criar_item_prazo_tabela_preco(
        12, {"produtoCodigo": 3, "preco": 7.0}
    )

    assert "/PRAZO_TABELA_PRECO/12/ITEM" in resp.calls[0].request.url


@resp.activate
def test_autorizar_pagamento_abastecimento(client):
    """POST autorizar pagamento retorna dados de autorização."""
    mock = {"autorizacaoId": "AUTH-001", "status": "APROVADO"}
    resp.add(
        resp.POST,
        f"{BASE}/INTEGRACAO/AUTORIZA_PAGAMENTO_ABASTECIMENTO",
        json=mock,
        status=200,
    )

    resultado = client.integracoes.autorizar_pagamento_abastecimento(
        {"clienteCodigo": 10, "valor": 250.00}
    )

    assert resultado["status"] == "APROVADO"


@resp.activate
def test_persistir_cartao_retorna_dados(client):
    """POST persistir cartão retorna dados do cartão."""
    mock = {"cartaoId": "CARD-555", "bandeira": "VISA"}
    resp.add(
        resp.POST, f"{BASE}/INTEGRACAO/PERSISTIR_CARTAO_DTO", json=mock, status=200
    )

    resultado = client.integracoes.persistir_cartao(
        {"numero": "4111111111111111", "bandeira": "VISA"}
    )

    assert resultado["bandeira"] == "VISA"


# ══════════════════════════════════════════════════════════════════
# PRODUTOS — GET restantes
# ══════════════════════════════════════════════════════════════════


@resp.activate
def test_listar_itens_retorna_lista(client):
    """GET lista de itens retorna lista."""
    mock = [{"codigo": 1, "nome": "GASOLINA COMUM"}, {"codigo": 2, "nome": "DIESEL"}]
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/LISTA_DE_ITENS", json=mock, status=200)

    resultado = client.produtos.listar_itens()

    assert len(resultado) == 2


@resp.activate
def test_listar_itens_com_paginacao(client):
    """GET lista de itens aceita paginação."""
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/LISTA_DE_ITENS", json=[], status=200)

    client.produtos.listar_itens(pagina=1, tamanho_pagina=20)

    url = resp.calls[0].request.url
    assert "pagina=1" in url
    assert "tamanhoPagina=20" in url


@resp.activate
def test_listar_inventario_itens(client):
    """GET itens de inventário retorna lista."""
    mock = [{"produtoCodigo": 5, "quantidade": 300.0}]
    resp.add(
        resp.GET, f"{BASE}/INTEGRACAO/PRODUTO_INVENTARIO_ITENS", json=mock, status=200
    )

    resultado = client.produtos.listar_inventario_itens()

    assert resultado[0]["quantidade"] == 300.0


@resp.activate
def test_tributos_icms_retorna_lista(client):
    """GET tributos ICMS retorna lista de produtos com ICMS."""
    mock = [{"produtoCodigo": 1, "aliquota": 12.0, "uf": "PE"}]
    resp.add(
        resp.GET,
        f"{BASE}/INTEGRACAO/INTEGRACAO_PRODUTO_TRIBUTO_ICMS",
        json=mock,
        status=200,
    )

    resultado = client.produtos.tributos_icms()

    assert resultado[0]["aliquota"] == 12.0
    assert resultado[0]["uf"] == "PE"


@resp.activate
def test_tributos_icms_com_paginacao(client):
    """GET tributos ICMS aceita paginação."""
    resp.add(
        resp.GET,
        f"{BASE}/INTEGRACAO/INTEGRACAO_PRODUTO_TRIBUTO_ICMS",
        json=[],
        status=200,
    )

    client.produtos.tributos_icms(pagina=0, tamanho_pagina=50)

    assert "pagina=0" in resp.calls[0].request.url


@resp.activate
def test_tributos_pis_confins_retorna_lista(client):
    """GET tributos PIS/CONFINS retorna lista."""
    mock = [{"produtoCodigo": 1, "aliquotaPis": 0.65, "aliquotaCofins": 3.0}]
    resp.add(
        resp.GET,
        f"{BASE}/INTEGRACAO/INTEGRACAO_PRODUTO_TRIBUTO_PIS_CONFINS",
        json=mock,
        status=200,
    )

    resultado = client.produtos.tributos_pis_confins()

    assert resultado[0]["aliquotaPis"] == 0.65


@resp.activate
def test_tributos_pis_confins_500_server_error(client):
    """GET tributos PIS/CONFINS com erro do servidor lança ServerError."""
    resp.add(
        resp.GET,
        f"{BASE}/INTEGRACAO/INTEGRACAO_PRODUTO_TRIBUTO_PIS_CONFINS",
        json={"error": "Internal Error"},
        status=500,
    )

    with pytest.raises(ServerError):
        client.produtos.tributos_pis_confins()


# ══════════════════════════════════════════════════════════════════
# RELATÓRIOS — 100% cobertura
# ══════════════════════════════════════════════════════════════════


@resp.activate
def test_relatorio_vendas_produto(client):
    """GET relatório vendas por produto retorna lista."""
    mock = [{"produto": "GASOLINA", "totalVendido": 50000.0, "receita": 290000.00}]
    resp.add(
        resp.GET, f"{BASE}/INTEGRACAO/RELATORIO/VENDA_PRODUTO", json=mock, status=200
    )

    resultado = client.relatorios.vendas_produto(
        data_inicial=date(2025, 4, 1), data_final=date(2025, 4, 7)
    )

    assert resultado[0]["produto"] == "GASOLINA"
    assert resultado[0]["receita"] == 290000.00


@resp.activate
def test_relatorio_vendas_produto_filtro_filial(client):
    """GET relatório vendas aceita filtro de filial."""
    resp.add(
        resp.GET, f"{BASE}/INTEGRACAO/RELATORIO/VENDA_PRODUTO", json=[], status=200
    )

    client.relatorios.vendas_produto(
        data_inicial=date(2025, 4, 1), data_final=date(2025, 4, 7), filial=[1, 2]
    )

    assert "filial" in resp.calls[0].request.url


@resp.activate
def test_relatorio_vendas_combustivel(client):
    """GET relatório vendas combustível retorna lista."""
    mock = [{"produto": "DIESEL", "litros": 8000.0, "receita": 52000.00}]
    resp.add(
        resp.GET,
        f"{BASE}/INTEGRACAO/RELATORIO/VENDA_COMBUSTIVEL",
        json=mock,
        status=200,
    )

    resultado = client.relatorios.vendas_combustivel(
        data_inicial=date(2025, 4, 1), data_final=date(2025, 4, 7)
    )

    assert resultado[0]["litros"] == 8000.0


@resp.activate
def test_relatorio_vendas_combustivel_envia_datas(client):
    """GET relatório combustível envia datas corretamente."""
    resp.add(
        resp.GET, f"{BASE}/INTEGRACAO/RELATORIO/VENDA_COMBUSTIVEL", json=[], status=200
    )

    client.relatorios.vendas_combustivel(
        data_inicial=date(2025, 3, 1), data_final=date(2025, 3, 31)
    )

    url = resp.calls[0].request.url
    assert "dataInicial=2025-03-01" in url
    assert "dataFinal=2025-03-31" in url


@resp.activate
def test_relatorio_resumo_vendas(client):
    """GET resumo de vendas retorna objeto consolidado."""
    mock = {"totalVendas": 180000.00, "totalLitros": 30000.0, "ticketMedio": 85.00}
    resp.add(
        resp.GET, f"{BASE}/INTEGRACAO/RELATORIO/RESUMO_VENDAS", json=mock, status=200
    )

    resultado = client.relatorios.resumo_vendas(
        data_inicial=date(2025, 4, 1), data_final=date(2025, 4, 7)
    )

    assert resultado["totalVendas"] == 180000.00
    assert resultado["ticketMedio"] == 85.00


@resp.activate
def test_relatorio_resumo_vendas_401(client):
    """GET resumo com chave inválida lança AuthError."""
    resp.add(
        resp.GET,
        f"{BASE}/INTEGRACAO/RELATORIO/RESUMO_VENDAS",
        json={"error": "Unauthorized"},
        status=401,
    )

    with pytest.raises(AuthError):
        client.relatorios.resumo_vendas(
            data_inicial=date(2025, 4, 1), data_final=date(2025, 4, 7)
        )


@resp.activate
def test_relatorio_estoque(client):
    """GET estoque retorna lista de produtos com saldo."""
    mock = [
        {"produtoCodigo": 1, "nome": "GASOLINA", "saldo": 25000.0},
        {"produtoCodigo": 2, "nome": "DIESEL", "saldo": 18000.0},
    ]
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/RELATORIO/ESTOQUE", json=mock, status=200)

    resultado = client.relatorios.estoque()

    assert len(resultado) == 2
    assert resultado[0]["saldo"] == 25000.0


@resp.activate
def test_relatorio_estoque_filtro_produto(client):
    """GET estoque aceita filtro por produto."""
    resp.add(resp.GET, f"{BASE}/INTEGRACAO/RELATORIO/ESTOQUE", json=[], status=200)

    client.relatorios.estoque(produto=[1, 2])

    assert "produto" in resp.calls[0].request.url


@resp.activate
def test_relatorio_estoque_500_server_error(client):
    """GET estoque com erro do servidor lança ServerError."""
    resp.add(
        resp.GET,
        f"{BASE}/INTEGRACAO/RELATORIO/ESTOQUE",
        json={"error": "Database timeout"},
        status=500,
    )

    with pytest.raises(ServerError):
        client.relatorios.estoque()
