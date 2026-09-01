"""DATA-ON-DEMAND-01 — planner local. Sem rede e sem executor real."""

from src.services.executive_copilot.data_on_demand.executor import FakeDataRefreshExecutor
from src.services.executive_copilot.data_on_demand.service import DataOnDemandService
from src.services.executive_copilot.data_on_demand.states import DataRequestState

__all__ = [
    "DataOnDemandService",
    "DataRequestState",
    "FakeDataRefreshExecutor",
]
