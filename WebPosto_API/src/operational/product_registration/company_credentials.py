"""Guard de empresa para escrita no WebPosto.

O endpoint legado roteia a empresa exclusivamente pela CHAVE, entao usar a chave de
outra filial grava o produto na filial errada sem qualquer erro HTTP (incidente
2481344: gravado em 11495 quando o destino era 118508).

O mapeamento empresa -> variaveis de ambiente vem de `core.config`
(`OFFICIAL_COMPANY_CREDENTIAL_ALIASES`), que ja e a fonte oficial e nao admite
fallback generico. Aqui se acrescenta a prova por leitura: um produto sentinel cujo
vinculo em PRODUTO_EMPRESA precisa apontar para a empresa esperada.
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from typing import Any, Iterable, Protocol

from src.core.config import OFFICIAL_COMPANY_CREDENTIAL_ALIASES, resolve_company_api_key

logger = logging.getLogger(__name__)

BASE_URL = "https://web.qualityautomacao.com.br"


class CompanyCredentialError(RuntimeError):
    """Falha na resolucao ou na validacao da credencial da empresa."""


@dataclass(frozen=True)
class CompanySentinel:
    """Produto conhecido que prova o vinculo da credencial com a empresa."""

    produto_codigo: int
    ean: str
    referencia: str


# Sentinels confirmados por GET em 2026-08-14 (PRODUTO + PRODUTO_EMPRESA).
COMPANY_SENTINELS: dict[int, CompanySentinel] = {
    118508: CompanySentinel(produto_codigo=2481160, ean="7891000376928", referencia="005207"),
    11495: CompanySentinel(produto_codigo=2481344, ean="7891962076317", referencia="005208"),
}


def fingerprint(key: str) -> str:
    """Identificador estavel da credencial, seguro para log e relatorio."""
    return hashlib.sha256(key.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class ResolvedCredential:
    empresa_codigo: int
    variable_name: str
    key: str

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.key)

    def __repr__(self) -> str:  # evita vazar a chave em traceback/log
        return (
            f"ResolvedCredential(empresa={self.empresa_codigo}, "
            f"variable={self.variable_name!r}, fingerprint={self.fingerprint})"
        )


def resolve_credential(
    empresa_codigo: int,
    env: dict[str, str] | None = None,
) -> ResolvedCredential:
    """Resolve a credencial da empresa pelos aliases oficiais, sem fallback generico."""
    aliases = OFFICIAL_COMPANY_CREDENTIAL_ALIASES.get(int(empresa_codigo), ())
    if not aliases:
        raise CompanyCredentialError(
            f"Empresa {empresa_codigo} nao possui aliases declarados em "
            "OFFICIAL_COMPANY_CREDENTIAL_ALIASES"
        )

    source = dict(os.environ) if env is None else env
    for alias in aliases:
        value = (source.get(alias) or "").strip()
        if value:
            credential = ResolvedCredential(empresa_codigo, alias, value)
            logger.info(
                "Credencial resolvida: empresa=%s variavel=%s fingerprint=%s",
                empresa_codigo,
                alias,
                credential.fingerprint,
            )
            return credential

    # O resolvedor oficial tambem le o arquivo .env quando a variavel nao esta exportada.
    if env is None:
        value = (resolve_company_api_key(empresa_codigo) or "").strip()
        if value:
            return ResolvedCredential(empresa_codigo, aliases[0], value)

    raise CompanyCredentialError(
        f"Nenhuma credencial declarada para empresa {empresa_codigo} presente no ambiente. "
        f"Variaveis aceitas: {', '.join(aliases)}"
    )


class ProductReader(Protocol):
    """Leitura de catalogo e vinculos, permitindo injecao em teste."""

    def get_catalog(self, key: str, cursor: int, page_size: int) -> Iterable[dict[str, Any]]: ...

    def get_company_links(self, key: str, cursor: int, page_size: int) -> Iterable[dict[str, Any]]: ...


class HttpProductReader:
    """Leitor real, paginado pelo cursor `ultimoCodigo` do endpoint legado.

    A resposta legada e {"ultimoCodigo": int, "resultados": [...]}; ler `data.items`
    devolve vazio silenciosamente e foi o que mascarou o incidente 2481344.
    """

    def __init__(self, client: Any, base_url: str = BASE_URL) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")

    def _fetch(self, path: str, key: str, cursor: int, page_size: int) -> list[dict[str, Any]]:
        response = self._client.get(
            f"{self._base_url}{path}",
            params={"CHAVE": key, "ultimoCodigo": cursor, "tamanhoPagina": page_size},
        )
        if response.status_code != 200:
            raise CompanyCredentialError(f"GET {path} retornou HTTP {response.status_code}")
        payload = response.json()
        resultados = payload.get("resultados") if isinstance(payload, dict) else None
        return list(resultados or [])

    def get_catalog(self, key: str, cursor: int, page_size: int) -> list[dict[str, Any]]:
        return self._fetch("/INTEGRACAO/PRODUTO", key, cursor, page_size)

    def get_company_links(self, key: str, cursor: int, page_size: int) -> list[dict[str, Any]]:
        return self._fetch("/INTEGRACAO/PRODUTO_EMPRESA", key, cursor, page_size)


def _barcodes(item: dict[str, Any]) -> set[str]:
    found: set[str] = set()
    for entry in item.get("produtoCodigoBarra") or []:
        if isinstance(entry, dict) and entry.get("codigoBarra") is not None:
            found.add(str(entry["codigoBarra"]).strip())
    externo = item.get("produtoCodigoExterno")
    if externo:
        found.add(str(externo).strip())
    return found


@dataclass(frozen=True)
class GuardResult:
    empresa_codigo: int
    variable_name: str
    fingerprint: str
    sentinel_found: bool
    company_link_confirmed: bool
    details: dict[str, Any]

    @property
    def passed(self) -> bool:
        return self.sentinel_found and self.company_link_confirmed


def company_guard(
    credential: ResolvedCredential,
    reader: ProductReader,
    page_size: int = 50,
) -> GuardResult:
    """Confirma, apenas com leitura, que a credencial responde pela empresa esperada.

    Exige o sentinel no catalogo com referencia e EAN corretos e o vinculo
    PRODUTO_EMPRESA apontando para a empresa esperada.
    """
    sentinel = COMPANY_SENTINELS.get(credential.empresa_codigo)
    if sentinel is None:
        raise CompanyCredentialError(
            f"Empresa {credential.empresa_codigo} nao possui sentinel declarado; "
            "guard nao pode ser executado"
        )

    cursor = sentinel.produto_codigo - 1
    details: dict[str, Any] = {"sentinel": sentinel.produto_codigo}

    sentinel_found = False
    for item in reader.get_catalog(credential.key, cursor, page_size):
        if item.get("produtoCodigo") != sentinel.produto_codigo:
            continue
        referencia = str(item.get("referenciaCodigo") or "").strip()
        details["catalog"] = {
            "nome": item.get("nome"),
            "referenciaCodigo": referencia,
            "grupoCodigo": item.get("grupoCodigo"),
        }
        sentinel_found = referencia == sentinel.referencia and sentinel.ean in _barcodes(item)
        break

    company_link_confirmed = False
    for item in reader.get_company_links(credential.key, cursor, page_size):
        if item.get("produtoCodigo") != sentinel.produto_codigo:
            continue
        empresa = item.get("empresaCodigo")
        details["link"] = {"empresaCodigo": empresa, "precoVenda": item.get("precoVenda")}
        company_link_confirmed = empresa == credential.empresa_codigo
        break

    result = GuardResult(
        empresa_codigo=credential.empresa_codigo,
        variable_name=credential.variable_name,
        fingerprint=credential.fingerprint,
        sentinel_found=sentinel_found,
        company_link_confirmed=company_link_confirmed,
        details=details,
    )

    if not result.passed:
        logger.error(
            "COMPANY_CREDENTIAL_MISMATCH empresa=%s variavel=%s fingerprint=%s sentinel=%s link=%s",
            result.empresa_codigo,
            result.variable_name,
            result.fingerprint,
            result.sentinel_found,
            result.company_link_confirmed,
        )

    return result


def require_company_guard(
    empresa_codigo: int,
    reader: ProductReader,
    env: dict[str, str] | None = None,
) -> ResolvedCredential:
    """Resolve a credencial e bloqueia a escrita se o guard nao passar."""
    credential = resolve_credential(empresa_codigo, env=env)
    result = company_guard(credential, reader)
    if not result.passed:
        raise CompanyCredentialError(
            "COMPANY_CREDENTIAL_MISMATCH: credencial "
            f"{credential.variable_name} (fingerprint {credential.fingerprint}) nao comprovou "
            f"vinculo com empresa {empresa_codigo}. Escrita bloqueada."
        )
    return credential
