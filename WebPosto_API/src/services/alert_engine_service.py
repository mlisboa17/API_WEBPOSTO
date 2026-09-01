"""Motor de Alertas Proativos com Matriz de Criticidade.

Sprint 59: Sistema de notificacoes ativas por impacto financeiro.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel


class AlertSeverity(str, Enum):
    CRITICO = "CRITICO"
    MEDIO = "MEDIO"
    BAIXO = "BAIXO"


class AlertStatus(str, Enum):
    PENDENTE = "PENDENTE"
    VISUALIZADO = "VISUALIZADO"
    APROVADO = "APROVADO"
    REJEITADO = "REJEITADO"
    EXPIRADO = "EXPIRADO"


class AlertCategory(str, Enum):
    QUEBRA_CAIXA = "QUEBRA_CAIXA"
    ABASTECIMENTO_RETIDO = "ABASTECIMENTO_RETIDO"
    GIRO_CAIXA = "GIRO_CAIXA"
    DESVIO_TANQUE = "DESVIO_TANQUE"
    PRECO_COMBUSTIVEL = "PRECO_COMBUSTIVEL"
    ESTOQUE_CRITICO = "ESTOQUE_CRITICO"
    MARGEM_NEGATIVA = "MARGEM_NEGATIVA"


SEVERITY_THRESHOLDS = {
    AlertSeverity.CRITICO: 3000.00,
    AlertSeverity.MEDIO: 500.00,
    AlertSeverity.BAIXO: 0.00,
}

RENOTIFICATION_INTERVALS = {
    15: "15 minutos",
    30: "30 minutos",
    60: "1 hora",
    120: "2 horas",
}


@dataclass
class AlertRule:
    """Regra de deteccao de alerta."""
    
    category: AlertCategory
    description: str
    check_function: str
    default_severity: AlertSeverity = AlertSeverity.MEDIO


@dataclass
class ProactiveAlert:
    """Alerta proativo com ciclo de vida."""
    
    id: str = ""
    category: AlertCategory = AlertCategory.QUEBRA_CAIXA
    severity: AlertSeverity = AlertSeverity.MEDIO
    status: AlertStatus = AlertStatus.PENDENTE
    
    title: str = ""
    description: str = ""
    justificativa: str = ""
    
    impact_rs: float = 0.0
    empresa_codigo: int = 0
    empresa_nome: str = ""
    
    operador: str | None = None
    bico: int | None = None
    turno: str | None = None
    produto: str | None = None
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime | None = None
    
    notification_count: int = 0
    last_notification_at: datetime | None = None
    renotification_interval_min: int = 30
    
    assigned_to: str | None = None
    resolved_by: str | None = None
    resolution_note: str | None = None
    
    metadata: dict[str, Any] = field(default_factory=dict)


class NotificationProfile(BaseModel):
    """Perfil de notificacao por usuario."""
    
    user_id: str
    user_name: str
    role: str  # diretor, gerente_compras, gerente_pista
    
    empresas_autorizadas: list[int] = []
    severidades_autorizadas: list[AlertSeverity] = []
    categorias_autorizadas: list[AlertCategory] = []
    
    renotification_interval_min: int = 30
    notification_channels: list[str] = ["app", "email"]
    
    active: bool = True


class AlertEngineService:
    """Motor de processamento de alertas proativos."""
    
    def __init__(self) -> None:
        self.alerts: dict[str, ProactiveAlert] = {}
        self.profiles: dict[str, NotificationProfile] = {}
        self._alert_counter = 0
    
    def classify_severity(self, impact_rs: float) -> AlertSeverity:
        """Classifica severidade baseado no impacto financeiro."""
        if impact_rs >= SEVERITY_THRESHOLDS[AlertSeverity.CRITICO]:
            return AlertSeverity.CRITICO
        elif impact_rs >= SEVERITY_THRESHOLDS[AlertSeverity.MEDIO]:
            return AlertSeverity.MEDIO
        return AlertSeverity.BAIXO
    
    def create_alert(
        self,
        category: AlertCategory,
        title: str,
        description: str,
        impact_rs: float,
        empresa_codigo: int,
        empresa_nome: str = "",
        justificativa: str = "",
        **kwargs: Any,
    ) -> ProactiveAlert:
        """Cria um novo alerta proativo."""
        
        self._alert_counter += 1
        alert_id = f"ALT-{datetime.now().strftime('%Y%m%d')}-{self._alert_counter:04d}"
        
        severity = self.classify_severity(impact_rs)
        
        expires_at = None
        if severity == AlertSeverity.CRITICO:
            expires_at = datetime.now() + timedelta(hours=24)
        elif severity == AlertSeverity.MEDIO:
            expires_at = datetime.now() + timedelta(hours=72)
        
        alert = ProactiveAlert(
            id=alert_id,
            category=category,
            severity=severity,
            title=title,
            description=description,
            justificativa=justificativa,
            impact_rs=impact_rs,
            empresa_codigo=empresa_codigo,
            empresa_nome=empresa_nome,
            expires_at=expires_at,
            **kwargs,
        )
        
        self.alerts[alert_id] = alert
        return alert
    
    def get_pending_renotifications(self) -> list[ProactiveAlert]:
        """Retorna alertas criticos que precisam de re-notificacao."""
        
        now = datetime.now()
        pending = []
        
        for alert in self.alerts.values():
            if alert.severity != AlertSeverity.CRITICO:
                continue
            if alert.status not in [AlertStatus.PENDENTE, AlertStatus.VISUALIZADO]:
                continue
            if alert.expires_at and now > alert.expires_at:
                alert.status = AlertStatus.EXPIRADO
                continue
            
            if alert.last_notification_at is None:
                pending.append(alert)
            else:
                next_notification = alert.last_notification_at + timedelta(
                    minutes=alert.renotification_interval_min
                )
                if now >= next_notification:
                    pending.append(alert)
        
        return pending
    
    def mark_notified(self, alert_id: str) -> bool:
        """Marca alerta como notificado."""
        if alert_id not in self.alerts:
            return False
        
        alert = self.alerts[alert_id]
        alert.notification_count += 1
        alert.last_notification_at = datetime.now()
        alert.updated_at = datetime.now()
        return True
    
    def update_status(
        self,
        alert_id: str,
        status: AlertStatus,
        resolved_by: str | None = None,
        resolution_note: str | None = None,
    ) -> bool:
        """Atualiza status do alerta."""
        if alert_id not in self.alerts:
            return False
        
        alert = self.alerts[alert_id]
        alert.status = status
        alert.updated_at = datetime.now()
        
        if status in [AlertStatus.APROVADO, AlertStatus.REJEITADO]:
            alert.resolved_by = resolved_by
            alert.resolution_note = resolution_note
        
        return True
    
    def get_alerts_by_severity(
        self,
        severity: AlertSeverity | None = None,
        empresa_codigo: int | None = None,
        status: AlertStatus | None = None,
    ) -> list[ProactiveAlert]:
        """Filtra alertas por severidade, empresa e status."""
        
        result = []
        for alert in self.alerts.values():
            if severity and alert.severity != severity:
                continue
            if empresa_codigo and alert.empresa_codigo != empresa_codigo:
                continue
            if status and alert.status != status:
                continue
            result.append(alert)
        
        return sorted(result, key=lambda a: a.created_at, reverse=True)
    
    def get_summary(self) -> dict[str, Any]:
        """Retorna resumo dos alertas."""
        
        criticos = len([a for a in self.alerts.values() if a.severity == AlertSeverity.CRITICO and a.status == AlertStatus.PENDENTE])
        medios = len([a for a in self.alerts.values() if a.severity == AlertSeverity.MEDIO and a.status == AlertStatus.PENDENTE])
        baixos = len([a for a in self.alerts.values() if a.severity == AlertSeverity.BAIXO and a.status == AlertStatus.PENDENTE])
        
        total_impact = sum(a.impact_rs for a in self.alerts.values() if a.status == AlertStatus.PENDENTE)
        
        pending_renotifications = len(self.get_pending_renotifications())
        
        return {
            "total_pendentes": criticos + medios + baixos,
            "criticos": criticos,
            "medios": medios,
            "baixos": baixos,
            "impacto_total_rs": round(total_impact, 2),
            "aguardando_renotificacao": pending_renotifications,
        }


_engine_instance: AlertEngineService | None = None


def get_alert_engine() -> AlertEngineService:
    """Singleton do motor de alertas."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = AlertEngineService()
    return _engine_instance
