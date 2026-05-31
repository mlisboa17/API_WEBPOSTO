"""
Caso de uso: reconciliação de caixa por sub-centro (Pista / Loja / Food).
Divergencia = CaixaApurado - CaixaApresentado
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from src.application.caching.audit_cache import audit_cache_key, get_or_reconcile
from src.domain.entities.audit import AuditSession, SubCentroCusto, calcular_faturamento_periodo
from src.domain.gateways.audit_gateway import AuditGateway

logger = logging.getLogger(__name__)

TOLERANCIA_DIVERGENCIA = Decimal("50.00")


class ReconcileAuditUseCase:
    def __init__(self, posto_gateway: AuditGateway) -> None:
        self.posto_gateway = posto_gateway

    async def execute(
        self,
        start_date: date,
        end_date: date,
        sub_centro: str | SubCentroCusto,
        *,
        posto_id: str = "default",
        job_id: str | None = None,
        filial: list[int] | None = None,
        use_cache: bool = True,
    ) -> AuditSession:
        sc = (
            sub_centro
            if isinstance(sub_centro, SubCentroCusto)
            else SubCentroCusto.from_legacy(sub_centro)
        )
        cache_key = audit_cache_key(posto_id, sc.value, start_date.isoformat(), end_date.isoformat())

        async def _run() -> AuditSession:
            raw = await self.posto_gateway.fetch_transactions(
                start_date, end_date, sc, posto_id=posto_id, filial=filial
            )

            if raw.turnos:
                total_apurado = sum(t.valor_caixa for t in raw.turnos)
                total_apresentado = sum(t.valor_sistema for t in raw.turnos)
            else:
                total_apurado = raw.caixa_apurado_total
                total_apresentado = raw.caixa_apresentado_total

            divergencia = (total_apurado - total_apresentado).quantize(Decimal("0.01"))

            faturamento = raw.faturamento_periodo or calcular_faturamento_periodo(sc, raw.vendas)

            if sc == SubCentroCusto.PISTA:
                litros = sum((v.litros for v in raw.vendas), Decimal("0")).quantize(Decimal("0.01"))
            else:
                litros = Decimal("0.00")

            despesas = sum((d.valor for d in raw.despesas), Decimal("0")).quantize(Decimal("0.01"))

            alerta = abs(divergencia) > TOLERANCIA_DIVERGENCIA
            msg = None
            if alerta:
                msg = (
                    f"Divergência {divergencia} acima da tolerância {TOLERANCIA_DIVERGENCIA} "
                    f"— sub-centro {sc.value}"
                )
                logger.critical("AUDIT_DIVERGENCIA_CRITICA %s", msg)

            return AuditSession(
                job_id=job_id,
                posto_id=posto_id,
                sub_centro=sc,
                data_inicio=start_date,
                data_fim=end_date,
                galonagem_litros=litros,
                faturamento_periodo=faturamento,
                moeda="BRL",
                valor_apurado=total_apurado,
                valor_apresentado=total_apresentado,
                divergencia=divergencia,
                despesas_periodo=despesas,
                turnos_totais=len(raw.turnos),
                alerta_critico=alerta,
                mensagem_alerta=msg,
                cache_hit=False,
            )

        if use_cache:
            return await get_or_reconcile(cache_key, _run)
        return await _run()
