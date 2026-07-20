import pytest
from decimal import Decimal
from src.models.response_model import WebPostoResponse
from src.services.director_financial_reconciliation_pipeline import DirectorFinancialReconciliationPipeline
from src.domain.financial_reconciliation import CoverageStatus

class FakeClient:
    def __init__(self, expenses_data=None, payable_data=None, success=True):
        self.expenses_data = expenses_data if expenses_data is not None else []
        self.payable_data = payable_data if payable_data is not None else []
        self.success = success

    async def call_endpoint(self, endpoint, params):
        if endpoint == "despesas_financeiro_rede":
            if not self.success:
                return WebPostoResponse.fail(None)
            return WebPostoResponse.ok(self.expenses_data)
        if endpoint == "financeiro":
            return WebPostoResponse.ok(self.payable_data)
        if endpoint == "caixa_apresentado":
            return WebPostoResponse.ok([])
        return WebPostoResponse.ok([])

class CompleteCoverage:
    async def collect_account_movements(self, start, end, companies):
        return WebPostoResponse.ok({
            "resultados": [],
            "coverage": {"complete": True, "strategy": "COMPANY_DAY_CURSOR"},
        })

@pytest.mark.asyncio
async def test_dre_blocked_when_expenses_unavailable() -> None:
    # Caso: API falhou (success=False)
    client = FakeClient(success=False)
    pipeline = DirectorFinancialReconciliationPipeline(client, CompleteCoverage())
    
    result = await pipeline.build("2026-07-01", "2026-07-01", 11495)
    
    expenses_coverage = next(c for c in result["coverage"] if c["source"] == "DESPESAS_FINANCEIRO_REDE")
    assert expenses_coverage["status"] == CoverageStatus.SOURCE_UNAVAILABLE
    assert result["complete"] is False

@pytest.mark.asyncio
async def test_dre_released_when_zero_expenses_proven() -> None:
    # Caso: API funcionou, mas retornou vazio (zero comprovado)
    client = FakeClient(expenses_data=[])
    pipeline = DirectorFinancialReconciliationPipeline(client, CompleteCoverage())
    
    result = await pipeline.build("2026-07-01", "2026-07-01", 11495)
    
    expenses_coverage = next(c for c in result["coverage"] if c["source"] == "DESPESAS_FINANCEIRO_REDE")
    assert expenses_coverage["status"] == CoverageStatus.PROVEN_WITHOUT_MOVEMENT
    assert result["complete"] is True # Agora libera!

    for row in result["departmentalDre"]:
        assert row["status"] == "LIBERADO"
        assert row["confirmedExpenses"] == "0.00"

@pytest.mark.asyncio
async def test_dre_released_when_expenses_exist_and_classified() -> None:
    # Caso: API funcionou e retornou despesas (movimento comprovado)
    # Para ser confirmado, precisa de um match (ex: no financeiro com mesmo documento)
    client = FakeClient(
        expenses_data=[{
            "empresaCodigo": 11495,
            "codigo": 1,
            "data": "2026-07-01",
            "valor": "50.00",
            "documento": "NF123",
            "planoContaGerencialCodigo": "1",
            "planoContaGerencialDescricao": "Combustiveis",
        }],
        payable_data=[{
            "empresaCodigo": 11495,
            "tituloPagarCodigo": 100,
            "dataMovimento": "2026-07-01",
            "valor": "50.00",
            "numeroTitulo": "NF123",
            "planoContaGerencialCodigo": "1",
        }]
    )
    pipeline = DirectorFinancialReconciliationPipeline(client, CompleteCoverage())
    
    result = await pipeline.build("2026-07-01", "2026-07-01", 11495)
    
    expenses_coverage = next(c for c in result["coverage"] if c["source"] == "DESPESAS_FINANCEIRO_REDE")
    assert expenses_coverage["status"] == CoverageStatus.PROVEN_WITH_MOVEMENT
    assert result["complete"] is True
    
    combustible = next(row for row in result["departmentalDre"] if row["department"] == "combustiveis")
    assert combustible["confirmedExpenses"] == "50.00"
