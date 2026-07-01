"""
Business Analyst API Routes
Rotas FastAPI para relatórios executivos e análises
"""

from __future__ import annotations

from datetime import date
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.services.business_analyst.business_analyst_service import BusinessAnalystService

router = APIRouter(prefix="/v1/business-analyst", tags=["Business Analyst"])

# Instância do serviço
_analyst_service = BusinessAnalystService()


@router.get("/daily")
async def get_daily_report(
    tenant: str | None = Query(None, description="Nome do tenant (opcional)"),
    report_date: str | None = Query(None, description="Data do relatório (YYYY-MM-DD, padrão: hoje)"),
) -> JSONResponse:
    """
    Relatório Executivo Diário
    
    Retorna:
    - Business Health Score
    - Resumo executivo
    - Receita e despesas do dia
    - Alertas críticos
    - Riscos identificados
    - Oportunidades
    - Ações recomendadas
    """
    try:
        tenant_name = tenant or "DEFAULT"
        target_date = date.fromisoformat(report_date) if report_date else None
        
        report = await _analyst_service.generate_daily_report(tenant_name, target_date)
        return JSONResponse(content=report.to_dict(), status_code=200)
    
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": {
                    "type": "REPORT_GENERATION_ERROR",
                    "message": f"Erro ao gerar relatório diário: {str(e)[:200]}",
                },
            },
            status_code=500,
        )


@router.get("/weekly")
async def get_weekly_report(
    tenant: str | None = Query(None, description="Nome do tenant (opcional)"),
    week_start: str | None = Query(None, description="Início da semana (YYYY-MM-DD)"),
    week_end: str | None = Query(None, description="Fim da semana (YYYY-MM-DD)"),
) -> JSONResponse:
    """
    Relatório Executivo Semanal
    
    Retorna:
    - Business Health Score semanal
    - O que melhorou vs semana anterior
    - O que piorou vs semana anterior
    - Riscos da semana
    - Oportunidades
    - Previsão para próxima semana
    - Ações recomendadas
    """
    try:
        tenant_name = tenant or "DEFAULT"
        
        # TODO: Implementar lógica de weekly report
        # Por ora, retorna estrutura básica
        return JSONResponse(
            content={
                "success": True,
                "tenant": tenant_name,
                "period_start": week_start or date.today().isoformat(),
                "period_end": week_end or date.today().isoformat(),
                "message": "Weekly report - em implementação",
            },
            status_code=200,
        )
    
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": {
                    "type": "REPORT_GENERATION_ERROR",
                    "message": f"Erro ao gerar relatório semanal: {str(e)[:200]}",
                },
            },
            status_code=500,
        )


@router.get("/health-score")
async def get_health_score(
    tenant: str | None = Query(None, description="Nome do tenant (opcional)"),
    report_date: str | None = Query(None, description="Data de referência (YYYY-MM-DD)"),
) -> JSONResponse:
    """
    Business Health Score
    
    Retorna apenas o score de saúde do negócio (0-100) com classificação.
    """
    try:
        tenant_name = tenant or "DEFAULT"
        target_date = date.fromisoformat(report_date) if report_date else date.today()
        
        # Gerar report completo e extrair apenas health score
        report = await _analyst_service.generate_daily_report(tenant_name, target_date)
        
        return JSONResponse(
            content={
                "success": True,
                **report.health_score.to_dict(),
            },
            status_code=200,
        )
    
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": {
                    "type": "SCORE_CALCULATION_ERROR",
                    "message": f"Erro ao calcular health score: {str(e)[:200]}",
                },
            },
            status_code=500,
        )


@router.get("/payloads")
async def get_report_payloads(
    tenant: str | None = Query(None, description="Nome do tenant (opcional)"),
    report_type: str = Query("daily", description="Tipo de relatório: daily ou weekly"),
    report_date: str | None = Query(None, description="Data do relatório (YYYY-MM-DD)"),
) -> JSONResponse:
    """
    Payloads de Relatórios
    
    Gera payloads formatados para:
    - Telegram (Markdown)
    - Discord (Embed JSON)
    - Email (HTML)
    
    NÃO envia os relatórios, apenas gera os payloads prontos.
    """
    try:
        tenant_name = tenant or "DEFAULT"
        target_date = date.fromisoformat(report_date) if report_date else date.today()
        
        # Gerar report
        report = await _analyst_service.generate_daily_report(tenant_name, target_date)
        
        # TODO: Implementar payload builders
        # Por ora, estrutura básica
        
        telegram_text = f"""
*LOGOS Business Report - {tenant_name}*
📅 {report.period}

🎯 *Health Score:* {report.health_score.overall_score:.1f}/100 ({report.health_score.classification})

📊 *Resumo:*
{report.summary}

💰 *Financeiro:*
• Receita: R$ {report.revenue_today:,.2f}
• Despesas: R$ {report.expenses_today:,.2f}
• Fluxo: R$ {report.cash_flow_today:,.2f}

⚠️ *Alertas Críticos:* {len(report.critical_alerts)}
🔴 *Riscos:* {len(report.risks)}
🟢 *Oportunidades:* {len(report.opportunities)}
"""
        
        discord_embed = {
            "title": f"📊 LOGOS Business Report - {tenant_name}",
            "description": report.summary,
            "color": 0x00ff00 if report.health_score.overall_score >= 80 else 0xff9900 if report.health_score.overall_score >= 60 else 0xff0000,
            "fields": [
                {
                    "name": "Health Score",
                    "value": f"{report.health_score.overall_score:.1f}/100 ({report.health_score.classification})",
                    "inline": True,
                },
                {
                    "name": "Receita",
                    "value": f"R$ {report.revenue_today:,.2f}",
                    "inline": True,
                },
                {
                    "name": "Fluxo de Caixa",
                    "value": f"R$ {report.cash_flow_today:,.2f}",
                    "inline": True,
                },
            ],
            "footer": {
                "text": f"LOGOS • {report.generated_at}",
            },
        }
        
        email_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
        .header {{ background: #1a1a1a; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .score {{ font-size: 48px; font-weight: bold; color: #00aa00; }}
        .metric {{ margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>LOGOS Business Report</h1>
        <p>{tenant_name} • {report.period}</p>
    </div>
    <div class="content">
        <div class="score">{report.health_score.overall_score:.1f}/100</div>
        <p><strong>Classificação:</strong> {report.health_score.classification}</p>
        
        <h2>Resumo</h2>
        <p>{report.summary}</p>
        
        <h2>Financeiro</h2>
        <div class="metric">Receita: R$ {report.revenue_today:,.2f}</div>
        <div class="metric">Despesas: R$ {report.expenses_today:,.2f}</div>
        <div class="metric">Fluxo de Caixa: R$ {report.cash_flow_today:,.2f}</div>
        
        <h2>Análise</h2>
        <p>Alertas Críticos: {len(report.critical_alerts)}</p>
        <p>Riscos Identificados: {len(report.risks)}</p>
        <p>Oportunidades: {len(report.opportunities)}</p>
    </div>
</body>
</html>
"""
        
        return JSONResponse(
            content={
                "success": True,
                "payloads": {
                    "telegram": {
                        "format": "markdown",
                        "content": telegram_text.strip(),
                    },
                    "discord": {
                        "format": "embed",
                        "content": discord_embed,
                    },
                    "email": {
                        "format": "html",
                        "content": email_html.strip(),
                    },
                },
            },
            status_code=200,
        )
    
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": {
                    "type": "PAYLOAD_GENERATION_ERROR",
                    "message": f"Erro ao gerar payloads: {str(e)[:200]}",
                },
            },
            status_code=500,
        )
