"""Testes do simulador financeiro — Sprint 49."""

from src.services.financial_simulator_service import (
    FinancialSimulatorService,
    SimulationInput,
    SimulationResult,
)


def test_simulate_price_increase_positive_impact():
    service = FinancialSimulatorService()
    
    input_data = SimulationInput(
        delta_preco_bomba_rs=0.10,
        volume_base_litros=100000.0,
        preco_medio_base_rs=5.00,
        margem_bruta_base_rs=0.50
    )
    
    result = service.simulate(input_data)
    
    # Preço base 5.00 * 100k = 500k fat
    # Novo preço 5.10 * 100k = 510k fat
    assert result.impacto_faturamento_rs == 10000.0
    
    # EBITDA (Margem): 0.50 * 100k = 50k -> 0.60 * 100k = 60k
    assert result.impacto_ebitda_rs == 10000.0


def test_simulate_volume_decrease_negative_impact():
    service = FinancialSimulatorService()
    
    input_data = SimulationInput(
        variacao_volume_pct=-10.0, # -10% de 100k = -10k litros
        volume_base_litros=100000.0,
        preco_medio_base_rs=5.00,
        margem_bruta_base_rs=0.50
    )
    
    result = service.simulate(input_data)
    
    # Faturamento: 100k * 5.0 = 500k -> 90k * 5.0 = 450k
    assert result.impacto_faturamento_rs == -50000.0
    
    # EBITDA: 100k * 0.5 = 50k -> 90k * 0.5 = 45k
    assert result.impacto_ebitda_rs == -5000.0


def test_simulate_capital_giro_impact():
    service = FinancialSimulatorService()
    
    input_data = SimulationInput(
        delta_preco_bomba_rs=0.20, # Sobe preço, sobe fat, sobe necessidade de capital se vácuo é igual
        volume_base_litros=100000.0,
        preco_medio_base_rs=5.00,
        faturamento_diario_base_rs=16666.67, # ~500k / 30
        vacuo_financeiro_dias=15.0
    )
    
    result = service.simulate(input_data)
    
    assert result.impacto_capital_giro_rs > 0
    # Custo antecipação é positivo (aumento de custo)
    assert result.custo_antecipacao_projetado_rs > 0


def test_simulate_combined_scenario():
    service = FinancialSimulatorService()
    
    # Cenário: Sobe preço 10 cents, mas volume cai 2%
    input_data = SimulationInput(
        delta_preco_bomba_rs=0.10,
        variacao_volume_pct=-2.0,
        volume_base_litros=100000.0,
        preco_medio_base_rs=5.50,
        margem_bruta_base_rs=0.60
    )
    
    result = service.simulate(input_data)
    
    # Fat Base: 100k * 5.5 = 550k
    # Fat Novo: 98k * 5.6 = 548.8k
    assert result.impacto_faturamento_rs == -1200.0
    
    # EBITDA Base: 100k * 0.6 = 60k
    # EBITDA Novo: 98k * 0.7 = 68.6k
    assert result.impacto_ebitda_rs == 8600.0 # Mesmo com menos volume, o preço maior compensou na margem
