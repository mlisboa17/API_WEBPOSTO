"""Serviço de Alertas Proativos de Exceção — Sprint 50."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, List, Optional

from src.models.alert_model import ExecutiveAlertModel, AlertSeverity, AlertCategory
from src.infrastructure.repositories.executive_alert_repository import ExecutiveAlertRepository
from src.services.notification_dispatcher_service import NotificationDispatcherService

logger = logging.getLogger(__name__)


class ProactiveAlertService:
    """Motor de avaliação proativa de métricas e geração de alertas persistentes."""

    VACUUM_LIMIT_DAYS = 15.0
    CASH_BREAK_CRITICAL_RS = 100.0

    def __init__(
        self, 
        repository: Optional[ExecutiveAlertRepository] = None,
        dispatcher: Optional[NotificationDispatcherService] = None
    ) -> None:
        self.repository = repository
        self.dispatcher = dispatcher or NotificationDispatcherService()

    async def _save_and_notify(self, alert_data: ExecutiveAlertModel) -> Optional[ExecutiveAlertModel]:
        """Salva o alerta no banco (idempotente) e dispara notificação se necessário."""
        if not self.repository:
            logger.warning("Repository não configurado. Alerta não persistido.")
            return alert_data

        # Idempotência: Verifica se já existe um alerta com este ID externo
        existing = await self.repository.get_by_external_id(alert_data.alert_external_id)
        if existing:
            return existing

        # Salva no banco
        saved_alert = await self.repository.create(alert_data)
        
        # Despacha notificação para alertas críticos
        if saved_alert.severity == AlertSeverity.CRITICAL and self.dispatcher:
            await self.dispatcher.dispatch_alert(saved_alert)
            
        return saved_alert

    async def evaluate_cash_break(
        self, 
        empresa_codigo: int, 
        data: str, 
        diferenca_absoluta: float, 
        operador: str
    ) -> Optional[ExecutiveAlertModel]:
        """Avalia se uma quebra de caixa deve disparar alerta proativo."""
        if diferenca_absoluta > self.CASH_BREAK_CRITICAL_RS:
            alert = ExecutiveAlertModel(
                alert_external_id=f"break_{empresa_codigo}_{data}",
                category=AlertCategory.QUEBRA_CAIXA,
                severity=AlertSeverity.CRITICAL,
                title="Quebra de Caixa Crítica",
                description=f"Operador {operador} fechou com divergência de R$ {diferenca_absoluta:,.2f}",
                impact_rs=diferenca_absoluta,
                unit_id=empresa_codigo,
                data_referencia=data,
                metadata_json={"operador": operador}
            )
            return await self._save_and_notify(alert)
        return None

    async def evaluate_tank_deviation(
        self,
        empresa_codigo: int,
        data: str,
        tanque_id: int,
        combustivel: str,
        variacao_real_litros: float,
        is_thermal_explained: bool
    ) -> Optional[ExecutiveAlertModel]:
        """Avalia desvios em tanques que não são explicados por física térmica."""
        if not is_thermal_explained and abs(variacao_real_litros) > 50:
            alert = ExecutiveAlertModel(
                alert_external_id=f"tank_{empresa_codigo}_{tanque_id}_{data}",
                category=AlertCategory.DESVIO_TANQUE,
                severity=AlertSeverity.CRITICAL,
                title="Desvio Suspeito em Tanque",
                description=f"Tanque {tanque_id} ({combustivel}) teve variação de {variacao_real_litros:,.2f}L não explicada por temperatura.",
                impact_rs=None,
                unit_id=empresa_codigo,
                data_referencia=data,
                metadata_json={"tanque_id": tanque_id, "combustivel": combustivel}
            )
            return await self._save_and_notify(alert)
        return None

    async def evaluate_cash_vacuum(
        self,
        empresa_codigo: int,
        data: str,
        vacuo_dias: float,
        necessidade_capital: float
    ) -> Optional[ExecutiveAlertModel]:
        """Avalia se o vácuo financeiro ultrapassou o limite operacional."""
        if vacuo_dias > self.VACUUM_LIMIT_DAYS:
            alert = ExecutiveAlertModel(
                alert_external_id=f"vacuum_{empresa_codigo}_{data}",
                category=AlertCategory.ESTOURO_VACUO,
                severity=AlertSeverity.WARNING,
                title="Estouro de Vácuo Financeiro",
                description=f"Vácuo de {vacuo_dias:,.1f} dias identificado. Necessidade de capital: R$ {necessidade_capital:,.2f}",
                impact_rs=necessidade_capital,
                unit_id=empresa_codigo,
                data_referencia=data,
                metadata_json={"vacuo_dias": vacuo_dias}
            )
            return await self._save_and_notify(alert)
        return None

    async def evaluate_ruptura_curva_a(
        self,
        empresa_codigo: int,
        data: str,
        produto_codigo: int,
        produto_nome: str,
        estoque: float,
        dias_cobertura: float
    ) -> Optional[ExecutiveAlertModel]:
        """Avalia ruptura de produtos Curva A (Alta Margem/Giro)."""
        if dias_cobertura <= 2.0:
            alert = ExecutiveAlertModel(
                alert_external_id=f"ruptura_{empresa_codigo}_{produto_codigo}_{data}",
                category=AlertCategory.RUPTURA_CURVA_A,
                severity=AlertSeverity.CRITICAL,
                title="Ruptura Iminente Curva A",
                description=f"Produto {produto_nome} com apenas {dias_cobertura:,.1f} dias de cobertura ({estoque:,.0f} un).",
                impact_rs=None,
                unit_id=empresa_codigo,
                data_referencia=data,
                metadata_json={"produto_codigo": produto_codigo, "produto_nome": produto_nome}
            )
            return await self._save_and_notify(alert)
        return None

    async def list_unresolved(self, unit_id: Optional[int] = None) -> List[ExecutiveAlertModel]:
        """Retorna lista de alertas ainda não resolvidos."""
        if self.repository:
            return await self.repository.list_unresolved(unit_id=unit_id)
        return []

    async def resolve_alert(self, alert_id: int, resolved_by: str, notes: Optional[str] = None) -> bool:
        """Marca um alerta como resolvido."""
        if self.repository:
            return await self.repository.resolve(alert_id, resolved_by, notes)
        return False

    async def get_history(
        self, 
        unit_id: Optional[int] = None, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> List[ExecutiveAlertModel]:
        """Retorna histórico de alertas."""
        if self.repository:
            return await self.repository.get_history(unit_id=unit_id, start_date=start_date, end_date=end_date)
        return []
