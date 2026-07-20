"""Validação somente leitura; não imprime documentos nem descrições financeiras."""

import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.gateway.webposto_client import WebPostoClient
from src.services.director_financial_reconciliation_pipeline import (
    DirectorFinancialReconciliationPipeline,
)


async def main() -> None:
    pipeline = DirectorFinancialReconciliationPipeline(WebPostoClient())
    data = await pipeline.build("2026-07-01", "2026-07-01")
    print(f"COMPLETE={data['complete']}")
    print(f"ROWS={len(data['executiveSummary'])}")
    print(f"ALERTS={data['alertSummary']}")
    print("COVERAGE=" + ";".join(
        f"{item['source']}:{item['complete']}:{item['records']}"
        for item in data["coverage"]
    ))
    print(f"GOVERNANCE={data['departmentGovernance']}")
    print(f"PERFORMANCE_MS={data['performance']['totalMs']}")


if __name__ == "__main__":
    asyncio.run(main())
