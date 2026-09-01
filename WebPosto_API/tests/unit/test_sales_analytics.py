import pytest
from src.services.sales_analytics_service import SalesAnalyticsService
from src.interfaces.http.schemas.executive_sales_schema import SalesHeatmap, HourlyVolume


@pytest.mark.asyncio
async def test_sales_analytics_generates_valid_summary(monkeypatch):
    service = SalesAnalyticsService()

    sample = [
        {
            "empresaCodigo": 5555,
            "quantidade": 40.0,
            "valorTotal": 240.0,
            "codigoProduto": "1257884",
            "dataHoraAbastecimento": "2026-07-05T08:15:00",
        },
        {
            "empresaCodigo": 5555,
            "quantidade": 30.0,
            "valorTotal": 180.0,
            "codigoProduto": "1260803",
            "dataHoraAbastecimento": "2026-07-06T18:20:00",
        },
        {
            "empresaCodigo": 11495,
            "quantidade": 50.0,
            "valorTotal": 300.0,
            "codigoProduto": "1257884",
            "dataHoraAbastecimento": "2026-07-05T09:00:00",
        },
    ]

    async def fake_fetch(_di, _df):
        return sample

    async def fake_items(_di, _df, _emp):
        return [
            {
                "empresaCodigo": 5555,
                "produtoCodigo": "999001",
                "produto": "Óleo Motor 1L",
                "valorTotal": 45.0,
                "vendaCodigo": "V1",
            },
            {
                "empresaCodigo": 5555,
                "produtoCodigo": "999002",
                "produto": "Cerveja Lata",
                "valorTotal": 8.0,
                "vendaCodigo": "V1",
            },
        ]

    monkeypatch.setattr(service, "_fetch_abastecimentos", fake_fetch)
    monkeypatch.setattr(service, "_fetch_venda_items", fake_items)

    summary = await service.analyze("2026-07-01", "2026-07-10", 5555)

    assert summary.heatmap is not None
    assert len(summary.heatmap.data) == 7
    assert len(summary.heatmap.data[0]) == 24
    assert summary.volume_medio_diario_litros > 0
    assert summary.composicao.empresa_codigo == 5555
    assert len(summary.composicao.combustiveis) > 0
    assert summary.composicao.faturamento_total_rs > 0
    assert len(summary.cesta_afinidade) > 0


@pytest.mark.asyncio
async def test_sales_filter_isolates_company(monkeypatch):
    service = SalesAnalyticsService()

    async def fake_fetch(_di, _df):
        return [
            {
                "empresaCodigo": 5555,
                "quantidade": 10.0,
                "valorTotal": 60.0,
                "codigoProduto": "1257884",
                "dataHoraAbastecimento": "2026-07-05T10:00:00",
            },
            {
                "empresaCodigo": 11495,
                "quantidade": 100.0,
                "valorTotal": 700.0,
                "codigoProduto": "1257884",
                "dataHoraAbastecimento": "2026-07-05T10:00:00",
            },
        ]

    async def fake_items(_di, _df, _emp):
        return []

    monkeypatch.setattr(service, "_fetch_abastecimentos", fake_fetch)
    monkeypatch.setattr(service, "_fetch_venda_items", fake_items)

    # Período de 10 dias inclusivos → média = total / 10
    casa = await service.analyze("2026-07-01", "2026-07-10", 5555)
    vip = await service.analyze("2026-07-01", "2026-07-10", 11495)

    assert casa.volume_medio_diario_litros == 1.0
    assert vip.volume_medio_diario_litros == 10.0
    assert casa.composicao.faturamento_total_rs != vip.composicao.faturamento_total_rs

    # D-1 (1 dia): média diária == total do dia
    casa_d1 = await service.analyze("2026-07-05", "2026-07-05", 5555)
    assert casa_d1.volume_medio_diario_litros == 10.0


def test_sales_heatmap_structure():
    service = SalesAnalyticsService()
    rows = [
        {
            "quantidade": 20.0,
            "valorTotal": 120.0,
            "dataHoraAbastecimento": "2026-07-06T08:00:00",  # Monday-ish week
        },
        {
            "quantidade": 5.0,
            "valorTotal": 30.0,
            "dataHoraAbastecimento": "2026-07-06T03:00:00",
        },
    ]
    heatmap = service._calculate_heatmap_from_real_data(rows)
    assert isinstance(heatmap, SalesHeatmap)
    assert len(heatmap.data[0]) == 24
    # Same day: hour 8 should have more volume than hour 3
    day = None
    for d, hours in heatmap.data.items():
        if any(h.litros > 0 for h in hours):
            day = d
            break
    assert day is not None
    by_hour = {h.hora: h.litros for h in heatmap.data[day]}
    assert by_hour[8] > by_hour[3]
