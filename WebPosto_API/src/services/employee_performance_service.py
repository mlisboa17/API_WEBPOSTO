"""Sprint 55 — Employee Performance Service: ranking, produtividade e auditoria de caixa por funcionário."""
from __future__ import annotations
import logging
from typing import Any, List, Dict, Optional
from collections import defaultdict
from datetime import datetime

from src.interfaces.http.schemas.executive_employee_schema import (
    EmployeePerformanceSummary,
    EmployeeRanking,
    CashBreakByEmployee,
)

logger = logging.getLogger(__name__)


class EmployeePerformanceService:
    """
    Consolida desempenho de frentistas e operadores de caixa.
    Integra dados de VENDA, ABASTECIMENTO e CAIXA para produzir ranking
    e auditoria de quebras por funcionário/turno.
    """

    def __init__(self, raw_client: Any | None = None) -> None:
        self._client = raw_client

    def analyze(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: Optional[int] = None,
    ) -> EmployeePerformanceSummary:
        # TODO: substituir mock por fetch real do WebPosto quando integração estiver pronta
        sales = self._mock_sales(data_inicial, data_final, empresa_codigo)
        cash = self._mock_cash(data_inicial, data_final, empresa_codigo)
        employees = self._mock_employees()
        return self._build_summary(sales, cash, employees)

    def _mock_employees(self) -> List[Dict[str, Any]]:
        return [
            {"funcionarioCodigo": 101, "nome": "João Silva", "funcao": "Frentista", "horas_trabalhadas": 176},
            {"funcionarioCodigo": 102, "nome": "Maria Santos", "funcao": "Frentista", "horas_trabalhadas": 160},
            {"funcionarioCodigo": 103, "nome": "Pedro Lima", "funcao": "Operador Caixa", "horas_trabalhadas": 180},
            {"funcionarioCodigo": 104, "nome": "Ana Costa", "funcao": "Frentista", "horas_trabalhadas": 168},
            {"funcionarioCodigo": 105, "nome": "Bruno Alves", "funcao": "Operador Caixa", "horas_trabalhadas": 172},
        ]

    def _mock_sales(self, start: str, end: str, unit: Optional[int]) -> List[Dict[str, Any]]:
        return [
            {"funcionarioCodigo": 101, "tipo": "ABASTECIMENTO", "litros": 42150, "valor": 245000, "upsell": 8500},
            {"funcionarioCodigo": 102, "tipo": "ABASTECIMENTO", "litros": 38900, "valor": 228000, "upsell": 12400},
            {"funcionarioCodigo": 104, "tipo": "ABASTECIMENTO", "litros": 31500, "valor": 185000, "upsell": 4200},
        ]

    def _mock_cash(self, start: str, end: str, unit: Optional[int]) -> List[Dict[str, Any]]:
        return [
            {"funcionarioCodigo": 103, "turno": "Manhã", "pdvCodigo": 1, "caixaCodigo": 1001, "datahora": "2026-07-26T08:00:00", "diferenca": 12.5, "status": "OK"},
            {"funcionarioCodigo": 103, "turno": "Tarde", "pdvCodigo": 2, "caixaCodigo": 1002, "datahora": "2026-07-26T14:00:00", "diferenca": -85.0, "status": "ATENCAO"},
            {"funcionarioCodigo": 105, "turno": "Noite", "pdvCodigo": 3, "caixaCodigo": 1003, "datahora": "2026-07-26T22:00:00", "diferenca": -150.2, "status": "CRITICO"},
        ]

    def _build_summary(
        self,
        sales: List[Dict[str, Any]],
        cash: List[Dict[str, Any]],
        employees: List[Dict[str, Any]],
    ) -> EmployeePerformanceSummary:
        # Agregar vendas por funcionário
        by_employee: Dict[int, Dict[str, Any]] = defaultdict(lambda: {"litros": 0.0, "valor": 0.0, "upsell": 0.0, "count": 0})
        for sale in sales:
            code = int(sale.get("funcionarioCodigo", 0))
            by_employee[code]["litros"] += float(sale.get("litros", 0))
            by_employee[code]["valor"] += float(sale.get("valor", 0))
            by_employee[code]["upsell"] += float(sale.get("upsell", 0))
            by_employee[code]["count"] += 1

        ranking: List[EmployeeRanking] = []
        for emp in employees:
            code = int(emp.get("funcionarioCodigo", 0))
            nome = emp.get("nome", "Desconhecido")
            funcao = emp.get("funcao", "Operador")
            horas = float(emp.get("horas_trabalhadas", 1))
            agg = by_employee[code]
            litros = agg["litros"]
            valor = agg["valor"]
            count = agg["count"] or 1
            ticket = valor / count if count > 0 else 0.0
            conversion = (agg["upsell"] / valor * 100) if valor > 0 else 0.0
            galonagem_hora = litros / horas if horas > 0 else 0.0

            # Score simples: 50% produtividade, 30% ticket, 20% conversão
            score = min(100.0, round((galonagem_hora * 0.5) + (ticket * 0.03) + (conversion * 0.2), 2))

            if funcao in ("Frentista", "Operador"):
                ranking.append(EmployeeRanking(
                    funcionario_codigo=code,
                    nome=nome,
                    funcao=funcao,
                    litros_vendidos=round(litros, 2),
                    ticket_medio=round(ticket, 2),
                    conversion_pct=round(conversion, 2),
                    galonagem_por_hora=round(galonagem_hora, 2),
                    score=score,
                ))

        ranking.sort(key=lambda x: x.score, reverse=True)
        auditoria = [
            CashBreakByEmployee(
                funcionario_codigo=int(c.get("funcionarioCodigo", 0)),
                nome=next((e.get("nome") for e in employees if int(e.get("funcionarioCodigo", 0)) == int(c.get("funcionarioCodigo", 0))), "Desconhecido"),
                turno=c.get("turno", ""),
                pdv_codigo=int(c.get("pdvCodigo", 0)),
                caixa_codigo=int(c.get("caixaCodigo", 0)),
                datahora=c.get("datahora", ""),
                diferenca=float(c.get("diferenca", 0)),
                status=c.get("status", "OK"),
            )
            for c in cash
        ]

        media = round(sum(r.galonagem_por_hora for r in ranking) / len(ranking), 2) if ranking else 0.0

        return EmployeePerformanceSummary(
            ranking=ranking,
            auditoria_caixa=auditoria,
            media_galonagem_por_hora=media,
            melhor_frentista=ranking[0] if ranking else None,
            pior_frentista=ranking[-1] if ranking else None,
        )
