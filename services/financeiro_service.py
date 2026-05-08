"""FinanceiroService — auditoria de caixas via cliente WebPosto unificado."""

from datetime import date, datetime
from typing import List, Optional

import logging

from models import FechamentoCaixaResponse, InsightAuditor, MovimentacaoEspecie
from webposto_client import WebPostoClient, webposto_client

logger = logging.getLogger(__name__)


class FinanceiroService:
    """
    Operações financeiras assíncronas.
    Usa o singleton `webposto_client` por padrão; ao usar `async with` sem cliente
    injetado, abre/fecha o pool apenas para scripts isolados (não use assim dentro
    do processo do FastAPI enquanto o lifespan mantém o mesmo cliente aberto).
    """

    def __init__(self, client: Optional[WebPostoClient] = None) -> None:
        self._c = client or webposto_client
        self._close_on_exit = client is None

    async def __aenter__(self) -> "FinanceiroService":
        await self._c.open()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._close_on_exit:
            await self._c.close()

    async def get_fechamento_caixa(
        self,
        unidade_id: int,
        data: Optional[date] = None,
    ) -> FechamentoCaixaResponse:
        if not data:
            data = datetime.now().date()
        response = await self._c.get_fechamento_caixa(unidade_id, data)
        logger.info("Fechamento obtido: %s - %s", response.unidade, response.data)
        return response

    async def get_despesas_caixa(
        self,
        unidade_id: int,
        data: Optional[date] = None,
    ) -> List[dict]:
        if not data:
            data = datetime.now().date()
        return await self._c.get_despesas_caixa_raw(unidade_id, data)

    async def get_movimentacao_especie(
        self,
        unidade_id: int,
        data: Optional[date] = None,
    ) -> List[MovimentacaoEspecie]:
        if not data:
            data = datetime.now().date()
        response = await self._c.get_movimentacao_especie(unidade_id, data)
        return response

    async def gerar_insights_auditoria(
        self,
        unidade_id: int,
        data: Optional[date] = None,
        unidades_comparacao: Optional[List[int]] = None,
    ) -> List[InsightAuditor]:
        if not data:
            data = datetime.now().date()

        if unidades_comparacao:
            logger.debug(
                "Comparativo multi-unidade ainda não implementado; ignorando unidades_comparacao=%s",
                unidades_comparacao,
            )

        fechamento = await self.get_fechamento_caixa(unidade_id, data)
        movimentacao = await self.get_movimentacao_especie(unidade_id, data)
        despesas = await self.get_despesas_caixa(unidade_id, data)

        insights: List[InsightAuditor] = []

        if fechamento.quebra_total > 10.0:
            insights.append(
                InsightAuditor(
                    tipo="anomalia_padrão",
                    severidade="crítico" if fechamento.quebra_total > 50 else "warning",
                    mensagem=f"Quebra total de R$ {fechamento.quebra_total:.2f} (esperado < R$ 10)",
                    metrica="quebra_caixa",
                    desvio_percentual=(
                        round(
                            (
                                fechamento.quebra_total
                                / fechamento.faturamento_total
                                * 100
                            ),
                            2,
                        )
                        if fechamento.faturamento_total > 0
                        else None
                    ),
                )
            )

        despesas_sem_cat = [d for d in despesas if not d.get("categoria")]
        if despesas_sem_cat:
            insights.append(
                InsightAuditor(
                    tipo="tipo_alerta",
                    severidade="warning",
                    mensagem=f"{len(despesas_sem_cat)} despesa(s) sem categoria definida",
                    metrica="despesas_incompletas",
                )
            )

        desvio_alto = [m for m in movimentacao if abs(m.percentual_desvio) > 5.0]
        for mov in desvio_alto:
            insights.append(
                InsightAuditor(
                    tipo="anomalia_padrão",
                    severidade="warning",
                    mensagem=f"Desvio em {mov.modalidade}: {mov.percentual_desvio:.1f}%",
                    metrica=f"especie_{mov.modalidade.lower()}",
                    desvio_percentual=mov.percentual_desvio,
                )
            )

        taxa_despesas = (
            (fechamento.despesas_total / fechamento.faturamento_total * 100)
            if fechamento.faturamento_total > 0
            else 0
        )
        if taxa_despesas > 10.0:
            insights.append(
                InsightAuditor(
                    tipo="anomalia_padrão",
                    severidade="info",
                    mensagem=f"Taxa de despesas em {taxa_despesas:.1f}% (padrão: ~5%)",
                    metrica="taxa_despesas",
                    desvio_percentual=taxa_despesas - 5.0,
                )
            )

        ordem_severidade = {"crítico": 0, "warning": 1, "info": 2}
        insights.sort(key=lambda x: ordem_severidade.get(x.severidade, 999))

        logger.info("Gerados %s insights para auditoria", len(insights))
        return insights
