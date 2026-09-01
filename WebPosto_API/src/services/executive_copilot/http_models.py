"""Entrada HTTP do Copiloto. extra=forbid; sem I/O."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.services.executive_copilot.contracts import PeriodWindow, SpecialistId


class AskRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    question: str = Field(alias="pergunta", min_length=1)
    specialist: SpecialistId = Field(alias="especialista")
    units: list[int] | None = Field(None, alias="unidades")
    period: PeriodWindow = Field(alias="periodo")

    @field_validator("question")
    @classmethod
    def _strip_question(cls, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("pergunta obrigatória")
        return text
