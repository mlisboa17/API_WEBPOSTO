"""Testes de conciliação de perdas volumétricas de combustíveis — Sprint 46/47."""

from src.services.fuel_loss_service import (
    FuelLossService,
    TankReconciliation,
    FuelLossSummary,
    LossClassification,
    ThermalAnalysis,
    FUEL_EXPANSION_COEFFICIENTS,
)


def test_reconcile_tank_within_tolerance():
    service = FuelLossService(tolerance_pct=0.6)

    result = service.reconcile_tank(
        tanque_codigo=1,
        empresa_codigo=11495,
        estoque_inicial=10000.0,
        entradas_nf=5000.0,
        saidas_vendas=8000.0,
        estoque_medido=6990.0,
        combustivel_tipo="Gasolina Comum",
        preco_medio=5.89,
    )

    assert isinstance(result, TankReconciliation)
    assert result.estoque_esperado == 7000.0
    assert result.variacao_litros == -10.0
    assert result.classificacao == LossClassification.NORMAL
    assert result.within_tolerance is True
    assert result.alert_level == "OK"


def test_reconcile_tank_loss_exceeds_tolerance():
    service = FuelLossService(tolerance_pct=0.6)

    result = service.reconcile_tank(
        tanque_codigo=2,
        empresa_codigo=11495,
        estoque_inicial=10000.0,
        entradas_nf=5000.0,
        saidas_vendas=8000.0,
        estoque_medido=6900.0,
        combustivel_tipo="Diesel S10",
        preco_medio=6.29,
    )

    assert result.estoque_esperado == 7000.0
    assert result.variacao_litros == -100.0
    assert result.within_tolerance is False
    assert result.alert_level == "WARNING"
    assert result.is_loss is True


def test_reconcile_tank_critical_loss():
    service = FuelLossService(tolerance_pct=0.6)

    result = service.reconcile_tank(
        tanque_codigo=3,
        empresa_codigo=11495,
        estoque_inicial=10000.0,
        entradas_nf=5000.0,
        saidas_vendas=8000.0,
        estoque_medido=6000.0,
        combustivel_tipo="Etanol",
        preco_medio=4.19,
    )

    assert result.variacao_litros == -1000.0
    assert result.classificacao in {LossClassification.CRITICO, LossClassification.VAZAMENTO, LossClassification.DESVIO_SUSPEITO}
    assert result.alert_level == "CRITICAL"
    assert result.variacao_reais == -4190.0


def test_reconcile_tank_surplus_suspicious():
    service = FuelLossService(tolerance_pct=0.6)

    result = service.reconcile_tank(
        tanque_codigo=4,
        empresa_codigo=11495,
        estoque_inicial=10000.0,
        entradas_nf=5000.0,
        saidas_vendas=8000.0,
        estoque_medido=7080.0,
    )

    assert result.variacao_litros == 80.0
    assert result.is_surplus is True
    assert result.classificacao == LossClassification.SOBRA_SUSPEITA
    assert result.alert_level == "WARNING"


def test_reconcile_batch_aggregates_correctly():
    service = FuelLossService()

    tank_data = [
        {
            "tanqueCodigo": 1,
            "empresaCodigo": 11495,
            "estoqueInicial": 10000.0,
            "entradasNf": 5000.0,
            "saidasVendas": 8000.0,
            "estoqueMedido": 6990.0,
            "precoMedio": 5.89,
        },
        {
            "tanqueCodigo": 2,
            "empresaCodigo": 11495,
            "estoqueInicial": 8000.0,
            "entradasNf": 4000.0,
            "saidasVendas": 6000.0,
            "estoqueMedido": 5500.0,
            "precoMedio": 6.29,
        },
    ]

    summary = service.reconcile_batch(tank_data, "2026-07-01", "2026-07-25")

    assert isinstance(summary, FuelLossSummary)
    assert summary.total_tanques_analisados == 2
    assert summary.tanques_com_perda == 2
    assert summary.perda_total_litros > 0
    assert len(summary.reconciliations) == 2


def test_reconcile_batch_identifies_critical_tanks():
    service = FuelLossService()

    tank_data = [
        {
            "tanqueCodigo": 1,
            "empresaCodigo": 11495,
            "estoqueInicial": 10000.0,
            "entradasNf": 5000.0,
            "saidasVendas": 8000.0,
            "estoqueMedido": 5500.0,
        },
    ]

    summary = service.reconcile_batch(tank_data, "2026-07-01", "2026-07-25")

    assert summary.tanques_criticos == 1
    assert summary.overall_status == "CRITICAL"
    assert len(summary.critical_alerts) == 1
    assert summary.critical_alerts[0]["tipo"] == "PERDA_CRITICA"


def test_extract_from_lmc_data():
    service = FuelLossService()

    lmc_records = [
        {
            "empresaCodigo": 11495,
            "empresaNome": "Posto VIP",
            "lmcTanque": [
                {
                    "tanqueCodigo": 1,
                    "produtoDescricao": "Gasolina Comum",
                    "estoqueInicial": 10000.0,
                    "entradaLitros": 5000.0,
                    "saidaLitros": 8000.0,
                    "estoqueFinal": 6995.0,
                    "precoCusto": 5.89,
                },
            ],
        },
    ]

    summary = service.extract_from_lmc_data(lmc_records, "2026-07-01", "2026-07-25")

    assert summary.total_tanques_analisados == 1
    assert len(summary.reconciliations) == 1
    assert summary.reconciliations[0].combustivel_tipo == "Gasolina Comum"


def test_calculate_thermal_variance():
    service = FuelLossService()

    result = service.calculate_thermal_variance(
        volume_litros=10000.0,
        temp_inicial=20.0,
        temp_final=35.0,
    )

    assert result["delta_temperatura"] == 15.0
    assert result["variacao_termica_litros"] == 142.5
    assert result["volume_corrigido"] == 10142.5


def test_thermal_correction_with_temperature_data():
    service = FuelLossService()

    result = service.reconcile_tank(
        tanque_codigo=10,
        empresa_codigo=11495,
        estoque_inicial=10000.0,
        entradas_nf=5000.0,
        saidas_vendas=8000.0,
        estoque_medido=6990.0,
        combustivel_tipo="Diesel S10",
        temp_inicial=25.0,
        temp_final=30.0,
    )

    assert result.thermal_analysis is not None
    assert result.thermal_analysis.has_thermal_data is True
    assert result.thermal_analysis.delta_temp == 5.0
    assert result.variacao_real_litros is not None


def test_thermal_correction_classifies_perda_termica():
    service = FuelLossService(tolerance_pct=0.6)

    result = service.reconcile_tank(
        tanque_codigo=11,
        empresa_codigo=11495,
        estoque_inicial=10000.0,
        entradas_nf=0.0,
        saidas_vendas=0.0,
        estoque_medido=9952.5,
        combustivel_tipo="Diesel",
        temp_inicial=30.0,
        temp_final=25.0,
    )

    assert result.thermal_analysis is not None
    assert result.thermal_analysis.variacao_termica_esperada < 0
    assert result.classificacao == LossClassification.PERDA_TERMICA


def test_thermal_correction_detects_vazamento():
    service = FuelLossService(tolerance_pct=0.6)

    result = service.reconcile_tank(
        tanque_codigo=12,
        empresa_codigo=11495,
        estoque_inicial=10000.0,
        entradas_nf=0.0,
        saidas_vendas=0.0,
        estoque_medido=9500.0,
        combustivel_tipo="Gasolina",
        temp_inicial=20.0,
        temp_final=20.0,
    )

    assert result.classificacao in {LossClassification.VAZAMENTO, LossClassification.DESVIO_SUSPEITO, LossClassification.CRITICO}
    assert result.alert_level == "CRITICAL"


def test_convert_to_anp_reference():
    service = FuelLossService()

    result = service.convert_to_anp_reference(
        volume_litros=10000.0,
        temperatura_atual=30.0,
        combustivel_tipo="Diesel",
    )

    assert result["temperatura_ambiente"] == 30.0
    assert result["volume_20c"] < result["volume_ambiente"]
    assert result["fator_conversao"] < 1.0


def test_expansion_coefficients_by_fuel_type():
    service = FuelLossService()

    assert service._get_expansion_coefficient("Gasolina Comum") == 0.00120
    assert service._get_expansion_coefficient("Diesel S10") == 0.00095
    assert service._get_expansion_coefficient("Etanol") == 0.00110
    assert service._get_expansion_coefficient("Desconhecido") == 0.00095
