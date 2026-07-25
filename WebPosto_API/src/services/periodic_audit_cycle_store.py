"""Agenda persistida de auditorias de prestação de contas.

Não executa lançamentos financeiros: apenas define ciclos de conferência humana.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator
from src.core.management_scope import is_licensed_company
from src.services.json_file_lock import InterProcessFileLock


DEFAULT_PATH = Path(".runtime/periodic_audits/cycles.json")
VALID_CENTERS = {"PISTA", "CONVENIENCIA"}


class PeriodicAuditCycle(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    empresa_codigo: str = Field(min_length=1)
    centro_custo: str
    periodicidade_dias: int = Field(ge=1, le=90)
    responsavel: str = Field(min_length=2)
    data_corte: date
    ativo: bool = True
    criado_em: datetime
    atualizado_em: datetime

    @field_validator("centro_custo")
    @classmethod
    def validate_center(cls, value: str) -> str:
        normalized = value.strip().upper().replace("Ê", "E").replace("É", "E")
        if normalized == "LOJA":
            normalized = "CONVENIENCIA"
        if normalized not in VALID_CENTERS:
            raise ValueError("centro_custo deve ser PISTA ou CONVENIENCIA")
        return normalized

    def proxima_auditoria(self, hoje: date | None = None) -> date:
        current = hoje or date.today()
        due = self.data_corte
        while due < current:
            due += timedelta(days=self.periodicidade_dias)
        return due

    def status(self, hoje: date | None = None) -> str:
        current = hoje or date.today()
        return "VENCE_HOJE" if self.proxima_auditoria(current) == current else "PROGRAMADA"


class PeriodicAuditCycleStore:
    def __init__(self, path: str | Path = DEFAULT_PATH) -> None:
        self._path = Path(path)

    def _load(self) -> dict[str, PeriodicAuditCycle]:
        if not self._path.exists():
            return {}
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            return {key: PeriodicAuditCycle.model_validate(value) for key, value in raw.items()}
        except (OSError, json.JSONDecodeError, ValueError):
            return {}

    def _save(self, records: dict[str, PeriodicAuditCycle]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps({key: item.model_dump(mode="json") for key, item in records.items()}, ensure_ascii=False, indent=2)
        temp: Path | None = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self._path.parent, delete=False) as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
                temp = Path(handle.name)
            os.replace(temp, self._path)
        finally:
            if temp and temp.exists():
                temp.unlink(missing_ok=True)

    def list_all(self) -> list[PeriodicAuditCycle]:
        return sorted(self._load().values(), key=lambda item: (item.empresa_codigo, item.centro_custo))

    def create(
        self, empresa_codigo: str, centro_custo: str, periodicidade_dias: int,
        responsavel: str, data_corte: date,
    ) -> PeriodicAuditCycle:
        if not is_licensed_company(empresa_codigo):
            raise ValueError("UNLICENSED_COMPANY")
        now = datetime.now(timezone.utc)
        item = PeriodicAuditCycle(
            id=str(uuid4()), empresa_codigo=str(empresa_codigo), centro_custo=centro_custo,
            periodicidade_dias=periodicidade_dias, responsavel=responsavel,
            data_corte=data_corte, criado_em=now, atualizado_em=now,
        )
        with InterProcessFileLock(self._path):
            records = self._load()
            existing = next(
                (
                    current for current in records.values()
                    if current.empresa_codigo == item.empresa_codigo
                    and current.centro_custo == item.centro_custo
                    and current.periodicidade_dias == item.periodicidade_dias
                    and current.data_corte == item.data_corte
                ),
                None,
            )
            if existing:
                return existing
            records[item.id] = item
            self._save(records)
        return item

    def set_active(self, cycle_id: str, ativo: bool) -> PeriodicAuditCycle | None:
        with InterProcessFileLock(self._path):
            records = self._load()
            current = records.get(cycle_id)
            if not current:
                return None
            updated = current.model_copy(update={"ativo": ativo, "atualizado_em": datetime.now(timezone.utc)})
            records[cycle_id] = updated
            self._save(records)
            return updated
