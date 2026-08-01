import pytest
from src.services.sales_composition_service import SalesCompositionService, _abastecimento_id


@pytest.mark.asyncio
async def test_composition_counts_distinct_abastecimentos(monkeypatch):
    service = SalesCompositionService()

    async def fake_abast(_di, _df):
        return [
            {
                "abastecimentoCodigo": 1,
                "empresaCodigo": 5555,
                "quantidade": 20.0,
                "valorTotal": 120.0,
                "codigoProduto": "1257884",
                "vendaItemCodigo": 101,
            },
            {
                "abastecimentoCodigo": 1,  # mesmo abastecimento — não duplica
                "empresaCodigo": 5555,
                "quantidade": 20.0,
                "valorTotal": 120.0,
                "codigoProduto": "1257884",
                "vendaItemCodigo": 101,
            },
            {
                "abastecimentoCodigo": 2,
                "empresaCodigo": 5555,
                "quantidade": 30.0,
                "valorTotal": 180.0,
                "codigoProduto": "1260803",
                "vendaItemCodigo": 102,
            },
            {
                "abastecimentoCodigo": 99,
                "empresaCodigo": 11495,
                "quantidade": 100.0,
                "valorTotal": 700.0,
                "codigoProduto": "1257884",
            },
        ]

    async def fake_items(_di, _df, _emp):
        return [
            {
                "empresaCodigo": 5555,
                "produtoCodigo": "888",
                "produto": "Óleo 1L",
                "valorTotal": 40.0,
                "vendaCodigo": "101",
            },
            {
                "empresaCodigo": 5555,
                "produtoCodigo": "889",
                "produto": "Cerveja Lata",
                "valorTotal": 9.0,
                "vendaCodigo": "102",
            },
        ]

    monkeypatch.setattr(service, "_fetch_abastecimentos", fake_abast)
    monkeypatch.setattr(service, "_fetch_venda_items", fake_items)

    result = await service.build("2026-07-01", "2026-07-10", 5555)
    assert result.summary.quantidadeAbastecimentos == 2  # DISTINCT ids 1 e 2
    assert result.crossSellingFunnel.totalAbastecimentos == 2
    assert result.summary.faturamentoCombustivel == 300.0  # 120 + 180 (dup do id1 ignorado)
    assert result.fonteAbastecimentos == "INTEGRACAO/ABASTECIMENTO"
    assert result.empresaCodigo == 5555
    assert len(result.compositionBySector) == 3


def test_abastecimento_id_prefers_operational_code():
    assert _abastecimento_id({"abastecimentoCodigo": 55, "codigo": 9}) == "55"
    assert "NF" not in _abastecimento_id({"codigo": 7}).upper()


@pytest.mark.asyncio
async def test_composition_fallback_never_raises(monkeypatch):
    service = SalesCompositionService()

    async def boom(*_a, **_k):
        raise RuntimeError("webposto down")

    monkeypatch.setattr(service, "_fetch_abastecimentos", boom)
    out = await service.build("2026-07-01", "2026-07-10", 11495)
    assert out.fallback is True
    assert out.summary.quantidadeAbastecimentos == 0
