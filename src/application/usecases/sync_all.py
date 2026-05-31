"""
Use Case: Orquestrador de Sincronização Multi-Tenant

Responsabilidades:
1. Recuperar configs de todas as empresas
2. Para cada empresa: executar sincronização
3. Coletar eventos de divergência
4. Persistir resultados
5. Emitir eventos de conclusão
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
import logging
from decimal import Decimal

from src.domain.entities.empresa import (
    Empresa,
    SincronizacaoFactory,
    EmpresaID,
    RateiConfiguracao,
    CentroCusto,
    CentroCustoID,
    DomainEvent
)
from src.domain.services.validador_rateio import ValidadorRateio


logger = logging.getLogger(__name__)


class SincronizacaoResultado:
    """Resultado consolidado de uma sincronização."""
    
    def __init__(self):
        self.empresas_processadas: int = 0
        self.total_rateios_criados: int = 0
        self.total_divergencias: int = 0
        self.total_erros: int = 0
        self.timestamp_inicio: datetime = datetime.utcnow()
        self.timestamp_fim: Optional[datetime] = None
        self.resultados_por_empresa: Dict[str, Dict[str, Any]] = {}
        self.eventos_gerados: List[DomainEvent] = []
    
    def finalizar(self):
        """Marcar sincronização como finalizada."""
        self.timestamp_fim = datetime.utcnow()
    
    def tempo_execucao_segundos(self) -> float:
        """Calcular tempo de execução em segundos."""
        if not self.timestamp_fim:
            return (datetime.utcnow() - self.timestamp_inicio).total_seconds()
        return (self.timestamp_fim - self.timestamp_inicio).total_seconds()
    
    def para_dict(self) -> Dict[str, Any]:
        """Converter resultado para dicionário."""
        return {
            'empresas_processadas': self.empresas_processadas,
            'total_rateios_criados': self.total_rateios_criados,
            'total_divergencias': self.total_divergencias,
            'total_erros': self.total_erros,
            'tempo_execucao_segundos': self.tempo_execucao_segundos(),
            'timestamp_inicio': self.timestamp_inicio.isoformat(),
            'timestamp_fim': self.timestamp_fim.isoformat() if self.timestamp_fim else None,
            'resultados_por_empresa': self.resultados_por_empresa,
            'total_eventos': len(self.eventos_gerados),
            'sucesso': self.total_erros == 0
        }


class OrquestradorSincronizacaoMultiTenant:
    """
    Use Case: Orquestrar sincronização de múltiplas empresas.
    
    Encapsula a lógica de aplicação para sincronizar dados de centros
    de custo e lançamentos para todas as empresas em paralelo.
    """
    
    def __init__(self, 
                 empresa_repository: 'EmpresaRepository',
                 webposto_client_factory: 'WebPostoClientFactory',
                 event_store: Optional['EventStore'] = None):
        """
        Inicializar orquestrador.
        
        Args:
            empresa_repository: Repository para carregar empresas
            webposto_client_factory: Factory para criar clientes WebPosto
            event_store: Store para persistir eventos (opcional)
        """
        self.empresa_repo = empresa_repository
        self.client_factory = webposto_client_factory
        self.event_store = event_store
        self.logger = logger
    
    async def executar(self, 
                      filtro_empresas: Optional[List[str]] = None,
                      paralelo: bool = True) -> SincronizacaoResultado:
        """
        Sincronizar todas as empresas.
        
        Fluxo:
        1. Emitir SyncStartedEvent
        2. Para cada empresa:
           a. Carregar configuração
           b. Recuperar centros de custo (WebPosto)
           c. Recuperar lançamentos (WebPosto)
           d. Calcular rateios
           e. Validar com ValidadorRateio
           f. Persistir em repositório
        3. Coletar todos os eventos
        4. Emitir SyncCompletedEvent
        5. Retornar resultado consolidado
        
        Args:
            filtro_empresas: IDs específicas de empresas (None = todas)
            paralelo: Executar em paralelo (True) ou sequencial (False)
            
        Returns:
            SincronizacaoResultado com resultados consolidados
        """
        resultado = SincronizacaoResultado()
        
        try:
            self.logger.info("Iniciando sincronização multi-tenant")
            
            # 1. Carregar todas as empresas
            empresas = await self._carregar_empresas(filtro_empresas)
            self.logger.info(f"Carregadas {len(empresas)} empresas para sincronização")
            
            # 2. Processar em paralelo ou sequencial
            if paralelo:
                await self._sincronizar_paralelo(empresas, resultado)
            else:
                await self._sincronizar_sequencial(empresas, resultado)
            
            # 3. Finalizar resultado
            resultado.finalizar()
            
            self.logger.info(
                f"Sincronização concluída: {resultado.empresas_processadas} empresas, "
                f"{resultado.total_rateios_criados} rateios, "
                f"{resultado.total_divergencias} divergências"
            )
            
            # 4. Persistir eventos se houver store
            if self.event_store:
                await self._persistir_eventos(resultado)
            
            return resultado
            
        except Exception as e:
            self.logger.error(f"Erro na sincronização: {str(e)}", exc_info=True)
            resultado.total_erros += 1
            resultado.finalizar()
            return resultado
    
    async def _carregar_empresas(self, 
                                 filtro_ids: Optional[List[str]] = None) -> List[Empresa]:
        """
        Carregar empresas do repositório.
        
        Args:
            filtro_ids: IDs específicas (None = todas)
            
        Returns:
            Lista de empresas
        """
        try:
            if filtro_ids:
                empresas = [
                    await self.empresa_repo.obter_por_id(emp_id) 
                    for emp_id in filtro_ids
                ]
                empresas = [e for e in empresas if e is not None]
            else:
                empresas = await self.empresa_repo.obter_todas()
            
            return empresas
        except Exception as e:
            self.logger.error(f"Erro ao carregar empresas: {str(e)}")
            return []
    
    async def _sincronizar_paralelo(self, 
                                   empresas: List[Empresa],
                                   resultado: SincronizacaoResultado) -> None:
        """Sincronizar múltiplas empresas em paralelo."""
        tasks = [
            self._sincronizar_empresa(empresa, resultado)
            for empresa in empresas
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _sincronizar_sequencial(self,
                                     empresas: List[Empresa],
                                     resultado: SincronizacaoResultado) -> None:
        """Sincronizar múltiplas empresas sequencialmente."""
        for empresa in empresas:
            await self._sincronizar_empresa(empresa, resultado)
    
    async def _sincronizar_empresa(self,
                                  empresa: Empresa,
                                  resultado: SincronizacaoResultado) -> None:
        """
        Sincronizar uma empresa específica.
        
        Args:
            empresa: Empresa a sincronizar
            resultado: Objeto para acumular resultados
        """
        try:
            empresa_id = empresa.empresa_id.valor
            self.logger.info(f"Iniciando sincronização da empresa: {empresa_id}")
            
            # 1. Recuperar centros de custo do WebPosto
            ccs_webposto = await self._recuperar_centros_custo(empresa_id)
            self.logger.debug(f"Empresa {empresa_id}: {len(ccs_webposto)} CCs recuperados")
            
            # 2. Atualizar empresa com CCs
            for cc_data in ccs_webposto:
                cc = CentroCusto(
                    centro_custo_id=CentroCustoID(valor=cc_data['id']),
                    nome=cc_data['nome'],
                    percentual_padrao=Decimal(str(cc_data.get('percentual', 0))),
                    ativo=cc_data.get('ativo', True)
                )
                try:
                    empresa.adicionar_centro_custo(cc)
                except Exception as e:
                    self.logger.warning(
                        f"Empresa {empresa_id}: Não foi possível adicionar CC "
                        f"{cc_data['id']}: {str(e)}"
                    )
            
            # 3. Recuperar lançamentos do WebPosto
            lancamentos = await self._recuperar_lancamentos(empresa_id)
            self.logger.debug(
                f"Empresa {empresa_id}: {len(lancamentos)} lançamentos recuperados"
            )
            
            # 4. Sincronizar lançamentos
            resultado_sync = empresa.sincronizar(lancamentos)
            
            # 5. Validar rateios criados
            validador = SincronizacaoFactory.criar_validador(empresa)
            resultado_validacao = validador.validar_lote(empresa.rateios, empresa)
            
            # 6. Acumular resultados
            resultado.empresas_processadas += 1
            resultado.total_rateios_criados += resultado_sync['rateios_criados']
            resultado.total_divergencias += len(resultado_sync['divergencias_detectadas'])
            resultado.total_erros += resultado_sync.get('erros', 0)
            
            # 7. Armazenar resultado por empresa
            resultado.resultados_por_empresa[empresa_id] = {
                'rateios_criados': resultado_sync['rateios_criados'],
                'divergencias': resultado_sync['divergencias_detectadas'],
                'validacao': resultado_validacao,
                'sucesso': resultado_sync['sucesso']
            }
            
            # 8. Coletar eventos
            eventos = empresa.obter_eventos()
            resultado.eventos_gerados.extend(eventos)
            
            self.logger.info(
                f"Empresa {empresa_id}: Sincronização concluída com sucesso. "
                f"{resultado_sync['rateios_criados']} rateios criados"
            )
            
        except Exception as e:
            self.logger.error(
                f"Erro na sincronização da empresa {empresa.empresa_id.valor}: {str(e)}",
                exc_info=True
            )
            resultado.total_erros += 1
            resultado.empresas_processadas += 1
    
    async def _recuperar_centros_custo(self, empresa_id: str) -> List[Dict[str, Any]]:
        """
        Recuperar centros de custo do WebPosto.
        
        Args:
            empresa_id: ID da empresa
            
        Returns:
            Lista de centros de custo
        """
        try:
            client = self.client_factory.criar_cliente(empresa_id)
            ccs = await client.discover_centros_custo()
            return ccs
        except Exception as e:
            self.logger.warning(
                f"Erro ao recuperar CCs da empresa {empresa_id}: {str(e)}"
            )
            return []
    
    async def _recuperar_lancamentos(self, empresa_id: str) -> List[Dict[str, Any]]:
        """
        Recuperar lançamentos do WebPosto.
        
        Args:
            empresa_id: ID da empresa
            
        Returns:
            Lista de lançamentos
        """
        try:
            client = self.client_factory.criar_cliente(empresa_id)
            lancamentos = await client.obter_lancamentos()
            return lancamentos
        except Exception as e:
            self.logger.warning(
                f"Erro ao recuperar lançamentos da empresa {empresa_id}: {str(e)}"
            )
            return []
    
    async def _persistir_eventos(self, resultado: SincronizacaoResultado) -> None:
        """
        Persistir eventos gerados durante a sincronização.
        
        Args:
            resultado: Resultado com eventos para persistir
        """
        try:
            for evento in resultado.eventos_gerados:
                await self.event_store.persistir_evento(evento)
            self.logger.info(
                f"Persistidos {len(resultado.eventos_gerados)} eventos"
            )
        except Exception as e:
            self.logger.error(
                f"Erro ao persistir eventos: {str(e)}"
            )


# ===== INTERFACES PARA INJEÇÃO DE DEPENDÊNCIA =====

class EmpresaRepository:
    """Interface para repositório de empresas."""
    
    async def obter_por_id(self, empresa_id: str) -> Optional[Empresa]:
        """Obter empresa por ID."""
        raise NotImplementedError
    
    async def obter_todas(self) -> List[Empresa]:
        """Obter todas as empresas."""
        raise NotImplementedError
    
    async def persistir(self, empresa: Empresa) -> None:
        """Persistir empresa."""
        raise NotImplementedError


class WebPostoClientFactory:
    """Interface para factory de clientes WebPosto."""
    
    def criar_cliente(self, empresa_id: str):
        """Criar cliente WebPosto para empresa."""
        raise NotImplementedError


class EventStore:
    """Interface para persistência de eventos."""
    
    async def persistir_evento(self, evento: DomainEvent) -> None:
        """Persistir evento."""
        raise NotImplementedError
