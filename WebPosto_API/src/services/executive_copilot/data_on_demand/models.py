"""Contratos locais do planner. extra=forbid; sem I/O."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.services.executive_copilot.contracts import PeriodWindow, WEBPOSTO_WRITES
from src.services.executive_copilot.data_on_demand.policy import LOGICAL_ENDPOINT, OPERATION
from src.services.executive_copilot.data_on_demand.states import DataRequestState


class PlanBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    units: list[int] = Field(alias="unidades")
    period: PeriodWindow = Field(alias="periodo")


class ConfirmBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    plan_hash: str = Field(alias="planHash", min_length=16)


class DataRefreshCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["REFRESH_SDS"] = OPERATION
    logical_endpoint: Literal["ABASTECIMENTO"] = LOGICAL_ENDPOINT
    units: tuple[int, ...]
    start: date
    end: date
    gaps: tuple[tuple[int, str], ...]
    request_id: str
    plan_hash: str
    webposto_writes: int = WEBPOSTO_WRITES


class PageOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int
    ok: bool
    detail: str = ""


class PairOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit: int
    day: date
    pages: list[PageOutcome]
    consolidated: bool
    claim_status: str

    @property
    def incomplete(self) -> bool:
        return not self.consolidated or any(not page.ok for page in self.pages)


class RefreshResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: DataRequestState
    pairs: list[PairOutcome]
    webposto_writes: int = WEBPOSTO_WRITES

    def publishes_fact(self) -> bool:
        return False
