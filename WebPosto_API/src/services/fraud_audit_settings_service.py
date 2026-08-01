"""CRUD de parâmetros dinâmicos de auditoria anti-fraude.

Prioridade: SQLModel/Postgres → fallback JSON local (data/audit_fraud_settings.json).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

LOGGER = logging.getLogger(__name__)

DEFAULTS = {
    "empresa_id": 0,
    "tempo_retencao_critico_min": 30,
    "tempo_retencao_atencao_min": 15,
    "tempo_agrupamento_max_min": 15,
    "percentual_desconto_suspeito_pct": 10.0,
    "recorrencia_cpf_cartao_limite": 3,
}

_JSON_PATH = Path(__file__).resolve().parents[2] / "data" / "audit_fraud_settings.json"


class AuditFraudSettingsDTO(BaseModel):
    empresa_id: int = 0
    tempo_retencao_critico_min: int = 30
    tempo_retencao_atencao_min: int = 15
    tempo_agrupamento_max_min: int = 15
    percentual_desconto_suspeito_pct: float = 10.0
    recorrencia_cpf_cartao_limite: int = 3
    updated_at: str | None = None
    fonte: str = "defaults"


class AuditFraudSettingsUpdate(BaseModel):
    empresa_id: int = 0
    tempo_retencao_critico_min: int = Field(10, ge=1, le=180)
    tempo_retencao_atencao_min: int = Field(5, ge=1, le=120)
    tempo_agrupamento_max_min: int = Field(5, ge=1, le=120)
    percentual_desconto_suspeito_pct: float = Field(10.0, ge=0, le=100)
    recorrencia_cpf_cartao_limite: int = Field(3, ge=2, le=50)


def _normalize(raw: dict[str, Any], fonte: str) -> AuditFraudSettingsDTO:
    critico = int(raw.get("tempo_retencao_critico_min") or DEFAULTS["tempo_retencao_critico_min"])
    atencao = int(raw.get("tempo_retencao_atencao_min") or DEFAULTS["tempo_retencao_atencao_min"])
    if atencao >= critico:
        atencao = max(1, critico - 1)
    return AuditFraudSettingsDTO(
        empresa_id=int(raw.get("empresa_id") or 0),
        tempo_retencao_critico_min=critico,
        tempo_retencao_atencao_min=atencao,
        tempo_agrupamento_max_min=int(
            raw.get("tempo_agrupamento_max_min") or DEFAULTS["tempo_agrupamento_max_min"]
        ),
        percentual_desconto_suspeito_pct=float(
            raw.get("percentual_desconto_suspeito_pct")
            or DEFAULTS["percentual_desconto_suspeito_pct"]
        ),
        recorrencia_cpf_cartao_limite=int(
            raw.get("recorrencia_cpf_cartao_limite")
            or DEFAULTS["recorrencia_cpf_cartao_limite"]
        ),
        updated_at=str(raw.get("updated_at") or "") or None,
        fonte=fonte,
    )


def _read_json(empresa_id: int = 0) -> AuditFraudSettingsDTO | None:
    try:
        if not _JSON_PATH.exists():
            return None
        data = json.loads(_JSON_PATH.read_text(encoding="utf-8"))
        rows = data if isinstance(data, list) else [data]
        for row in rows:
            if int(row.get("empresa_id") or 0) == int(empresa_id):
                return _normalize(row, "json_file")
        if rows:
            return _normalize(rows[0], "json_file")
    except Exception as exc:
        LOGGER.warning("fraud_settings json read: %s", exc)
    return None


def _write_json(dto: AuditFraudSettingsDTO) -> None:
    _JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = dto.model_dump()
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    existing: list[dict[str, Any]] = []
    if _JSON_PATH.exists():
        try:
            raw = json.loads(_JSON_PATH.read_text(encoding="utf-8"))
            existing = raw if isinstance(raw, list) else [raw]
        except Exception:
            existing = []
    others = [r for r in existing if int(r.get("empresa_id") or 0) != dto.empresa_id]
    others.append(payload)
    _JSON_PATH.write_text(json.dumps(others, ensure_ascii=False, indent=2), encoding="utf-8")


async def get_settings(empresa_id: int = 0) -> AuditFraudSettingsDTO:
    try:
        from sqlmodel import select
        from src.infrastructure.config.database import AsyncSessionLocal
        from src.models.audit_fraud_settings_model import ConfiguracaoAuditoriaFraude

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ConfiguracaoAuditoriaFraude).where(
                    ConfiguracaoAuditoriaFraude.empresa_id == int(empresa_id)
                )
            )
            row = result.scalar_one_or_none()
            if row is None and empresa_id != 0:
                result = await session.execute(
                    select(ConfiguracaoAuditoriaFraude).where(
                        ConfiguracaoAuditoriaFraude.empresa_id == 0
                    )
                )
                row = result.scalar_one_or_none()
            if row is not None:
                return _normalize(
                    {
                        "empresa_id": row.empresa_id,
                        "tempo_retencao_critico_min": row.tempo_retencao_critico_min,
                        "tempo_retencao_atencao_min": row.tempo_retencao_atencao_min,
                        "tempo_agrupamento_max_min": row.tempo_agrupamento_max_min,
                        "percentual_desconto_suspeito_pct": row.percentual_desconto_suspeito_pct,
                        "recorrencia_cpf_cartao_limite": row.recorrencia_cpf_cartao_limite,
                        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                    },
                    "database",
                )
    except Exception as exc:
        LOGGER.warning("fraud_settings db get fallback json: %s", exc)

    cached = _read_json(empresa_id)
    if cached:
        return cached
    return _normalize({**DEFAULTS, "empresa_id": empresa_id}, "defaults")


async def save_settings(update: AuditFraudSettingsUpdate) -> AuditFraudSettingsDTO:
    if update.tempo_retencao_atencao_min >= update.tempo_retencao_critico_min:
        update.tempo_retencao_atencao_min = max(1, update.tempo_retencao_critico_min - 1)

    now = datetime.now(timezone.utc)
    dto = AuditFraudSettingsDTO(
        empresa_id=update.empresa_id,
        tempo_retencao_critico_min=update.tempo_retencao_critico_min,
        tempo_retencao_atencao_min=update.tempo_retencao_atencao_min,
        tempo_agrupamento_max_min=update.tempo_agrupamento_max_min,
        percentual_desconto_suspeito_pct=update.percentual_desconto_suspeito_pct,
        recorrencia_cpf_cartao_limite=update.recorrencia_cpf_cartao_limite,
        updated_at=now.isoformat(),
        fonte="database",
    )

    db_ok = False
    try:
        from sqlmodel import select
        from src.infrastructure.config.database import AsyncSessionLocal
        from src.models.audit_fraud_settings_model import ConfiguracaoAuditoriaFraude

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ConfiguracaoAuditoriaFraude).where(
                    ConfiguracaoAuditoriaFraude.empresa_id == update.empresa_id
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                row = ConfiguracaoAuditoriaFraude(empresa_id=update.empresa_id)
                session.add(row)
            row.tempo_retencao_critico_min = update.tempo_retencao_critico_min
            row.tempo_retencao_atencao_min = update.tempo_retencao_atencao_min
            row.tempo_agrupamento_max_min = update.tempo_agrupamento_max_min
            row.percentual_desconto_suspeito_pct = update.percentual_desconto_suspeito_pct
            row.recorrencia_cpf_cartao_limite = update.recorrencia_cpf_cartao_limite
            row.updated_at = now
            await session.commit()
            db_ok = True
            dto.fonte = "database"
    except Exception as exc:
        LOGGER.warning("fraud_settings db save fallback json: %s", exc)

    _write_json(dto)
    if not db_ok:
        dto.fonte = "json_file"
    return dto
