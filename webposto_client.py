"""
Cliente HTTP unificado para API WebPosto (paths /v1/...).
Pool de conexões: AsyncClient persistente (open/close no ciclo de vida da app).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Type, TypeVar

import httpx

from config import webposto
from models import (
    FechamentoCaixaResponse,
    MovimentacaoEspecie as MovimentacaoEspecieFinanceira,
)
from models_auditoria import (
    CategoriaDesapesa,
    DespesaCaixa,
    EspecieFinanceira,
    FechamentoCaixa,
    MovimentacaoEspecie,
    StatusCaixa,
    StatusJustificativa,
    TipoCaixa,
)

logger = logging.getLogger(__name__)
T = TypeVar("T")


class WebPostoClient:
    """Cliente async httpx com conexão persistente e endpoints /v1."""

    def __init__(self) -> None:
        self._base = webposto.BASE_URL.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {webposto.BEARER_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self._timeout = httpx.Timeout(webposto.TIMEOUT_SECONDS)
        self._max_retries = webposto.MAX_RETRIES
        self._retry_delay = webposto.RETRY_DELAY
        self._client: Optional[httpx.AsyncClient] = None

    async def open(self) -> None:
        if self._client is not None:
            return
        self._client = httpx.AsyncClient(
            base_url=self._base,
            headers=self._headers,
            timeout=self._timeout,
        )
        logger.debug("WebPosto AsyncClient aberto (base_url=%s)", self._base)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.debug("WebPosto AsyncClient encerrado")

    async def __aenter__(self) -> WebPostoClient:
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    def _require_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError(
                "WebPostoClient não inicializado: chame await client.open() "
                "(ex.: no startup do FastAPI ou no início do script)."
            )
        return self._client

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[T]] = None,
    ) -> T | Dict[str, Any]:
        client = self._require_client()
        url_path = path if path.startswith("/") else f"/{path}"
        retry_count = 0

        while retry_count < self._max_retries:
            try:
                response = await client.request(
                    method,
                    url_path,
                    params=params,
                    json=json,
                )
                response.raise_for_status()
                data = response.json()

                if response_model is not None:
                    try:
                        return response_model(**data)
                    except Exception as e:
                        logger.error(
                            "Integração WebPosto: validação Pydantic falhou path=%s método=%s erro=%s corpo=%s",
                            url_path,
                            method,
                            e,
                            str(data)[:2000],
                        )
                        raise ValueError(f"Resposta inválida do WebPosto: {e}") from e

                return data

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                retry_count += 1
                logger.warning(
                    "Integração WebPosto: timeout/conexão path=%s tentativa=%s/%s erro=%s",
                    url_path,
                    retry_count,
                    self._max_retries,
                    e,
                )
                if retry_count < self._max_retries:
                    await asyncio.sleep(self._retry_delay)
                else:
                    raise ConnectionError(
                        f"Falha ao conectar WebPosto após {self._max_retries} tentativas: {e}"
                    ) from e

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    logger.warning(
                        "Integração WebPosto: rate limit 429 path=%s, aguardando retry",
                        url_path,
                    )
                    await asyncio.sleep(self._retry_delay * 2)
                    retry_count += 1
                    if retry_count >= self._max_retries:
                        logger.error(
                            "Integração WebPosto: HTTP %s path=%s corpo=%s",
                            e.response.status_code,
                            url_path,
                            (e.response.text or "")[:2000],
                        )
                        raise e
                    continue
                logger.error(
                    "Integração WebPosto: HTTP %s path=%s params=%s corpo_resposta=%s",
                    e.response.status_code,
                    url_path,
                    params,
                    (e.response.text or "")[:2000],
                )
                raise

        raise ConnectionError("Falha inesperada nas retentativas WebPosto")

    async def get_despesas(
        self, unidade_id: int, data_inicio: Optional[str] = None
    ) -> List[DespesaCaixa]:
        params: Dict[str, Any] = {"unidade_id": unidade_id}
        if data_inicio:
            params["data_inicio"] = data_inicio
            # Mesmo filtro que get_despesas_caixa_raw (API costuma aceitar `data`).
            params["data"] = data_inicio

        data = await self._request("GET", webposto.ENDPOINT_V1_DESPESAS, params=params)
        despesas: List[DespesaCaixa] = []
        for item in data.get("despesas", []):
            try:
                despesas.append(
                    DespesaCaixa(
                        id=str(item["id"]),
                        unidade_id=int(item["unidade_id"]),
                        caixa_tipo=TipoCaixa(item["caixa_tipo"]),
                        horario=_parse_dt(item["horario"]),
                        categoria=CategoriaDesapesa(item["categoria"]),
                        valor=item["valor"],
                        operador=item["operador"],
                        status_justificativa=StatusJustificativa(
                            item.get("status_justificativa", "pendente")
                        ),
                        tem_documento=item.get("tem_documento", False),
                        documento_anexo=item.get("documento_anexo"),
                    )
                )
            except Exception as e:
                logger.error(
                    "Integração WebPosto: erro ao mapear despesa id=%s item=%s erro=%s",
                    item.get("id"),
                    item,
                    e,
                )
        return despesas

    async def get_fechamentos(
        self, unidade_id: int, data: Optional[str] = None
    ) -> List[FechamentoCaixa]:
        params: Dict[str, Any] = {"unidade_id": unidade_id}
        if data:
            params["data"] = data

        data_response = await self._request(
            "GET", webposto.ENDPOINT_V1_FECHAMENTOS, params=params
        )
        fechamentos: List[FechamentoCaixa] = []
        for item in data_response.get("fechamentos", []):
            try:
                movimentacoes = []
                for mov in item.get("movimentacoes", []):
                    movimentacoes.append(
                        MovimentacaoEspecie(
                            especie=EspecieFinanceira(mov["especie"]),
                            valor_esperado=mov["valor_esperado"],
                            valor_informado=mov["valor_informado"],
                        )
                    )
                fechamentos.append(
                    FechamentoCaixa(
                        id=str(item["id"]),
                        unidade_id=int(item["unidade_id"]),
                        caixa_tipo=TipoCaixa(item["caixa_tipo"]),
                        horario_abertura=_parse_dt(item["horario_abertura"]),
                        horario_fechamento=_parse_dt(item["horario_fechamento"]),
                        faturamento_bruto=item.get("faturamento_bruto", 0),
                        despesas_caixa_total=item.get("despesas_caixa_total", 0),
                        movimentacoes=movimentacoes,
                        saldo_esperado_dinheiro=item.get("saldo_esperado_dinheiro", 0),
                        saldo_informado_dinheiro=item.get(
                            "saldo_informado_dinheiro", 0
                        ),
                        status=StatusCaixa(item.get("status", "aberto")),
                        operador_fechamento=item["operador_fechamento"],
                        despesas_sem_categoria=item.get("despesas_sem_categoria", 0),
                        despesas_sem_documento=item.get("despesas_sem_documento", 0),
                        flagged_auditoria=item.get("flagged_auditoria", False),
                        motivo_auditoria=item.get("motivo_auditoria"),
                    )
                )
            except Exception as e:
                logger.error(
                    "Integração WebPosto: erro ao mapear fechamento id=%s item=%s erro=%s",
                    item.get("id"),
                    item,
                    e,
                )
        return fechamentos

    async def registrar_despesa(self, despesa: DespesaCaixa) -> Dict[str, Any]:
        payload = despesa.model_dump(mode="json")
        if isinstance(payload.get("horario"), datetime):
            payload["horario"] = payload["horario"].isoformat()
        return await self._request("POST", webposto.ENDPOINT_V1_DESPESAS, json=payload)

    async def atualizar_fechamento_status(
        self, fechamento_id: str, novo_status: str
    ) -> Dict[str, Any]:
        path = f"{webposto.ENDPOINT_V1_FECHAMENTOS}/{fechamento_id}"
        payload = {"id": fechamento_id, "status": novo_status}
        return await self._request("PUT", path, json=payload)

    async def get_fechamento_caixa(
        self, unidade_id: int, data: Optional[date] = None
    ) -> FechamentoCaixaResponse:
        if not data:
            data = datetime.now().date()
        params = {"unidade_id": unidade_id, "data": data.isoformat()}
        return await self._request(
            "GET",
            webposto.ENDPOINT_V1_FECHAMENTO_CAIXA,
            params=params,
            response_model=FechamentoCaixaResponse,
        )

    async def get_despesas_caixa_raw(
        self,
        unidade_id: int,
        data: Optional[date] = None,
        status: str = "pendente",
    ) -> List[dict]:
        if not data:
            data = datetime.now().date()
        response = await self._request(
            "GET",
            webposto.ENDPOINT_V1_DESPESAS,
            params={
                "unidade_id": unidade_id,
                "data": data.isoformat(),
                "status": status,
            },
        )
        return response.get("despesas", [])

    async def get_movimentacao_especie(
        self, unidade_id: int, data: Optional[date] = None
    ) -> List[MovimentacaoEspecieFinanceira]:
        if not data:
            data = datetime.now().date()
        response = await self._request(
            "GET",
            webposto.ENDPOINT_V1_MOVIMENTACAO_ESPECIE,
            params={"unidade_id": unidade_id, "data": data.isoformat()},
        )
        movimentacoes: List[MovimentacaoEspecieFinanceira] = []
        for item in response.get("movimentacoes", []):
            diferenca = item["valor_sistematico"] - item["valor_informado"]
            percentual = (
                (diferenca / item["valor_sistematico"] * 100)
                if item["valor_sistematico"] > 0
                else 0
            )
            movimentacoes.append(
                MovimentacaoEspecieFinanceira(
                    modalidade=item["modalidade"],
                    valor_sistematico=item["valor_sistematico"],
                    valor_informado=item["valor_informado"],
                    diferenca=diferenca,
                    percentual_desvio=round(percentual, 2),
                )
            )
        return movimentacoes

    async def health_check(self) -> bool:
        try:
            await self._request("GET", webposto.ENDPOINT_V1_HEALTH)
            return True
        except Exception as e:
            logger.error(
                "Integração WebPosto: health_check falhou: %s", e, exc_info=True
            )
            return False


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise TypeError(f"horário inválido: {type(value)}")


webposto_client = WebPostoClient()


async def initialize_webposto_client() -> bool:
    await webposto_client.open()
    healthy = await webposto_client.health_check()
    if healthy:
        logger.info("WebPosto cliente inicializado e healthy")
    else:
        logger.error(
            "WebPosto health check falhou — a API Logos continuará sem integração saudável ao WebPosto"
        )
    return healthy
