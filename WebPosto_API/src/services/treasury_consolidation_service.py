from __future__ import annotations
import logging
from typing import List, Dict, Any, Optional

from src.interfaces.http.schemas.executive_treasury_schema import (
    TreasurySummary, UnitLiquidity, SweepSuggestion
)

logger = logging.getLogger(__name__)

class TreasuryConsolidationService:
    """
    Serviço de consolidação de tesouraria e otimização de fluxo de caixa intragrupo.
    """

    async def analyze(
        self, 
        empresa_codigo: Optional[int] = None
    ) -> TreasurySummary:
        """
        Consolida saldos bancários vs necessidades e sugere transferências (sweeps).
        """
        # Dados simulados baseados no cenário de 3 unidades do grupo
        liquidez = [
            UnitLiquidity(
                unit_id=11495,
                unit_name="POSTO VIP",
                saldo_bancario_rs=45000.00,
                contas_a_pagar_48h_rs=120000.00,
                necessidade_imediata_rs=75000.00
            ),
            UnitLiquidity(
                unit_id=5555,
                unit_name="CASA CAIADA",
                saldo_bancario_rs=180000.00,
                contas_a_pagar_48h_rs=35000.00,
                necessidade_imediata_rs=-145000.00 # Superavit
            ),
            UnitLiquidity(
                unit_id=74014,
                unit_name="POSTO DOZE FILIAL II",
                saldo_bancario_rs=12000.00,
                contas_a_pagar_48h_rs=45000.00,
                necessidade_imediata_rs=33000.00
            )
        ]

        saldo_consolidado = sum(u.saldo_bancario_rs for u in liquidez)
        exposicao_especial = 0.0 # Caso houvesse saldos negativos reais

        # Sugestões de Sweep: Mover dinheiro da 5555 (Superavit) para 11495 e 74014
        sugestoes = [
            SweepSuggestion(
                origem_unit_id=5555,
                origem_name="CASA CAIADA",
                destino_unit_id=11495,
                destino_name="POSTO VIP",
                valor_sugerido_rs=75000.00,
                justificativa="Cobrir CP de combustíveis vencendo em 24h e evitar cheque especial."
            ),
            SweepSuggestion(
                origem_unit_id=5555,
                origem_name="CASA CAIADA",
                destino_unit_id=74014,
                destino_name="POSTO DOZE FILIAL II",
                valor_sugerido_rs=33000.00,
                justificativa="Equilibrar fluxo de caixa operacional para virada de turno."
            )
        ]

        # Aging de Disponibilidade: Quantos dias o grupo sobrevive com o saldo atual?
        # Hipo: Gasto diário fixo do grupo (OPEX) é R$ 15.000,00
        aging_dias = saldo_consolidado / 15000.0 if saldo_consolidado > 0 else 0

        return TreasurySummary(
            saldo_consolidado_disponivel_rs=saldo_consolidado,
            exposicao_cheque_especial_total_rs=exposicao_especial,
            aging_disponibilidade_caixa_dias=round(aging_dias, 1),
            liquidez_por_unidade=liquidez,
            sugestoes_sweep=sugestoes
        )
