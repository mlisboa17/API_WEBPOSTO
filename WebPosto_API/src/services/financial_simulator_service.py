"""Serviço de Simulação Estratégica de Impacto Financeiro — Sprint 49."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Dict

from pydantic import BaseModel, ConfigDict, Field


class FuelPriceDelta(BaseModel):
    """Delta de preço por tipo de combustível."""
    gasolina_comum: float = 0.0
    gasolina_aditivada: float = 0.0
    etanol: float = 0.0
    diesel_s10: float = 0.0


class SimulationInput(BaseModel):
    """Parâmetros de entrada para simulação estratégica."""

    model_config = ConfigDict(frozen=True)

    # Inputs principais solicitados
    delta_preco_bomba_rs: float | FuelPriceDelta = 0.0
    variacao_volume_pct: float = 0.0
    taxa_antecipacao_mensal_pct: Optional[float] = None

    # Base atual para cálculo (opcional, se não enviado usa médias padrão do grupo)
    volume_base_litros: float = 100000.0
    preco_medio_base_rs: float = 5.80
    margem_bruta_base_rs: float = 0.60
    faturamento_diario_base_rs: float = 20000.0
    vacuo_financeiro_dias: float = 15.0
    cmv_base_rs: float = 5.20


class SimulationResult(BaseModel):
    """Resultado da projeção financeira."""

    model_config = ConfigDict(frozen=True)

    # Impacto no Faturamento
    faturamento_projetado_rs: float
    impacto_faturamento_rs: float

    # Impacto na Margem e EBITDA (Output Mandatário)
    ebitda_projetado_rs: float
    impacto_ebitda_rs: float
    
    # Margem Líquida Pós-Cartões (Output Mandatário)
    margem_liquida_pos_cartoes_projetada_rs: float
    variacao_margem_liquida_rs: float

    # Impacto no Vácuo e Capital de Giro (Output Mandatário)
    custo_antecipacao_projetado_rs: float
    necessidade_capital_projetada_rs: float
    impacto_capital_giro_rs: float

    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class FinancialSimulatorService:
    """Simula impactos estratégicos no EBITDA e Capital de Giro."""

    def simulate(self, input_data: SimulationInput) -> SimulationResult:
        # 1. Ajuste de Preço
        delta_p = 0.0
        if isinstance(input_data.delta_preco_bomba_rs, (float, int)):
            delta_p = float(input_data.delta_preco_bomba_rs)
        elif isinstance(input_data.delta_preco_bomba_rs, FuelPriceDelta):
            # Média ponderada simplificada para simulação global
            delta_p = (input_data.delta_preco_bomba_rs.gasolina_comum * 0.5 + 
                       input_data.delta_preco_bomba_rs.etanol * 0.3 +
                       input_data.delta_preco_bomba_rs.diesel_s10 * 0.2)

        # 2. Projeção de Volume
        fator_volume = 1 + (input_data.variacao_volume_pct / 100)
        novo_volume = input_data.volume_base_litros * fator_volume
        novo_preco = input_data.preco_medio_base_rs + delta_p
        
        faturamento_base = input_data.volume_base_litros * input_data.preco_medio_base_rs
        faturamento_projetado = novo_volume * novo_preco
        impacto_faturamento = faturamento_projetado - faturamento_base

        # 3. EBITDA (Margem Bruta)
        # CMV unitário fixo (conservador)
        nova_margem_unitaria = input_data.margem_bruta_base_rs + delta_p
        margem_bruta_base = input_data.volume_base_litros * input_data.margem_bruta_base_rs
        margem_bruta_projetada = novo_volume * nova_margem_unitaria
        impacto_ebitda = margem_bruta_projetada - margem_bruta_base

        # 4. Impacto Financeiro
        taxa_mensal = input_data.taxa_antecipacao_mensal_pct or 1.5
        taxa_diaria = taxa_mensal / 30 / 100
        
        # Necessidade de Capital de Giro (Faturamento Diário * Vácuo)
        novo_fat_diario = faturamento_projetado / 30
        cap_giro_base = input_data.faturamento_diario_base_rs * input_data.vacuo_financeiro_dias
        cap_giro_projetado = novo_fat_diario * input_data.vacuo_financeiro_dias
        impacto_cap_giro = cap_giro_projetado - cap_giro_base

        # Custo de Antecipação (80% cartões)
        percentual_cartao = 0.80
        custo_ant_projetado = (faturamento_projetado * percentual_cartao) * (taxa_diaria * input_data.vacuo_financeiro_dias)
        
        # Margem Líquida Pós-Cartões
        margem_liq_base = margem_bruta_base - ((faturamento_base * percentual_cartao) * (taxa_diaria * input_data.vacuo_financeiro_dias))
        margem_liq_projetada = margem_bruta_projetada - custo_ant_projetado
        variacao_margem_liq = margem_liq_projetada - margem_liq_base

        return SimulationResult(
            faturamento_projetado_rs=round(faturamento_projetado, 2),
            impacto_faturamento_rs=round(impacto_faturamento, 2),
            ebitda_projetado_rs=round(margem_bruta_projetada, 2),
            impacto_ebitda_rs=round(impacto_ebitda, 2),
            margem_liquida_pos_cartoes_projetada_rs=round(margem_liq_projetada, 2),
            variacao_margem_liquida_rs=round(variacao_margem_liq, 2),
            custo_antecipacao_projetado_rs=round(custo_ant_projetado, 2),
            necessidade_capital_projetada_rs=round(cap_giro_projetado, 2),
            impacto_capital_giro_rs=round(impacto_cap_giro, 2),
        )
