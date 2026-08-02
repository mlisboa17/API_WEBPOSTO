"""Rotas consolidadas do Cockpit Operacional — Sprint 48.

Namespace: /api/v1/operational/
Visão: Gerente de Pista/Loja
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from src.interfaces.http.authz import require_roles
from src.services.cash_break_service import CashBreakService, CashBreakSummary
from src.services.fuel_loss_service import FuelLossService
from src.services.convenience_analytics_service import ConvenienceAnalyticsService
from src.services.purchase_recommendation_service import PurchaseRecommendationService


router = APIRouter(
    prefix="/api/v1/operational",
    tags=["Operational Cockpit S48"],
)


@router.get("/cash-breaks")
async def operational_cash_breaks(
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: int | None = Query(None),
    turno: str | None = Query(None),
    operadorCodigo: int | None = Query(None),
    current_user: dict = Depends(require_roles("director", "admin", "manager", "supervisor")),
) -> dict:
    try:
        mock_closures = [
            {
                "caixaCodigo": 101,
                "empresaCodigo": empresaCodigo or 11495,
                "dataFechamento": dataInicial,
                "turno": "MANHA",
                "operadorCodigo": 501,
                "operadorNome": "João Silva",
                "valorEsperado": 5000.0,
                "valorInformado": 4985.0,
            },
            {
                "caixaCodigo": 102,
                "empresaCodigo": empresaCodigo or 11495,
                "dataFechamento": dataInicial,
                "turno": "TARDE",
                "operadorCodigo": 502,
                "operadorNome": "Maria Santos",
                "valorEsperado": 8000.0,
                "valorInformado": 7870.0,
            },
            {
                "caixaCodigo": 103,
                "empresaCodigo": empresaCodigo or 11495,
                "dataFechamento": dataFinal,
                "turno": "NOITE",
                "operadorCodigo": 503,
                "operadorNome": "Pedro Oliveira",
                "valorEsperado": 6500.0,
                "valorInformado": 6500.0,
            },
        ]

        if turno:
            mock_closures = [c for c in mock_closures if c["turno"] == turno.upper()]
        if operadorCodigo:
            mock_closures = [c for c in mock_closures if c["operadorCodigo"] == operadorCodigo]

        service = CashBreakService()
        summary = service.analyze_batch(mock_closures, dataInicial, dataFinal, empresaCodigo)

        return {
            "success": True,
            "data": summary.model_dump(),
            "namespace": "operational",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/cash-breaks/by-operator")
async def operational_cash_breaks_by_operator(
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: int | None = Query(None),
    current_user: dict = Depends(require_roles("director", "admin", "manager", "supervisor")),
) -> dict:
    try:
        service = CashBreakService()

        mock_closures = [
            {"caixaCodigo": 1, "empresaCodigo": empresaCodigo or 11495, "dataFechamento": dataInicial,
             "operadorCodigo": 501, "operadorNome": "João", "valorEsperado": 5000, "valorInformado": 4850},
            {"caixaCodigo": 2, "empresaCodigo": empresaCodigo or 11495, "dataFechamento": dataInicial,
             "operadorCodigo": 502, "operadorNome": "Maria", "valorEsperado": 6000, "valorInformado": 6000},
            {"caixaCodigo": 3, "empresaCodigo": empresaCodigo or 11495, "dataFechamento": dataFinal,
             "operadorCodigo": 501, "operadorNome": "João", "valorEsperado": 5500, "valorInformado": 5380},
        ]

        by_operator: dict[int, dict] = {}
        for closure in mock_closures:
            op_id = closure["operadorCodigo"]
            if op_id not in by_operator:
                by_operator[op_id] = {
                    "operador_codigo": op_id,
                    "operador_nome": closure["operadorNome"],
                    "fechamentos": 0,
                    "quebras_total": 0.0,
                    "quebras_absolutas": 0.0,
                }
            
            item = service.analyze_closure(**{k: v for k, v in closure.items()})
            by_operator[op_id]["fechamentos"] += 1
            by_operator[op_id]["quebras_total"] += item.diferenca
            by_operator[op_id]["quebras_absolutas"] += item.diferenca_absoluta

        operators = sorted(by_operator.values(), key=lambda x: -x["quebras_absolutas"])

        return {
            "success": True,
            "data": {
                "period": {"start": dataInicial, "end": dataFinal},
                "by_operator": operators,
            },
            "namespace": "operational",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/tanks/{tanqueCodigo}")
async def operational_tank_detail(
    tanqueCodigo: int,
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: int = Query(...),
    current_user: dict = Depends(require_roles("director", "admin", "manager", "supervisor")),
) -> dict:
    from src.services.lmc_intelligence_service import LmcIntelligenceService
    from datetime import datetime

    try:
        start_date = datetime.fromisoformat(dataInicial)
        end_date = datetime.fromisoformat(dataFinal)
        dias = (end_date - start_date).days + 1

        lmc_service = LmcIntelligenceService()
        lmc_response = await lmc_service.build(dataInicial, dataFinal, empresaCodigo)

        if not lmc_response.success:
            return {"success": False, "error": "Dados LMC indisponíveis"}

        lmc_records = lmc_response.data.get("factLmc") or []
        
        loss_service = FuelLossService()

        tank_aggregates: dict[int, dict] = {}
        for record in lmc_records:
            for tank in record.get("lmcTanque") or []:
                if not isinstance(tank, dict):
                    continue
                codigo = int(tank.get("tanqueCodigo") or tank.get("lmcTanqueCodigo") or 0)
                if codigo != tanqueCodigo:
                    continue
                
                if codigo not in tank_aggregates:
                    tank_aggregates[codigo] = {
                        "tanqueCodigo": codigo,
                        "empresaCodigo": empresaCodigo,
                        "combustivelTipo": tank.get("produtoDescricao"),
                        "estoqueInicial": 0.0,
                        "entradasNf": 0.0,
                        "saidasVendas": 0.0,
                        "estoqueMedido": 0.0,
                    }
                
                agg = tank_aggregates[codigo]
                agg["estoqueInicial"] = float(tank.get("estoqueInicial") or agg["estoqueInicial"])
                agg["entradasNf"] += float(tank.get("entradaLitros") or 0)
                agg["saidasVendas"] += float(tank.get("saidaLitros") or 0)
                agg["estoqueMedido"] = float(tank.get("estoqueFinal") or agg["estoqueMedido"])

        if not tank_aggregates:
            return {"success": False, "error": f"Tanque {tanqueCodigo} não encontrado"}

        tank_data = list(tank_aggregates.values())[0]
        
        reconciliation = loss_service.reconcile_tank(
            tanque_codigo=tank_data["tanqueCodigo"],
            empresa_codigo=tank_data["empresaCodigo"],
            estoque_inicial=tank_data["estoqueInicial"],
            entradas_nf=tank_data["entradasNf"],
            saidas_vendas=tank_data["saidasVendas"],
            estoque_medido=tank_data["estoqueMedido"],
            combustivel_tipo=tank_data["combustivelTipo"],
            dias_periodo=dias,
        )

        return {
            "success": True,
            "data": {
                "reconciliation": reconciliation.model_dump(),
                "dias_para_ruptura": reconciliation.dias_para_ruptura,
                "ruptura_iminente": reconciliation.ruptura_iminente,
                "venda_media_diaria": reconciliation.venda_media_diaria,
            },
            "namespace": "operational",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/tanks/rupture-risk")
async def operational_tanks_rupture_risk(
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: int | None = Query(None),
    limiteGiroDias: int = Query(5, ge=1, le=30),
    current_user: dict = Depends(require_roles("director", "admin", "manager", "supervisor")),
) -> dict:
    from src.services.lmc_intelligence_service import LmcIntelligenceService
    from datetime import datetime

    try:
        start_date = datetime.fromisoformat(dataInicial)
        end_date = datetime.fromisoformat(dataFinal)
        dias = (end_date - start_date).days + 1

        lmc_service = LmcIntelligenceService()
        lmc_response = await lmc_service.build(dataInicial, dataFinal, empresaCodigo)

        if not lmc_response.success:
            return {"success": False, "error": "Dados LMC indisponíveis"}

        lmc_records = lmc_response.data.get("factLmc") or []
        loss_service = FuelLossService()
        summary = loss_service.extract_from_lmc_data(lmc_records, dataInicial, dataFinal)

        at_risk = []
        for recon in summary.reconciliations:
            if recon.dias_para_ruptura is not None and recon.dias_para_ruptura <= limiteGiroDias:
                at_risk.append({
                    "tanque_codigo": recon.tanque_codigo,
                    "empresa_codigo": recon.empresa_codigo,
                    "combustivel": recon.combustivel_tipo,
                    "estoque_medido": recon.estoque_medido,
                    "venda_media_diaria": recon.venda_media_diaria,
                    "dias_para_ruptura": recon.dias_para_ruptura,
                    "ruptura_iminente": recon.ruptura_iminente,
                })

        at_risk.sort(key=lambda x: x["dias_para_ruptura"] or 999)

        return {
            "success": True,
            "data": {
                "period": {"start": dataInicial, "end": dataFinal},
                "limite_giro_dias": limiteGiroDias,
                "total_tanques": summary.total_tanques_analisados,
                "tanques_em_risco": len(at_risk),
                "items": at_risk,
            },
            "namespace": "operational",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/convenience/rupture")
async def operational_convenience_rupture(
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: int | None = Query(None),
    classificacaoAbc: str | None = Query(None),
    current_user: dict = Depends(require_roles("director", "admin", "manager", "supervisor")),
) -> dict:
    from src.services.non_fuel_product_sales_service import NonFuelProductSalesService

    try:
        nf_service = NonFuelProductSalesService()
        nf_response = await nf_service.build(dataInicial, dataFinal, empresaCodigo)

        if not nf_response.success:
            return {"success": False, "error": "Dados de conveniência indisponíveis"}

        products = nf_response.data.get("produtos") or []
        
        conv_service = ConvenienceAnalyticsService()
        abc_curve = conv_service.calculate_abc_curve(products, dataInicial, dataFinal, empresaCodigo)
        stock_breaks = conv_service.detect_stock_breaks(abc_curve, dataFinal)

        items = stock_breaks.items
        if classificacaoAbc:
            items = [i for i in items if i.classificacao_abc.value == classificacaoAbc.upper()]

        return {
            "success": True,
            "data": {
                "period": {"start": dataInicial, "end": dataFinal},
                "total_rupturas": len([i for i in items if i.status.value == "RUPTURA"]),
                "total_riscos": len([i for i in items if i.status.value in {"CRITICO", "BAIXO"}]),
                "perda_estimada_dia": sum(i.perda_estimada_dia or 0 for i in items),
                "items": [i.model_dump() for i in items[:20]],
            },
            "namespace": "operational",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/convenience/purchase-suggestions")
async def operational_purchase_suggestions(
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: int | None = Query(None),
    apenasUrgentes: bool = Query(False),
    current_user: dict = Depends(require_roles("director", "admin", "manager", "supervisor")),
) -> dict:
    from src.services.non_fuel_product_sales_service import NonFuelProductSalesService

    try:
        nf_service = NonFuelProductSalesService()
        nf_response = await nf_service.build(dataInicial, dataFinal, empresaCodigo)

        if not nf_response.success:
            return {"success": False, "error": "Dados de conveniência indisponíveis"}

        products = nf_response.data.get("produtos") or []
        
        conv_service = ConvenienceAnalyticsService()
        abc_curve = conv_service.calculate_abc_curve(products, dataInicial, dataFinal, empresaCodigo)

        purchase_service = PurchaseRecommendationService()
        
        product_data = []
        for p in abc_curve.produtos:
            product_data.append({
                "produtoCodigo": p.produto_codigo,
                "produtoNome": p.produto_nome,
                "estoqueAtual": p.estoque_atual,
                "vendaMediaDiaria": p.venda_media_diaria,
                "classificacaoAbc": p.classificacao.value,
                "empresaCodigo": p.empresa_codigo,
            })

        summary = purchase_service.recommend_batch(product_data, empresaCodigo)

        recommendations = summary.recommendations
        if apenasUrgentes:
            recommendations = [r for r in recommendations if r.urgencia.value in {"IMEDIATO", "URGENTE"}]

        return {
            "success": True,
            "data": {
                "period": {"start": dataInicial, "end": dataFinal},
                "total_recomendacoes": len(recommendations),
                "recomendacoes_urgentes": summary.recomendacoes_urgentes,
                "valor_total_estimado": summary.valor_total_estimado,
                "items": [r.model_dump() for r in recommendations[:30]],
            },
            "namespace": "operational",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/summary")
async def operational_summary(
    dataInicial: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    dataFinal: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    empresaCodigo: int | None = Query(None),
    current_user: dict = Depends(require_roles("director", "admin", "manager", "supervisor")),
) -> dict:
    try:
        cash_service = CashBreakService()
        mock_closures = [
            {"caixaCodigo": 1, "empresaCodigo": empresaCodigo or 11495, "dataFechamento": dataInicial,
             "valorEsperado": 5000, "valorInformado": 4920},
        ]
        cash_summary = cash_service.analyze_batch(mock_closures, dataInicial, dataFinal, empresaCodigo)

        return {
            "success": True,
            "data": {
                "period": {"start": dataInicial, "end": dataFinal},
                "empresa_codigo": empresaCodigo,
                "cash_breaks": {
                    "total_fechamentos": cash_summary.total_fechamentos,
                    "com_quebra": cash_summary.fechamentos_com_quebra,
                    "criticos": cash_summary.fechamentos_criticos,
                    "soma_quebras": cash_summary.soma_quebras_absoluta,
                    "status": cash_summary.overall_status.value,
                },
            },
            "namespace": "operational",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
