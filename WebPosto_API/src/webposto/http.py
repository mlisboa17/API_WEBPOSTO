"""
Camada HTTP base com retry, logging e tratamento de erros.
"""

import logging
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import WebPostoConfig
from .exceptions import (
    AuthError,
    BadRequestError,
    ConnectionError,
    NotFoundError,
    ServerError,
    TimeoutError,
    WebPostoError,
)

logger = logging.getLogger(__name__)


class HTTPClient:
    """
    Cliente HTTP com retry automático, logging estruturado e tratamento de erros.
    """

    def __init__(self, config: WebPostoConfig):
        self.config = config
        self._session = self._build_session()

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "WebPosto-Python-Client/1.0.0",
            }
        )
        return session

    def _build_params(self, extra_params: Optional[Dict] = None) -> Dict:
        """Adiciona a CHAVE em todos os requests."""
        params = {"CHAVE": self.config.chave}
        if extra_params:
            # Remove None values
            params.update({k: v for k, v in extra_params.items() if v is not None})
        return params

    def _handle_response(self, response: requests.Response) -> Any:
        """Trata a resposta e lança exceção adequada em caso de erro."""
        logger.debug(
            "Response: method=%s url=%s status=%d latency=%.3fs",
            response.request.method,
            response.url,
            response.status_code,
            response.elapsed.total_seconds(),
        )

        if response.status_code == 204:
            return None

        if response.status_code == 200 or response.status_code == 201:
            try:
                return response.json()
            except Exception:
                return response.text

        body = response.text
        if response.status_code == 400:
            raise BadRequestError(f"Requisição inválida: {body}", 400, body)
        elif response.status_code in (401, 403):
            raise AuthError(
                "Chave de integração inválida ou sem permissão. "
                "Verifique WEBPOSTO_CHAVE e o contrato com a Quality Automação.",
                response.status_code,
                body,
            )
        elif response.status_code == 404:
            raise NotFoundError(f"Recurso não encontrado: {response.url}", 404, body)
        elif response.status_code >= 500:
            raise ServerError(
                f"Erro no servidor WebPosto: {body}", response.status_code, body
            )
        else:
            raise WebPostoError(f"Erro inesperado: {body}", response.status_code, body)

    def get(self, path: str, params: Optional[Dict] = None) -> Any:
        url = f"{self.config.base_url}{path}"
        all_params = self._build_params(params)
        logger.info(
            "GET %s params=%s",
            path,
            {k: v for k, v in all_params.items() if k != "CHAVE"},
        )
        try:
            response = self._session.get(
                url,
                params=all_params,
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
            )
            return self._handle_response(response)
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Timeout após {self.config.timeout}s em GET {path}")
        except requests.exceptions.RetryError as e:
            raise ServerError(
                f"Erro no servidor WebPosto após tentativas: {e}",
                500,
                str(e),
            )
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Falha de conexão em GET {path}: {e}")

    def post(
        self, path: str, body: Optional[Dict] = None, params: Optional[Dict] = None
    ) -> Any:
        url = f"{self.config.base_url}{path}"
        all_params = self._build_params(params)
        logger.info("POST %s", path)
        try:
            response = self._session.post(
                url,
                json=body,
                params=all_params,
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
            )
            return self._handle_response(response)
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Timeout após {self.config.timeout}s em POST {path}")
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Falha de conexão em POST {path}: {e}")

    def put(
        self, path: str, body: Optional[Dict] = None, params: Optional[Dict] = None
    ) -> Any:
        url = f"{self.config.base_url}{path}"
        all_params = self._build_params(params)
        logger.info("PUT %s", path)
        try:
            response = self._session.put(
                url,
                json=body,
                params=all_params,
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
            )
            return self._handle_response(response)
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Timeout após {self.config.timeout}s em PUT {path}")
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Falha de conexão em PUT {path}: {e}")

    def patch(
        self, path: str, body: Optional[Dict] = None, params: Optional[Dict] = None
    ) -> Any:
        url = f"{self.config.base_url}{path}"
        all_params = self._build_params(params)
        logger.info("PATCH %s", path)
        try:
            response = self._session.patch(
                url,
                json=body,
                params=all_params,
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
            )
            return self._handle_response(response)
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Timeout após {self.config.timeout}s em PATCH {path}")
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Falha de conexão em PATCH {path}: {e}")

    def delete(self, path: str, params: Optional[Dict] = None) -> Any:
        url = f"{self.config.base_url}{path}"
        all_params = self._build_params(params)
        logger.info("DELETE %s", path)
        try:
            response = self._session.delete(
                url,
                params=all_params,
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
            )
            return self._handle_response(response)
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Timeout após {self.config.timeout}s em DELETE {path}")
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Falha de conexão em DELETE {path}: {e}")
