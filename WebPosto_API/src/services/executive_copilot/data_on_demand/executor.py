"""Executor do DATA-ON-DEMAND. Nesta sprint apenas o falso; sem rede."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from src.services.executive_copilot.contracts import ClaimStatus, WEBPOSTO_WRITES
from src.services.executive_copilot.data_on_demand.models import (
    DataRefreshCommand,
    PageOutcome,
    PairOutcome,
    RefreshResult,
)
from src.services.executive_copilot.data_on_demand.policy import assert_allowlisted
from src.services.executive_copilot.data_on_demand.states import DataRequestState
from src.services.sds_sanitize import sanitize_text


class DataRefreshExecutor(Protocol):
    def execute(self, command: DataRefreshCommand) -> RefreshResult: ...


class FakeDataRefreshExecutor:
    """Simula páginas ABASTECIMENTO. Não chama httpx, WebPosto nem SDS."""

    def __init__(
        self,
        *,
        pages_per_pair: int = 2,
        fail_pages: set[tuple[int, str, int]] | None = None,
        fail_detail: str = "pagina incompleta",
        fail_hard: bool = False,
        auto_by_units: bool = False,
    ) -> None:
        self.pages_per_pair = pages_per_pair
        self.fail_pages = set(fail_pages or [])
        self.fail_detail = fail_detail
        self.fail_hard = fail_hard
        self.auto_by_units = auto_by_units
        self.calls: list[DataRefreshCommand] = []
        self.external_requests = 0

    def execute(self, command: DataRefreshCommand) -> RefreshResult:
        assert_allowlisted(command.operation, command.logical_endpoint)
        if command.webposto_writes != WEBPOSTO_WRITES:
            raise ValueError("WEBPOSTO_WRITES deve permanecer 0")
        self.calls.append(command)
        if self.fail_hard:
            raise RuntimeError("falha simulada do executor local")
        fail_pages = set(self.fail_pages)
        if self.auto_by_units and not fail_pages:
            units = {unit for unit, _ in command.gaps}
            if 74014 in units:
                raise RuntimeError("falha simulada do executor local")
            if 11495 in units:
                fail_pages = {(unit, day, 2) for unit, day in command.gaps if unit == 11495}
        pairs: list[PairOutcome] = []
        for unit, day_iso in command.gaps:
            pages: list[PageOutcome] = []
            pair_ok = True
            for page in range(1, self.pages_per_pair + 1):
                failed = (unit, day_iso, page) in fail_pages
                if failed:
                    pair_ok = False
                    pages.append(PageOutcome(page=page, ok=False, detail=sanitize_text(self.fail_detail)))
                else:
                    pages.append(PageOutcome(page=page, ok=True, detail=""))
            pairs.append(
                PairOutcome(
                    unit=unit,
                    day=date.fromisoformat(day_iso),
                    pages=pages,
                    consolidated=pair_ok,
                    claim_status=ClaimStatus.UNAVAILABLE.value,
                )
            )
        if pairs and all(item.consolidated for item in pairs):
            state = DataRequestState.SUCCESS
        elif any(item.consolidated for item in pairs):
            state = DataRequestState.PARTIAL
        else:
            state = DataRequestState.PARTIAL if pairs else DataRequestState.FAILED
        return RefreshResult(state=state, pairs=pairs, webposto_writes=WEBPOSTO_WRITES)
