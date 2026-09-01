from src.services.logistics_freight_service import compute_freight_from_notes


def test_compute_freight_rs_per_liter_from_nf():
    notas = [
        {
            "empresaCodigo": 5555,
            "compraCodigo": 1,
            "valorFrete": 300.0,
            "fornecedorCodigo": 128841,
            "tipoFrete": "Contratação do Frete por conta do Destinatário",
        },
        {
            "empresaCodigo": 5555,
            "compraCodigo": 2,
            "valorFrete": 0.0,
            "fornecedorCodigo": 128841,
        },
    ]
    itens = [
        {
            "empresaCodigo": 5555,
            "compraCodigo": 1,
            "quantidade": 10000.0,
            "unidadeCompra": "LT",
        },
        {
            "empresaCodigo": 5555,
            "compraCodigo": 2,
            "quantidade": 5000.0,
            "unidadeCompra": "LT",
        },
    ]
    frete_total, frete_medio, _oportunidade, eficiencia = compute_freight_from_notes(
        notas, itens, {128841: "VIBRA ENERGIA S.A"}
    )
    assert frete_total == 300.0
    assert frete_medio == 0.03
    assert len(eficiencia) == 1
    assert eficiencia[0].fornecedor == "VIBRA ENERGIA S.A"
    assert eficiencia[0].total_litros_comprados == 10000.0
    assert eficiencia[0].custo_frete_medio_rs_litro == 0.03


def test_compute_freight_ignores_notes_without_volume():
    notas = [{"empresaCodigo": 1, "compraCodigo": 9, "valorFrete": 100.0, "fornecedorCodigo": 1}]
    frete_total, frete_medio, _, eficiencia = compute_freight_from_notes(notas, [], {})
    assert frete_total == 0.0
    assert frete_medio == 0.0
    assert eficiencia == []
