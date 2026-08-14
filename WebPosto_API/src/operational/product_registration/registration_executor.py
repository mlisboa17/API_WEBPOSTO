"""Executor de POST controlado com retry, timeout, checkpoint — FASE 7."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class RegistrationExecutor:
    """
    Executa POST /INTEGRACAO/INCLUIR_PRODUTO com:
    - Timeout 120s
    - Uma tentativa por body_hash
    - Tratamento de RET codes
    - Logging detalhado (sem credenciais)
    """

    def __init__(
        self,
        base_url: str = "https://web.qualityautomacao.com.br",
        chave: str | None = None,
        timeout: int = 120,
        max_retries: int = 1,
    ):
        self.base_url = base_url.rstrip("/")
        self.chave = chave
        self.timeout = timeout
        self.max_retries = max_retries
        self.executed_hashes: set[str] = set()

    def should_retry(self, http_status: int) -> bool:
        """Determina se deve fazer retry com backoff."""
        return http_status in (429, 503)

    def handle_ret_code(self, ret: str, http_status: int) -> dict[str, Any]:
        """
        Analisa RET code e HTTP status.
        
        Retorna dicionário com:
        - should_pause: bool (pausar execução)
        - should_continue: bool (continuar com próximos)
        - final_status: ProductStatus
        """
        ret_int = int(ret) if ret and ret.isdigit() else -1

        if http_status in (200, 201):
            if ret_int == 0:
                return {
                    "should_pause": False,
                    "should_continue": True,
                    "final_status": "CREATED_AND_VERIFIED",  # será verificado por GET
                    "reason": "HTTP 200/201 com RET=0",
                }
            elif ret_int == 3:
                return {
                    "should_pause": True,
                    "should_continue": False,
                    "final_status": "REJECTED",
                    "reason": "HTTP 200 mas RET=3 (modelo/categoria rejeitado)",
                }
            else:
                return {
                    "should_pause": False,
                    "should_continue": True,
                    "final_status": "RESULT_UNKNOWN",
                    "reason": f"HTTP 200 mas RET={ret_int} inesperado",
                }

        if http_status == 203:
            # Não Standard
            return {
                "should_pause": True,
                "should_continue": False,
                "final_status": "REJECTED",
                "reason": "HTTP 203 (não padrão)",
            }

        if http_status == 404:
            return {
                "should_pause": True,
                "should_continue": False,
                "final_status": "RESULT_UNKNOWN",
                "reason": "HTTP 404 (endpoint não encontrado)",
            }

        if http_status in (401, 403):
            return {
                "should_pause": True,
                "should_continue": False,
                "final_status": "RESULT_UNKNOWN",
                "reason": f"HTTP {http_status} (autenticação/autorização)",
            }

        if http_status in (429, 503):
            return {
                "should_pause": False,
                "should_continue": False,
                "final_status": "RESULT_UNKNOWN",
                "reason": f"HTTP {http_status} (throttle/serviço indisponível)",
            }

        return {
            "should_pause": False,
            "should_continue": False,
            "final_status": "RESULT_UNKNOWN",
            "reason": f"HTTP {http_status} (erro desconhecido)",
        }

    async def execute_post(
        self,
        body: dict[str, Any],
        body_hash: str,
        ean: str,
        client: httpx.AsyncClient | None = None,
    ) -> dict[str, Any]:
        """
        Executa POST /INTEGRACAO/INCLUIR_PRODUTO.
        
        Retorna {
            http_status: int,
            ret: str | None,
            men: str | None,
            cod_produto: int | None,
            executed: bool,
            error: str | None,
        }
        """
        
        # Verificar idempotência
        if body_hash in self.executed_hashes:
            logger.info(f"[SKIP] EAN {ean}: body_hash {body_hash[:8]}... já executado")
            return {
                "http_status": None,
                "ret": None,
                "men": None,
                "cod_produto": None,
                "executed": False,
                "error": "IDEMPOTENCE_CHECK",
            }

        endpoint = f"{self.base_url}/INTEGRACAO/INCLUIR_PRODUTO"
        params = {}
        if self.chave:
            params["CHAVE"] = self.chave

        headers = {"Content-Type": "application/json"}

        attempt = 0
        last_error = None

        while attempt < self.max_retries:
            attempt += 1
            try:
                if client is None:
                    async with httpx.AsyncClient(timeout=self.timeout) as _client:
                        response = await _client.post(
                            endpoint,
                            params=params,
                            json=body,
                            headers=headers,
                        )
                else:
                    response = await client.post(
                        endpoint,
                        params=params,
                        json=body,
                        headers=headers,
                    )

                # Registrar tentativa (sem credenciais)
                log_body = {k: v for k, v in body.items() if k not in ("senha", "token")}
                logger.info(
                    f"[POST] EAN {ean} (tentativa {attempt}): "
                    f"HTTP {response.status_code}, "
                    f"body_hash {body_hash[:8]}..., "
                    f"endpoint /{'/'.join(endpoint.split('/')[-2:])}"
                )

                # Parsear resposta
                result: dict[str, Any] = {
                    "http_status": response.status_code,
                    "ret": None,
                    "men": None,
                    "cod_produto": None,
                    "executed": True,
                    "error": None,
                }

                try:
                    resp_json = response.json()
                    result["ret"] = str(resp_json.get("ret", ""))
                    result["men"] = resp_json.get("men", "")
                    result["cod_produto"] = resp_json.get("codProduto")
                    
                    logger.info(
                        f"[RESPONSE] EAN {ean}: "
                        f"RET={result['ret']}, MEN={result['men'][:50] if result['men'] else 'N/A'}"
                    )
                except Exception as parse_err:
                    logger.warning(f"[PARSE_ERROR] EAN {ean}: {parse_err}")
                    result["men"] = f"Erro ao parsear resposta: {parse_err}"

                self.executed_hashes.add(body_hash)
                return result

            except asyncio.TimeoutError as e:
                last_error = f"Timeout após {self.timeout}s"
                logger.warning(f"[TIMEOUT] EAN {ean} (tentativa {attempt}): {last_error}")
                if attempt < self.max_retries and self.should_retry(408):
                    await asyncio.sleep(5 * attempt)  # Backoff
                    continue
                break

            except httpx.RequestError as e:
                last_error = str(e)
                logger.error(f"[REQUEST_ERROR] EAN {ean} (tentativa {attempt}): {last_error}")
                if attempt < self.max_retries:
                    await asyncio.sleep(5 * attempt)
                    continue
                break

        return {
            "http_status": None,
            "ret": None,
            "men": None,
            "cod_produto": None,
            "executed": False,
            "error": last_error or "Falha na execução",
        }
