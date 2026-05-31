"""Integration Test: End-to-End DDD Flow"""

import pytest
from decimal import Decimal
from datetime import datetime

from src.domain.entities.empresa import (
    Empresa, CentroCusto, CentroCustoID, SincronizacaoFactory
)
from src.domain.services.validador_rateio import ValidadorRateio
from src.infrastructure.persistence.repositories import (
    SyncHistory, OutboxEvent, SyncStatusEnum
)


class TestEndToEndIntegration:
    """Testar fluxo completo: Domain → Application → Infrastructure."""
    
    def test_e2e_sync_flow_complete(self):
        """E2E: Criar empresa → Processar lancamentos → Registrar histórico."""
        
        # 1. DOMAIN LAYER: Criar agregado
        empresa = SincronizacaoFactory.criar_empresa(
            empresa_id="emp_integration_001",
            nome="Empresa Integração"
        )
        
        # 2. DOMAIN LAYER: Adicionar centros de custo
        for i in range(2):
            cc = CentroCusto(
                centro_custo_id=CentroCustoID(valor=f"cc_{i}"),
                nome=f"Centro {i}",
                percentual_padrao=Decimal("50.00")
            )
            empresa.adicionar_centro_custo(cc)
        
        # Validar invariantes
        empresa.validar_invariantes()
        assert len(empresa.centros_custo) == 2
        
        # 3. DOMAIN SERVICE: Criar validador
        validador = SincronizacaoFactory.criar_validador(empresa)
        assert isinstance(validador, ValidadorRateio)
        
        # 4. APPLICATION LAYER: Processar lançamentos
        lancamentos = [
            {
                "id": "lanc_001",
                "valor_total": 1000.00,
                "centros_custo": [
                    {"cc_id": "cc_0", "percentual": Decimal("50.00"), "valor": 500},
                    {"cc_id": "cc_1", "percentual": Decimal("50.00"), "valor": 500}
                ]
            },
            {
                "id": "lanc_002",
                "valor_total": 2000.00,
                "centros_custo": [
                    {"cc_id": "cc_0", "percentual": Decimal("50.00"), "valor": 1000},
                    {"cc_id": "cc_1", "percentual": Decimal("50.00"), "valor": 1000}
                ]
            }
        ]
        
        resultado = empresa.sincronizar(lancamentos)
        
        # Validar resultado da sincronização
        assert resultado['rateios_criados'] == 2
        assert resultado['divergencias_detectadas'] == []
        assert len(empresa.rateios) == 2
        
        # 5. PERSISTENCE LAYER: Registrar histórico
        sync_history = SyncHistory(
            empresa_id="emp_integration_001",
            timestamp_inicio=datetime.utcnow(),
            total_lancamentos_processados=2,
            total_rateios_criados=resultado['rateios_criados'],
            total_divergencias_detectadas=len(resultado['divergencias_detectadas'])
        )
        
        sync_history.marcar_concluida()
        
        # Validar histórico
        assert sync_history.status == SyncStatusEnum.COMPLETED
        assert sync_history.duracao_segundos is not None
        assert sync_history.total_rateios_criados == 2
        
        # 6. PERSISTENCE LAYER: Registrar eventos no Outbox
        outbox_events = [
            OutboxEvent(
                empresa_id="emp_integration_001",
                event_type="RateioCriadoEvent",
                event_data={
                    "empresa_id": "emp_integration_001",
                    "rateio_id": str(rateio.rateio_id.valor),
                    "lancamento_id": rateio.lancamento_id
                }
            )
            for rateio in empresa.rateios
        ]
        
        # Validar Outbox
        assert len(outbox_events) == 2
        assert all(not event.processado for event in outbox_events)
        
        # 7. VERIFICATION: Validar fluxo completo
        assert len(empresa.eventos_nao_commitados) > 0  # Domain events emitted
        # Validação passou (não lançou exceção)
        try:
            empresa.rateios[0].validar_soma()
            assert True
        except Exception:
            assert False, "Validação deveria ter passado"
        
        print("[OK] E2E Flow Complete:")
        print(f"   - Empresa: {empresa.empresa_id.valor}")
        print(f"   - Centros: {len(empresa.centros_custo)}")
        print(f"   - Rateios: {len(empresa.rateios)}")
        print(f"   - Eventos: {len(empresa.eventos_nao_commitados)}")
        print(f"   - Sincronização: {sync_history.status}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
