import pytest
from src.services.treasury_consolidation_service import TreasuryConsolidationService

@pytest.mark.asyncio
async def test_treasury_consolidation_sweep_suggestions():
    service = TreasuryConsolidationService()
    summary = await service.analyze()
    
    assert summary.saldo_consolidado_disponivel_rs == 45000 + 180000 + 12000
    assert len(summary.sugestoes_sweep) == 2
    assert summary.aging_disponibilidade_caixa_dias > 0
    
    # Verifica se a origem do sweep é a unidade superavitária (5555)
    for sweep in summary.sugestoes_sweep:
        assert sweep.origem_unit_id == 5555
        assert sweep.valor_sugerido_rs > 0

@pytest.mark.asyncio
async def test_unit_liquidity_needs():
    service = TreasuryConsolidationService()
    summary = await service.analyze()
    
    # VIP (11495) deve ter necessidade positiva (precisa de dinheiro)
    vip = next(u for u in summary.liquidez_por_unidade if u.unit_id == 11495)
    assert vip.necessidade_imediata_rs > 0
    
    # CASA CAIADA (5555) deve ter necessidade negativa (superavit)
    caiada = next(u for u in summary.liquidez_por_unidade if u.unit_id == 5555)
    assert caiada.necessidade_imediata_rs < 0
