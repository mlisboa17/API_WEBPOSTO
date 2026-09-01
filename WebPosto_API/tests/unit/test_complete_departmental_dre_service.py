from src.models.response_model import WebPostoResponse
from src.services.complete_departmental_dre_service import CompleteDepartmentalDreService


class Reconciliation:
    async def build(self, start, end, company, **kwargs):
        return {
            "publication": {"dreTotalsReleased": True},
            "regime": kwargs.get("regime") or "competencia",
            "periodLock": {},
            "departmentalDre": [
                {"companyCode": 11495, "department": dept, "confirmedExpenses": "10.00"}
                for dept in ("combustiveis", "conveniencia", "lubrificantes")
            ],
        }


class Fuel:
    async def build(self, start, end, company):
        return WebPostoResponse.ok({"empresas": [{
            "empresaCodigo": 11495,
            "produtos": [{"faturamento": "100.00", "custoRegistrado": "60.00"}],
            "pagination": {"complete": True},
        }]})


class NonFuel:
    async def build(self, start, end, company):
        return WebPostoResponse.ok({"departmentDreRows": [
            {"empresaCodigo": 11495, "departamento": "conveniencia", "faturamento": "80", "custo": "50", "complete": True},
            {"empresaCodigo": 11495, "departamento": "lubrificantes", "faturamento": "40", "custo": "20", "complete": True},
        ]})


async def test_builds_complete_dre_without_generic_consolidation() -> None:
    result = await CompleteDepartmentalDreService(Reconciliation(), Fuel(), NonFuel()).build(
        "2026-07-01", "2026-07-01", 11495
    )
    assert result["allReleased"] is True
    assert result["consolidatedGenericResult"] is False
    fuel = next(row for row in result["lines"] if row["department"] == "combustiveis")
    assert fuel["revenue"] == "100.00"
    assert fuel["operatingResult"] == "30.00"
    assert fuel["operationalEvidence"]["status"] == "COMPROVADO"


async def test_exposes_proven_sales_without_publishing_blocked_dre() -> None:
    class PendingExpenses:
        async def build(self, start, end, company, **kwargs):
            return {"publication": {"dreTotalsReleased": False}, "departmentalDre": []}

    result = await CompleteDepartmentalDreService(PendingExpenses(), Fuel(), NonFuel()).build(
        "2026-07-01", "2026-07-01", 11495
    )
    fuel = next(row for row in result["lines"] if row["department"] == "combustiveis")
    assert fuel["status"] == "BLOQUEADO"
    assert fuel["revenue"] is None
    assert fuel["operationalEvidence"]["revenue"] == "100.00"
    assert "CLASSIFICACAO_DESPESAS" in fuel["missingEvidence"]


async def test_blocks_department_when_sales_evidence_is_missing() -> None:
    class EmptyNonFuel:
        async def build(self, start, end, company):
            return WebPostoResponse.ok({})

    result = await CompleteDepartmentalDreService(Reconciliation(), Fuel(), EmptyNonFuel()).build(
        "2026-07-01", "2026-07-01", 11495
    )
    convenience = next(row for row in result["lines"] if row["department"] == "conveniencia")
    assert convenience["status"] == "BLOQUEADO"
    assert "FATURAMENTO" in convenience["missingEvidence"]


async def test_dre_reports_financial_evidence_status() -> None:
    class ZeroProvenReconciliation:
        async def build(self, start, end, company, **kwargs):
            return {
                "publication": {"dreTotalsReleased": True},
                "coverage": [{
                    "source": "DESPESAS_FINANCEIRO_REDE",
                    "status": "COMPROVADO_SEM_MOVIMENTO",
                    "complete": True
                }],
                "departmentalDre": [
                    {"companyCode": 11495, "department": "combustiveis", "confirmedExpenses": "0.00"}
                ]
            }

    result = await CompleteDepartmentalDreService(ZeroProvenReconciliation(), Fuel(), NonFuel()).build(
        "2026-07-01", "2026-07-01", 11495
    )
    fuel = next(row for row in result["lines"] if row["department"] == "combustiveis")
    assert fuel["status"] == "LIBERADO"
    assert fuel["expenses"] == "0.00"
    assert fuel["financialEvidence"]["status"] == "COMPROVADO_SEM_MOVIMENTO"
    assert fuel["financialEvidence"]["confirmedExpenses"] == "0.00"

