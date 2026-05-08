"""
AuditoriaService - Serviço de Auditoria
Lógica de negócio para análise de despesas e fechamentos de caixa
"""

from typing import List, Optional
from datetime import datetime
from abc import ABC, abstractmethod

from src.domain.models.auditoria_models import (
    DespesaCaixa,
    FechamentoCaixa,
    ResumoAuditoriaUnidade,
    ListaFechamentos,
    StatusCaixa,
)
from src.infrastructure.repositories.auditoria_repository import AuditoriaRepository
from src.infrastructure.webposto.client import WebPostoClient
from src.shared.logger import logger

__all__ = ["AuditoriaService"]


class AuditoriaServiceBase(ABC):
    """Interface para serviço de auditoria"""

    @abstractmethod
    async def extrair_despesas_por_unidade(
        self, unidade_id: str, data: Optional[datetime] = None
    ) -> List[DespesaCaixa]:
        """Extrai despesas de uma unidade"""
        pass

    @abstractmethod
    async def extrair_fechamentos(
        self, unidade_id: str, data: Optional[datetime] = None
    ) -> List[FechamentoCaixa]:
        """Extrai fechamentos de uma unidade"""
        pass

    @abstractmethod
    def calcular_resumo_unidade(
        self, fechamentos: List[FechamentoCaixa], despesas: List[DespesaCaixa]
    ) -> ResumoAuditoriaUnidade:
        """Calcula resumo consolidado de auditoria"""
        pass

    @abstractmethod
    async def registrar_despesa(self, despesa: DespesaCaixa) -> DespesaCaixa:
        """Registra nova despesa"""
        pass


class AuditoriaService(AuditoriaServiceBase):
    """Serviço de auditoria com lógica de negócio"""

    def __init__(
        self,
        repository: AuditoriaRepository,
        webposto_client: WebPostoClient,
    ):
        """
        Inicializa o serviço de auditoria

        Args:
            repository: Repositório de auditoria para persistência
            webposto_client: Cliente webPosto para integração com API externa
        """
        self.repository = repository
        self.webposto_client = webposto_client
        self.logger = logger.getChild(__name__)

    async def extrair_despesas_por_unidade(
        self, unidade_id: str, data: Optional[datetime] = None
    ) -> List[DespesaCaixa]:
        """
        Extrai despesas estruturadas de uma unidade

        Args:
            unidade_id: ID da unidade (ex: 'real_01', 'casa_caiada_01')
            data: Data específica para filtro (opcional)

        Returns:
            Lista de despesas estruturadas

        Raises:
            Exception: Se houver erro na extração
        """
        try:
            self.logger.debug(f"Extraindo despesas para unidade {unidade_id}")

            # Tentar API webPosto primeiro
            try:
                despesas = await self.webposto_client.get_despesas(
                    unidade_id=unidade_id,
                    data_inicio=data.isoformat() if data else None,
                )
                self.logger.info(
                    f"Despesas extraídas da API webPosto: {len(despesas)} registros"
                )
                return despesas
            except Exception as e:
                self.logger.warning(
                    f"Erro ao acessar API webPosto: {e}. Tentando repositório..."
                )

            # Fallback para repositório local
            despesas = await self.repository.get_despesas_by_unidade(
                unidade_id=unidade_id,
                data=data,
            )
            self.logger.info(
                f"Despesas extraídas do repositório: {len(despesas)} registros"
            )
            return despesas

        except Exception as e:
            self.logger.error(f"Erro ao extrair despesas: {e}", exc_info=True)
            raise

    async def extrair_fechamentos(
        self, unidade_id: str, data: Optional[datetime] = None
    ) -> List[FechamentoCaixa]:
        """
        Extrai fechamentos estruturados de uma unidade

        Args:
            unidade_id: ID da unidade
            data: Data específica para filtro (opcional)

        Returns:
            Lista de fechamentos estruturados

        Raises:
            Exception: Se houver erro na extração
        """
        try:
            self.logger.debug(f"Extraindo fechamentos para unidade {unidade_id}")

            # Tentar API webPosto primeiro
            try:
                fechamentos = await self.webposto_client.get_fechamentos(
                    unidade_id=unidade_id,
                    data=data.isoformat() if data else None,
                )
                self.logger.info(
                    f"Fechamentos extraídos da API webPosto: {len(fechamentos)} registros"
                )
                return fechamentos
            except Exception as e:
                self.logger.warning(
                    f"Erro ao acessar API webPosto: {e}. Tentando repositório..."
                )

            # Fallback para repositório local
            fechamentos = await self.repository.get_fechamentos_by_unidade(
                unidade_id=unidade_id,
                data=data,
            )
            self.logger.info(
                f"Fechamentos extraídos do repositório: {len(fechamentos)} registros"
            )
            return fechamentos

        except Exception as e:
            self.logger.error(f"Erro ao extrair fechamentos: {e}", exc_info=True)
            raise

    def calcular_resumo_unidade(
        self, fechamentos: List[FechamentoCaixa], despesas: List[DespesaCaixa]
    ) -> ResumoAuditoriaUnidade:
        """
        Consolida análise de auditoria para uma unidade

        Business Logic:
        - Consolida KPIs de faturamento e despesas
        - Calcula quebra de caixa
        - Identifica outliers baseado em desvio de 5% de despesas
        - Agrega flags de auditoria

        Args:
            fechamentos: Lista de fechamentos da unidade
            despesas: Lista de despesas da unidade

        Returns:
            Resumo consolidado de auditoria
        """
        try:
            self.logger.debug("Calculando resumo de auditoria")

            if not fechamentos:
                unidade_id = "unknown"
            else:
                unidade_id = fechamentos[0].unidade_id

            # Consolidação de valores
            faturamento_total = sum(f.faturamento_bruto for f in fechamentos)
            despesas_operacionais = sum(f.despesas_caixa_total for f in fechamentos)
            quebra_total = sum(f.quebra_caixa for f in fechamentos)

            # Consolidação de status de caixas
            caixas_fechados = len(
                [f for f in fechamentos if f.status == StatusCaixa.FECHADO]
            )
            caixas_abertos = len(
                [f for f in fechamentos if f.status == StatusCaixa.ABERTO]
            )
            caixas_auditoria = len(
                [f for f in fechamentos if f.status == StatusCaixa.EM_AUDITORIA]
            )

            # Consolidação de issues de documentação
            despesas_sem_cat = sum(f.despesas_sem_categoria for f in fechamentos)
            despesas_sem_doc = sum(f.despesas_sem_documento for f in fechamentos)
            caixas_quebra_10 = len([f for f in fechamentos if f.quebra_caixa > 10])

            # Análise Estoica: Comparar despesas com padrão de 5%
            if faturamento_total > 0:
                desvio_percentual = (
                    despesas_operacionais / faturamento_total - 0.05
                ) * 100
                quebra_percentual = (quebra_total / faturamento_total) * 100
            else:
                desvio_percentual = 0
                quebra_percentual = 0

            # Outlier se desvio > 10%
            outlier = abs(desvio_percentual) > 10

            resumo = ResumoAuditoriaUnidade(
                unidade_id=unidade_id,
                data=datetime.now(),
                faturamento_total=round(faturamento_total, 2),
                despesas_operacionais=round(despesas_operacionais, 2),
                saldo_especie_total=round(
                    sum(f.saldo_informado_dinheiro for f in fechamentos), 2
                ),
                quebra_total=round(quebra_total, 2),
                quebra_percentual=round(quebra_percentual, 2),
                caixas_fechados=caixas_fechados,
                caixas_abertos=caixas_abertos,
                caixas_em_auditoria=caixas_auditoria,
                despesas_sem_categoria_total=despesas_sem_cat,
                despesas_sem_documento_total=despesas_sem_doc,
                caixas_com_quebra_acima_10=caixas_quebra_10,
                desvio_percentual_media_despesas=round(desvio_percentual, 2),
                outlier_unidade=outlier,
            )

            self.logger.info(
                f"Resumo calculado para {unidade_id}: "
                f"R$ {faturamento_total} faturado, "
                f"{desvio_percentual:.2f}% desvio de despesas"
            )

            return resumo

        except Exception as e:
            self.logger.error(f"Erro ao calcular resumo: {e}", exc_info=True)
            raise

    async def registrar_despesa(self, despesa: DespesaCaixa) -> DespesaCaixa:
        """
        Registra nova despesa no sistema

        Args:
            despesa: Despesa a ser registrada

        Returns:
            Despesa registrada com ID

        Raises:
            Exception: Se houver erro na persistência
        """
        try:
            self.logger.debug(f"Registrando despesa: {despesa.id}")

            # Validações de negócio
            if not despesa.tem_documento and despesa.status_justificativa == "pendente":
                self.logger.warning(
                    f"Despesa {despesa.id} sem documento e sem justificativa"
                )

            # Persistir no repositório
            despesa_registrada = await self.repository.save_despesa(despesa)

            self.logger.info(f"Despesa registrada com sucesso: {despesa.id}")
            return despesa_registrada

        except Exception as e:
            self.logger.error(
                f"Erro ao registrar despesa {despesa.id}: {e}", exc_info=True
            )
            raise

    async def get_fechamentos_com_resumo(
        self, unidade_id: str, data: Optional[datetime] = None
    ) -> ListaFechamentos:
        """
        Retorna fechamentos com resumo consolidado

        Args:
            unidade_id: ID da unidade
            data: Data para filtro (opcional)

        Returns:
            Lista de fechamentos com resumo

        Raises:
            Exception: Se houver erro na extração
        """
        try:
            fechamentos = await self.extrair_fechamentos(unidade_id, data)
            despesas = await self.extrair_despesas_por_unidade(unidade_id, data)
            resumo = self.calcular_resumo_unidade(fechamentos, despesas)

            return ListaFechamentos(
                unidade_id=unidade_id,
                data=datetime.now(),
                fechamentos=fechamentos,
                total_caixas=len(fechamentos),
                resumo=resumo,
            )
        except Exception as e:
            self.logger.error(
                f"Erro ao obter fechamentos com resumo: {e}", exc_info=True
            )
            raise
