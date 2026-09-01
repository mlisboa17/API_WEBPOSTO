"""Sprint 55 / Sprint 02 — desempenho de frentistas a partir do cache RAM (sem mocks)."""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

from src.interfaces.http.schemas.executive_employee_schema import (
    CashBreakByEmployee,
    EmployeePerformanceSummary,
    EmployeeRanking,
)
from src.utils.filial_normalizer import resolve_empresa_codigo

logger = logging.getLogger(__name__)


class EmployeePerformanceService:
    """
    Consolida desempenho de frentistas e operadores de caixa.
    Fonte: PistaCacheService (abastecimentos) + CashierAuditService (quebras).
    """

    def __init__(self, raw_client: Any | None = None) -> None:
        self._client = raw_client

    def analyze(
        self,
        data_inicial: str,
        data_final: str,
        empresa_codigo: Optional[int] = None,
    ) -> EmployeePerformanceSummary:
        sales, cash, employees = self._load_from_ram(empresa_codigo)
        if not sales and not cash and not employees:
            logger.info(
                "employee_performance: cache RAM vazio periodo=%s..%s empresa=%s",
                data_inicial,
                data_final,
                empresa_codigo,
            )
            return EmployeePerformanceSummary(
                ranking=[],
                auditoria_caixa=[],
                media_galonagem_por_hora=0.0,
                melhor_frentista=None,
                pior_frentista=None,
            )
        return self._build_summary(sales, cash, employees)

    def _load_from_ram(
        self, empresa_codigo: Optional[int]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        emp = resolve_empresa_codigo(empresa_codigo)
        sales: List[Dict[str, Any]] = []
        cash: List[Dict[str, Any]] = []
        employees: Dict[int, Dict[str, Any]] = {}

        try:
            from src.services.pista_cache_service import get_pista_cache

            snap = get_pista_cache().get_snapshot()
            for a in snap.baixados or ():
                if emp is not None and int(getattr(a, "idEmpresa", 0) or 0) != int(emp):
                    continue
                fid = int(getattr(a, "idFrentista", 0) or 0)
                if fid <= 0:
                    continue
                nome = str(getattr(a, "nomeFrentista", "") or f"Frentista {fid}")
                employees[fid] = {
                    "funcionarioCodigo": fid,
                    "nome": nome,
                    "funcao": "Frentista",
                    "horas_trabalhadas": 8.0,
                }
                sales.append(
                    {
                        "funcionarioCodigo": fid,
                        "tipo": "ABASTECIMENTO",
                        "litros": float(getattr(a, "litros", 0) or 0),
                        "valor": float(getattr(a, "valorTotal", 0) or 0),
                        "upsell": 0.0,
                    }
                )
        except Exception as exc:
            logger.warning("employee_performance pista_cache: %s", exc)

        try:
            from src.services.cashier_audit_service import get_cashier_audit_service

            store = get_cashier_audit_service().get_store()
            for f in store.fechamentos or ():
                if emp is not None and int(f.postoCodigo or 0) != int(emp):
                    continue
                oid = int(f.operadorId or 0)
                if oid <= 0:
                    continue
                if oid not in employees:
                    employees[oid] = {
                        "funcionarioCodigo": oid,
                        "nome": f.operadorNome or f"Operador {oid}",
                        "funcao": "Operador Caixa",
                        "horas_trabalhadas": 8.0,
                    }
                else:
                    # operador também frentista — marca caixa na auditoria
                    pass
                status = "OK"
                if abs(f.saldo) >= 100:
                    status = "CRITICO"
                elif abs(f.saldo) >= 20:
                    status = "ATENCAO"
                cash.append(
                    {
                        "funcionarioCodigo": oid,
                        "turno": f.turno or "",
                        "pdvCodigo": 0,
                        "caixaCodigo": int(f.caixaCodigo or 0),
                        "datahora": f.dataRef or "",
                        "diferenca": float(f.saldo or 0),
                        "status": status,
                    }
                )
        except Exception as exc:
            logger.warning("employee_performance cashier_audit: %s", exc)

        return sales, cash, list(employees.values())

    def _build_summary(
        self,
        sales: List[Dict[str, Any]],
        cash: List[Dict[str, Any]],
        employees: List[Dict[str, Any]],
    ) -> EmployeePerformanceSummary:
        by_employee: Dict[int, Dict[str, Any]] = defaultdict(
            lambda: {"litros": 0.0, "valor": 0.0, "upsell": 0.0, "count": 0}
        )
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
            horas = float(emp.get("horas_trabalhadas", 1) or 1)
            agg = by_employee[code]
            litros = agg["litros"]
            valor = agg["valor"]
            count = agg["count"] or 1
            ticket = valor / count if count > 0 else 0.0
            conversion = (agg["upsell"] / valor * 100) if valor > 0 else 0.0
            galonagem_hora = litros / horas if horas > 0 else 0.0
            score = min(
                100.0,
                round((galonagem_hora * 0.5) + (ticket * 0.03) + (conversion * 0.2), 2),
            )

            if funcao in ("Frentista", "Operador", "Operador Caixa") and (
                litros > 0 or valor > 0
            ):
                ranking.append(
                    EmployeeRanking(
                        funcionario_codigo=code,
                        nome=nome,
                        funcao=funcao,
                        litros_vendidos=round(litros, 2),
                        ticket_medio=round(ticket, 2),
                        conversion_pct=round(conversion, 2),
                        galonagem_por_hora=round(galonagem_hora, 2),
                        score=score,
                    )
                )

        ranking.sort(key=lambda x: x.score, reverse=True)
        auditoria = [
            CashBreakByEmployee(
                funcionario_codigo=int(c.get("funcionarioCodigo", 0)),
                nome=next(
                    (
                        e.get("nome")
                        for e in employees
                        if int(e.get("funcionarioCodigo", 0))
                        == int(c.get("funcionarioCodigo", 0))
                    ),
                    "Desconhecido",
                ),
                turno=c.get("turno", ""),
                pdv_codigo=int(c.get("pdvCodigo", 0)),
                caixa_codigo=int(c.get("caixaCodigo", 0)),
                datahora=c.get("datahora", ""),
                diferenca=float(c.get("diferenca", 0)),
                status=c.get("status", "OK"),
            )
            for c in cash
        ]

        media = (
            round(sum(r.galonagem_por_hora for r in ranking) / len(ranking), 2)
            if ranking
            else 0.0
        )

        return EmployeePerformanceSummary(
            ranking=ranking,
            auditoria_caixa=auditoria,
            media_galonagem_por_hora=media,
            melhor_frentista=ranking[0] if ranking else None,
            pior_frentista=ranking[-1] if ranking else None,
        )
