"""Filtros de abastecimento para KPIs reais."""

from src.domain.adelaide.abastecimento_filters import (
    aplicar_filtros_abastecimento,
    valor_financeiro_abastecimento,
)


def test_exclui_afericao():
    rows = [
        {"codigoProduto": "1", "quantidade": 10, "afericao": True},
        {"codigoProduto": "1257884", "quantidade": 5, "valorTotal": 50},
    ]
    out = aplicar_filtros_abastecimento(rows, excluir_afericao=True)
    assert len(out) == 1
    assert out[0]["codigoProduto"] == "1257884"


def test_apenas_combustivel():
    rows = [
        {"codigoProduto": "1257884", "quantidade": 1},
        {"codigoProduto": "9999999", "quantidade": 1},
    ]
    out = aplicar_filtros_abastecimento(rows, apenas_combustivel=True)
    assert len(out) == 1


def test_valor_financeiro_quantidade_vezes_unitario():
    v = valor_financeiro_abastecimento({"quantidade": 10, "valorUnitario": 5.5})
    assert float(v) == 55.0


def test_filtro_codigos_lista_vazia_bloqueia_tudo():
    rows = [{"codigoProduto": "1257884", "quantidade": 1}]
    out = aplicar_filtros_abastecimento(rows, codigos_produto=[])
    assert len(out) == 0
