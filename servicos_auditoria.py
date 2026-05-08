"""
Serviços de Auditoria - Extração e estruturação de dados do WebPosto
FastAPI routes + lógica de negócio (sem fallback MOCK)
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

import httpx
from fastapi import FastAPI, HTTPException

from config import initialize_config, webposto
from models_auditoria import (
    DespesaCaixa,
    FechamentoCaixa,
    ListaFechamentos,
    ResumoAuditoriaUnidade,
    StatusCaixa,
)
from webposto_client import initialize_webposto_client, webposto_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n" + "=" * 60)
    print("Logos Auditoria - Iniciando...")
    print("=" * 60)

    strict = webposto.STRICT_STARTUP
    if strict:
        if not initialize_config():
            raise RuntimeError(
                "WEBPOSTO_STRICT_STARTUP=true: defina WEBPOSTO_BASE_URL e "
                "WEBPOSTO_BEARER_TOKEN válidos no .env."
            )
    else:
        if not initialize_config():
            logger.warning("Configuração WebPosto incompleta (STRICT desligado).")

    healthy = await initialize_webposto_client()
    if strict and not healthy:
        await webposto_client.close()
        raise RuntimeError(
            "WEBPOSTO_STRICT_STARTUP=true: health check do WebPosto falhou. "
            "Confirme URL, token e WEBPOSTO_V1_HEALTH (ou defina WEBPOSTO_STRICT_STARTUP=false só para dev)."
        )
    if not healthy:
        logger.error(
            "Health check do WebPosto falhou; API sobe mesmo assim porque STRICT_STARTUP=false."
        )

    print("=" * 60 + "\n")
    yield
    print("Logos Auditoria - Desligando...")
    await webposto_client.close()


app = FastAPI(title="Logos Auditoria API", version="1.0", lifespan=lifespan)


def _http_from_integration_exc(exc: Exception) -> HTTPException:
    if isinstance(exc, ConnectionError):
        logger.error("Integração WebPosto: conexão falhou: %s", exc, exc_info=True)
        return HTTPException(
            status_code=503,
            detail=f"WebPosto indisponível (conexão): {exc}",
        )
    if isinstance(exc, httpx.HTTPStatusError):
        body = (exc.response.text or "")[:2000]
        logger.error(
            "Integração WebPosto: HTTP %s url=%s corpo=%s",
            exc.response.status_code,
            exc.request.url,
            body,
        )
        return HTTPException(
            status_code=exc.response.status_code,
            detail=body or str(exc),
        )
    if isinstance(exc, ValueError):
        logger.error(
            "Integração WebPosto: validação/resposta inválida: %s", exc, exc_info=True
        )
        return HTTPException(status_code=502, detail=str(exc))
    logger.exception("Integração WebPosto: erro não mapeado")
    return HTTPException(status_code=502, detail=str(exc))


class AuditoriaService:
    """Serviço de auditoria: sempre consome WebPosto real (sem MOCK)."""

    @staticmethod
    async def extrair_despesas_por_unidade(
        unidade_id: int, data: Optional[datetime] = None
    ) -> List[DespesaCaixa]:
        try:
            return await webposto_client.get_despesas(
                unidade_id,
                data_inicio=data.isoformat() if data else None,
            )
        except Exception:
            logger.exception(
                "Integração WebPosto falhou ao obter despesas unidade_id=%s",
                unidade_id,
            )
            raise

    @staticmethod
    async def extrair_fechamentos(
        unidade_id: int, data: Optional[datetime] = None
    ) -> List[FechamentoCaixa]:
        try:
            return await webposto_client.get_fechamentos(
                unidade_id,
                data=data.isoformat() if data else None,
            )
        except Exception:
            logger.exception(
                "Integração WebPosto falhou ao obter fechamentos unidade_id=%s",
                unidade_id,
            )
            raise

    @staticmethod
    def calcular_resumo_unidade(
        fechamentos: List[FechamentoCaixa],
        despesas: List[DespesaCaixa],
        unidade_id: int,
    ) -> ResumoAuditoriaUnidade:
        faturamento_total = sum(f.faturamento_bruto for f in fechamentos)
        despesas_operacionais = sum(f.despesas_caixa_total for f in fechamentos)
        quebra_total = sum(f.quebra_caixa for f in fechamentos)

        caixas_fechados = len(
            [f for f in fechamentos if f.status == StatusCaixa.FECHADO]
        )
        caixas_abertos = len([f for f in fechamentos if f.status == StatusCaixa.ABERTO])
        caixas_auditoria = len(
            [f for f in fechamentos if f.status == StatusCaixa.EM_AUDITORIA]
        )

        despesas_sem_cat = sum(f.despesas_sem_categoria for f in fechamentos)
        despesas_sem_doc = sum(f.despesas_sem_documento for f in fechamentos)
        caixas_quebra_10 = len([f for f in fechamentos if f.quebra_caixa > 10])

        desvio_percentual = (
            ((despesas_operacionais / faturamento_total) - 0.05) * 100
            if faturamento_total > 0
            else 0
        )
        outlier = abs(desvio_percentual) > 10

        return ResumoAuditoriaUnidade(
            unidade_id=unidade_id,
            data=datetime.now(),
            faturamento_total=round(faturamento_total, 2),
            despesas_operacionais=round(despesas_operacionais, 2),
            saldo_especie_total=round(
                sum(f.saldo_informado_dinheiro for f in fechamentos), 2
            ),
            quebra_total=round(quebra_total, 2),
            quebra_percentual=(
                round((quebra_total / faturamento_total) * 100, 2)
                if faturamento_total > 0
                else 0
            ),
            caixas_fechados=caixas_fechados,
            caixas_abertos=caixas_abertos,
            caixas_em_auditoria=caixas_auditoria,
            despesas_sem_categoria_total=despesas_sem_cat,
            despesas_sem_documento_total=despesas_sem_doc,
            caixas_com_quebra_acima_10=caixas_quebra_10,
            desvio_percentual_media_despesas=round(desvio_percentual, 2),
            outlier_unidade=outlier,
        )


def _parse_data_opcional(data: Optional[str]) -> Optional[datetime]:
    if not data:
        return None
    try:
        return datetime.fromisoformat(data.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Data inválida: {data}")


@app.get("/auditoria/despesas/{unidade_id}", response_model=List[DespesaCaixa])
async def get_despesas_unidade(unidade_id: int, data: Optional[str] = None):
    """GET despesas estruturadas de uma unidade (unidade_id numérico)."""
    try:
        dt = _parse_data_opcional(data)
        despesas = await AuditoriaService.extrair_despesas_por_unidade(unidade_id, dt)
    except HTTPException:
        raise
    except Exception as e:
        raise _http_from_integration_exc(e) from e

    return despesas


@app.get("/auditoria/fechamentos/{unidade_id}", response_model=ListaFechamentos)
async def get_fechamentos_unidade(unidade_id: int, data: Optional[str] = None):
    """GET fechamentos estruturados com resumo consolidado."""
    try:
        dt = _parse_data_opcional(data)
        fechamentos = await AuditoriaService.extrair_fechamentos(unidade_id, dt)
        despesas = await AuditoriaService.extrair_despesas_por_unidade(unidade_id, dt)
    except HTTPException:
        raise
    except Exception as e:
        raise _http_from_integration_exc(e) from e

    resumo = AuditoriaService.calcular_resumo_unidade(fechamentos, despesas, unidade_id)
    return ListaFechamentos(
        unidade_id=unidade_id,
        data=datetime.now(),
        fechamentos=fechamentos,
        total_caixas=len(fechamentos),
        resumo=resumo,
    )


@app.get("/auditoria/resumo/{unidade_id}", response_model=ResumoAuditoriaUnidade)
async def get_resumo_auditoria(unidade_id: int, data: Optional[str] = None):
    """GET resumo executivo de auditoria (KPIs)."""
    try:
        dt = _parse_data_opcional(data)
        fechamentos = await AuditoriaService.extrair_fechamentos(unidade_id, dt)
        despesas = await AuditoriaService.extrair_despesas_por_unidade(unidade_id, dt)
    except HTTPException:
        raise
    except Exception as e:
        raise _http_from_integration_exc(e) from e

    return AuditoriaService.calcular_resumo_unidade(fechamentos, despesas, unidade_id)


@app.get("/auditoria/despesas-por-categoria/{unidade_id}")
async def get_despesas_categorizado(unidade_id: int, data: Optional[str] = None):
    """GET despesas agrupadas por categoria."""
    try:
        dt = _parse_data_opcional(data)
        despesas = await AuditoriaService.extrair_despesas_por_unidade(unidade_id, dt)
    except HTTPException:
        raise
    except Exception as e:
        raise _http_from_integration_exc(e) from e

    resultado = {}
    for despesa in despesas:
        cat = despesa.categoria.value
        if cat not in resultado:
            resultado[cat] = {"total": 0, "qtd": 0, "sem_documento": 0}
        resultado[cat]["total"] += despesa.valor
        resultado[cat]["qtd"] += 1
        if not despesa.tem_documento:
            resultado[cat]["sem_documento"] += 1

    return resultado


@app.post("/auditoria/registrar-despesa", response_model=DespesaCaixa)
async def registrar_despesa(despesa: DespesaCaixa):
    """POST nova despesa no WebPosto."""
    try:
        await webposto_client.registrar_despesa(despesa)
    except Exception as e:
        raise _http_from_integration_exc(e) from e
    return despesa


@app.get("/auditoria/health")
async def health():
    """Health check do serviço Logos (não confunde com health do WebPosto upstream)."""
    return {"status": "ok", "service": "Logos Auditoria", "version": "1.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
