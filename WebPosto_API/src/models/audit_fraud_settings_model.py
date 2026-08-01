"""Configuração dinâmica de auditoria anti-fraude de pista."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class ConfiguracaoAuditoriaFraude(SQLModel, table=True):
    """Tabela: configuracao_auditoria_fraude — thresholds por empresa (0 = rede)."""

    __tablename__ = "configuracao_auditoria_fraude"

    id: Optional[int] = Field(default=None, primary_key=True)
    empresa_id: int = Field(default=0, index=True, unique=True)
    tempo_retencao_critico_min: int = Field(default=30)
    tempo_retencao_atencao_min: int = Field(default=15)
    tempo_agrupamento_max_min: int = Field(default=15)
    percentual_desconto_suspeito_pct: float = Field(default=10.0)
    recorrencia_cpf_cartao_limite: int = Field(default=3)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
    )
