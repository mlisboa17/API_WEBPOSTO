"""Pipeline auditável WebPosto -> fatos -> conciliação da Diretoria."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from time import perf_counter
from typing import Any

from src.core.financial_vocabulary import FinancialConcept
from src.core.management_scope import LICENSED_COMPANIES, LICENSED_COMPANY_CODES
from src.domain.financial_reconciliation import (
    CoverageStatus,
    FinancialCoverage,
    FinancialFact,
    FinancialSource,
    MatchStatus,
)
from src.models.response_model import WebPostoResponse
from src.services.director_financial_reconciliation_service import DirectorFinancialReconciliationService
from src.services.department_governance_service import DepartmentGovernanceService
from src.services.director_financial_alert_service import DirectorFinancialAlertService
from src.services.financial_partition_coverage_service import FinancialPartitionCoverageService
from src.services.department_review_store import DepartmentReviewStore
from src.services.financial_expense_taxonomy_service import FinancialExpenseTaxonomyService


def _rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("resultados", "data", "items"):
            if isinstance(payload.get(key), list):
                return [row for row in payload[key] if isinstance(row, dict)]
    return []


def _money(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    text = str(value).strip().replace("R$", "").replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        amount = abs(Decimal(text)).quantize(Decimal("0.01"))
        return amount if amount > 0 else None
    except (InvalidOperation, ValueError):
        return None


def _date(row: dict[str, Any], *fields: str) -> date | None:
    for field in fields:
        raw = str(row.get(field) or "")[:10]
        try:
            return date.fromisoformat(raw)
        except ValueError:
            continue
    return None


class DirectorFinancialReconciliationPipeline:
    def __init__(self, client: Any, coverage: FinancialPartitionCoverageService | None = None,
                 review_store: DepartmentReviewStore | None = None) -> None:
        self._client = client
        self._coverage = coverage or FinancialPartitionCoverageService(client)
        self._engine = DirectorFinancialReconciliationService()
        self._departments = DepartmentGovernanceService()
        self._alerts = DirectorFinancialAlertService()
        self._reviews = review_store or DepartmentReviewStore()
        self._taxonomy = FinancialExpenseTaxonomyService()

    async def _call(self, endpoint: str, start: str, end: str) -> WebPostoResponse:
        return await self._client.call_endpoint(endpoint, params={"dataInicial": start, "dataFinal": end})

    @staticmethod
    def _fact_id(source: FinancialSource, row: dict[str, Any], fallback: int) -> str:
        fields = {
            FinancialSource.EXPENSES: ("codigo", "despesaCodigo"),
            FinancialSource.PAYABLE: ("tituloPagarCodigo", "codigo"),
            FinancialSource.CASH_EXPENSE: ("caixaCodigo", "codigo"),
            FinancialSource.ACCOUNT_MOVEMENT: ("movimentoContaCodigo", "codigo"),
        }[source]
        value = next((row.get(field) for field in fields if row.get(field) not in (None, "")), None)
        if value is None:
            stable = json.dumps(row, sort_keys=True, ensure_ascii=False, default=str)
            value = sha256(stable.encode("utf-8")).hexdigest()[:20]
        return f"{source.value}:{value}"

    def _normalize(self, source: FinancialSource, rows: list[dict[str, Any]]) -> list[FinancialFact]:
        facts: list[FinancialFact] = []
        for index, row in enumerate(rows):
            try:
                company = int(row.get("empresaCodigo"))
            except (TypeError, ValueError):
                continue
            if company not in LICENSED_COMPANY_CODES:
                continue
            if source == FinancialSource.EXPENSES:
                concept = FinancialConcept.FINANCIAL_EXPENSE
                amount = _money(row.get("valor"))
                effective = _date(row, "data", "dataMovimento")
            elif source == FinancialSource.PAYABLE:
                concept = FinancialConcept.ACCOUNT_PAYABLE
                amount = _money(row.get("valor"))
                effective = _date(row, "dataMovimento", "dataPagamento", "vencimento")
            elif source == FinancialSource.CASH_EXPENSE:
                concept = FinancialConcept.CASH_REGISTER_EXPENSE
                amount = _money(row.get("despesaApurado"))
                effective = _date(row, "dataMovimento", "fechamento", "data")
            else:
                concept = FinancialConcept.ACCOUNT_MOVEMENT
                amount = _money(row.get("valor"))
                effective = _date(row, "dataMovimento", "data")
            if amount is None or effective is None:
                continue
            fact_id = self._fact_id(source, row, index)
            department = self._departments.classify(row)
            review = self._reviews.get(fact_id)
            account_code = str(
                row.get("planoContaGerencialCodigo")
                or row.get("planoContaCodigo")
                or ""
            ) or None
            allocation = self._reviews.get_allocation(account_code) if not review else None
            rule = self._reviews.get_rule(account_code) if not review and not allocation else None
            reviewed_department = (
                review.department if review else rule.department if rule else department.department
            )
            facts.append(FinancialFact(
                fact_id=fact_id,
                source=source,
                concept=concept,
                company_code=company,
                effective_date=effective,
                amount=amount,
                document=str(row.get("documento") or row.get("numeroTitulo") or row.get("descricaoDocumento") or "") or None,
                description=str(
                    row.get("planoConta")
                    or row.get("planoContaGerencialDescricao")
                    or row.get("descricao")
                    or row.get("historico")
                    or ""
                ) or None,
                management_account_code=account_code,
                management_category=str(
                    row.get("categoriaLogosV3")
                    or row.get("categoriaLogosV2")
                    or row.get("categoriaLogos")
                    or ""
                ) or None,
                cost_center=str(row.get("centroCusto") or row.get("centroCustoDescricao") or "") or None,
                supplier=str(row.get("fornecedor") or row.get("fornecedorNome") or row.get("pessoaNome") or "") or None,
                cash_register_code=str(row.get("caixaCodigo") or "") or None,
                source_status=str(row.get("situacao") or row.get("tipo") or "") or None,
                department=reviewed_department,
                department_method=("MANUAL_REVIEW" if review else "SHARED_ALLOCATION" if allocation else "ACCOUNT_MAPPING_RULE" if rule else department.method),
                department_evidence=(
                    (f"review:{review.reviewer}",) if review
                    else (f"allocation:{allocation.management_account_code}",) if allocation
                    else (f"account-rule:{rule.management_account_code}",) if rule
                    else department.evidence
                ),
                department_confidence=Decimal("1.00") if review or rule or allocation else department.confidence,
                allocation_percentages={key: Decimal(value) for key, value in allocation.percentages.items()} if allocation else {},
            ))
        return facts

    async def build(self, start: str, end: str, company_code: int | None = None) -> dict[str, Any]:
        started = perf_counter()
        requested = ((company_code,) if company_code is not None else tuple(sorted(LICENSED_COMPANY_CODES)))
        if any(code not in LICENSED_COMPANY_CODES for code in requested):
            raise ValueError("empresaCodigo fora das tres licencas autorizadas")

        expenses, payables, cash = await asyncio.gather(
            self._call("despesas_financeiro_rede", start, end),
            self._call("financeiro", start, end),
            self._call("caixa_apresentado", start, end),
        )
        movements = await self._coverage.collect_account_movements(start, end, requested)
        source_responses = {
            FinancialSource.EXPENSES: expenses,
            FinancialSource.PAYABLE: payables,
            FinancialSource.CASH_EXPENSE: cash,
            FinancialSource.ACCOUNT_MOVEMENT: movements,
        }
        facts: list[FinancialFact] = []
        coverages: list[FinancialCoverage] = []
        for source, response in source_responses.items():
            rows = _rows(response.data) if response.success else []
            rows = [row for row in rows if int(row.get("empresaCodigo") or 0) in requested]
            normalized = self._normalize(source, rows)
            facts.extend(normalized)

            if not response.success:
                status = CoverageStatus.SOURCE_UNAVAILABLE
                complete = False
            else:
                if source == FinancialSource.ACCOUNT_MOVEMENT:
                    is_complete = bool(((response.data or {}).get("coverage") or {}).get("complete"))
                    if not is_complete:
                        status = CoverageStatus.INCOMPLETE_COVERAGE
                        complete = False
                    elif len(normalized) > 0:
                        status = CoverageStatus.PROVEN_WITH_MOVEMENT
                        complete = True
                    else:
                        status = CoverageStatus.PROVEN_WITHOUT_MOVEMENT
                        complete = True
                else:
                    status = (
                        CoverageStatus.PROVEN_WITH_MOVEMENT if len(normalized) > 0
                        else CoverageStatus.PROVEN_WITHOUT_MOVEMENT
                    )
                    complete = True

            strategy = (
                "COMPANY_DAY_CURSOR" if source == FinancialSource.ACCOUNT_MOVEMENT
                else "DATE_RANGE_FILTERED_BY_LICENSE"
            )
            coverages.append(FinancialCoverage(
                source=source,
                status=status,
                complete=complete,
                records=len(normalized),
                strategy=strategy,
                warning=None if complete else "Fonte incompleta; totais bloqueados",
            ))

        source_coverage_complete = all(item.complete for item in coverages)
        reconciliation = self._engine.reconcile(
            facts, complete_source_coverage=source_coverage_complete
        )
        department_eligible = [fact for fact in facts if fact.concept == FinancialConcept.FINANCIAL_EXPENSE]
        governance = {
            "eligible": len(department_eligible),
            "classified": sum(1 for fact in department_eligible if fact.department is not None or fact.allocation_percentages),
            "allocated": sum(1 for fact in department_eligible if fact.allocation_percentages),
            "unclassified": sum(1 for fact in department_eligible if fact.department is None and not fact.allocation_percentages),
            "conflicts": sum(1 for fact in department_eligible if fact.department_method == "CONFLICTING_EVIDENCE"),
            "methods": sorted({fact.department_method for fact in department_eligible}),
            "automaticClassificationThreshold": "0.90",
        }
        expenses_coverage = next(c for c in coverages if c.source == FinancialSource.EXPENSES)
        proven_zero_expenses = expenses_coverage.status == CoverageStatus.PROVEN_WITHOUT_MOVEMENT
        
        departmental_classification_complete = (
            (governance["eligible"] > 0 or proven_zero_expenses)
            and governance["unclassified"] == 0
            and governance["conflicts"] == 0
        )
        complete = source_coverage_complete and departmental_classification_complete
        fact_by_id = {fact.fact_id: fact for fact in facts}
        company_names = {item.empresa_codigo: item.nome for item in LICENSED_COMPANIES}
        summary: dict[tuple[int, str], dict[str, Any]] = defaultdict(lambda: {
            "confirmedDreAmount": Decimal("0"), "confirmedMatches": 0,
            "probableMatches": 0, "quarantined": 0, "unmatched": 0, "duplicates": 0,
        })
        for company in requested:
            for department in ("combustiveis", "conveniencia", "lubrificantes"):
                summary[(company, department)]
        for match in reconciliation.matches:
            expense = next((fact_by_id[item] for item in match.fact_ids
                            if fact_by_id[item].source == FinancialSource.EXPENSES), None)
            if expense is None:
                continue
            anchor = expense
            targets = (
                list(anchor.allocation_percentages.items())
                if anchor.allocation_percentages
                else [(anchor.department or "nao_classificado", Decimal("100"))]
            )
            for department, percentage in targets:
                bucket = summary[(anchor.company_code, department)]
                if match.status == MatchStatus.CONFIRMED:
                    bucket["confirmedMatches"] += 1
                    if expense and match.may_enter_dre:
                        bucket["confirmedDreAmount"] += expense.amount * percentage / Decimal("100")
                elif match.status == MatchStatus.PROBABLE:
                    bucket["probableMatches"] += 1
                elif match.status == MatchStatus.QUARANTINED:
                    bucket["quarantined"] += 1
                elif match.status == MatchStatus.DUPLICATE:
                    bucket["duplicates"] += 1
                else:
                    bucket["unmatched"] += 1

        executive = [{
            "companyCode": company,
            "companyName": company_names[company],
            "department": department,
            **{key: (str(value.quantize(Decimal("0.01"))) if isinstance(value, Decimal) else value)
               for key, value in values.items()},
        } for (company, department), values in sorted(summary.items())]
        alerts = self._alerts.evaluate(coverages, executive)
        alert_summary = {
            "total": len(alerts),
            "critical": sum(1 for alert in alerts if alert.severity.value == "CRITICA"),
            "high": sum(1 for alert in alerts if alert.severity.value == "ALTA"),
            "medium": sum(1 for alert in alerts if alert.severity.value == "MEDIA"),
        }
        treasury = {
            "accountMovements": sum(1 for fact in facts if fact.source == FinancialSource.ACCOUNT_MOVEMENT),
            "payables": sum(1 for fact in facts if fact.source == FinancialSource.PAYABLE),
            "cashExpenses": sum(1 for fact in facts if fact.source == FinancialSource.CASH_EXPENSE),
            "requiresDepartment": False,
        }
        departmental_dre = [{
            "companyCode": row["companyCode"],
            "companyName": row["companyName"],
            "department": row["department"],
            "confirmedExpenses": row["confirmedDreAmount"] if complete else None,
            "status": "LIBERADO" if complete else "BLOQUEADO",
        } for row in executive if row["department"] != "nao_classificado"]
        reviewable = [{
            "factId": fact.fact_id,
            "companyCode": fact.company_code,
            "companyName": company_names[fact.company_code],
            "date": fact.effective_date.isoformat(),
            "amount": str(fact.amount),
            "description": fact.description,
            "document": fact.document,
            "supplier": fact.supplier,
            "costCenter": fact.cost_center,
            "managementCategory": fact.management_category,
            "taxonomySuggestion": self._taxonomy.suggest({
                "planoConta": fact.description,
                "descricaoDocumento": fact.document,
                "centroCusto": fact.cost_center,
                "fornecedor": fact.supplier,
            }).model_dump(mode="json"),
            "method": fact.department_method,
            "managementAccountCode": fact.management_account_code,
        } for fact in department_eligible if fact.department is None and not fact.allocation_percentages]
        homologation_groups: dict[tuple[int, str], dict[str, Any]] = {}
        for fact in department_eligible:
            if fact.department is not None or fact.allocation_percentages:
                continue
            key = (fact.company_code, fact.management_account_code or "SEM_PLANO")
            group = homologation_groups.setdefault(key, {
                "companyCode": fact.company_code,
                "managementAccountCode": fact.management_account_code,
                "records": 0,
                "totalAmount": Decimal("0"),
                "factIds": [],
                "decisionRequired": "DEPARTMENT_OR_SHARED_ALLOCATION",
            })
            group["records"] += 1
            group["totalAmount"] += fact.amount
            group["factIds"].append(fact.fact_id)
        homologation_queue = [{
            **group,
            "totalAmount": str(group["totalAmount"].quantize(Decimal("0.01"))),
        } for group in homologation_groups.values()]
        return {
            "period": {"start": start, "end": end},
            "scope": {"companies": list(requested), "departments": ["combustiveis", "conveniencia", "lubrificantes"]},
            "coverage": [item.model_dump(mode="json") for item in coverages],
            "departmentGovernance": governance,
            "treasury": treasury,
            "complete": complete,
            "executiveSummary": executive,
            "alerts": [alert.model_dump(mode="json") for alert in alerts],
            "alertSummary": alert_summary,
            "departmentalDre": departmental_dre,
            "reviewableFacts": reviewable,
            "homologationQueue": homologation_queue,
            "matches": [item.model_dump(mode="json") for item in reconciliation.matches],
            "warnings": list(reconciliation.warnings),
            "publication": {
                "sourceCoverageComplete": source_coverage_complete,
                "departmentalClassificationComplete": departmental_classification_complete,
                "dreTotalsReleased": complete,
                "rawPayloadExposed": False,
            },
            "performance": {"totalMs": round((perf_counter() - started) * 1000, 1)},
        }
