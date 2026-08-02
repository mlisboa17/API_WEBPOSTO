"""Serviço de Despacho de Notificações Proativas — Sprint 50."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx
from src.infrastructure.config.settings import settings
from src.models.alert_model import ExecutiveAlertModel, AlertSeverity

logger = logging.getLogger(__name__)


class NotificationDispatcherService:
    """Despacha notificações (webhooks) para alertas críticos."""

    def __init__(self, webhook_url: Optional[str] = None) -> None:
        # Tenta pegar das configurações ou do ambiente
        self.webhook_url = webhook_url or getattr(settings, "executive_notification_webhook_url", None)

    async def dispatch_alert(self, alert: ExecutiveAlertModel) -> bool:
        """Envia notificação se o alerta for crítico."""
        if alert.severity != AlertSeverity.CRITICAL:
            return False

        if not self.webhook_url:
            logger.warning("Webhook URL não configurada. Notificação ignorada.")
            return False

        payload = self._build_payload(alert)
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.webhook_url, json=payload)
                response.raise_for_status()
                logger.info(f"Notificação enviada com sucesso para alerta {alert.alert_external_id}")
                return True
        except Exception as e:
            logger.error(f"Erro ao despachar notificação: {str(e)}")
            return False

    def _build_payload(self, alert: ExecutiveAlertModel) -> Dict[str, Any]:
        """Constrói payload padronizado para o webhook."""
        impact_str = f"R$ {alert.impact_rs:,.2f}" if alert.impact_rs else "N/A"
        
        return {
            "event": "EXECUTIVE_ALERT_CRITICAL",
            "alert_id": alert.alert_external_id,
            "title": f"🚨 {alert.title}",
            "message": alert.description,
            "impact": impact_str,
            "unit": alert.unit_id,
            "category": alert.category.value,
            "data_referencia": alert.data_referencia,
            "link": f"/executive/cockpit", # Caminho relativo para o frontend
            "timestamp": alert.created_at.isoformat()
        }
