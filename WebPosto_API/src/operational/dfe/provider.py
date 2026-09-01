"""Abstração DFeDistributionProvider — nenhum consumidor importa PyNFe diretamente."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CertificateValidationResult:
    ok: bool
    status: str
    serial_number: str | None = None
    issuer: str | None = None
    subject: str | None = None
    extracted_cnpj: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    fingerprint_sha256: str | None = None
    days_to_expiry: int | None = None
    has_private_key: bool = False
    client_auth: bool | None = None
    chain_ok: bool | None = None
    error_sanitized: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DistributionQueryResult:
    c_stat: str
    x_motivo: str
    ult_nsu: str
    max_nsu: str
    documents: list[dict[str, Any]] = field(default_factory=list)
    raw_sanitized: dict[str, Any] = field(default_factory=dict)
    sefaz_query_performed: bool = False


class DFeDistributionProvider(ABC):
    @abstractmethod
    def validate_certificate(
        self,
        pfx_bytes: bytes,
        password: str,
        *,
        expected_cnpj: str | None = None,
    ) -> CertificateValidationResult: ...

    @abstractmethod
    def query_distribution_by_last_nsu(
        self, *, company_cnpj: str, uf: str, last_nsu: str, homologation: bool
    ) -> DistributionQueryResult: ...

    @abstractmethod
    def query_distribution_by_nsu(
        self, *, company_cnpj: str, uf: str, nsu: str, homologation: bool
    ) -> DistributionQueryResult: ...

    @abstractmethod
    def query_distribution_by_key(
        self, *, company_cnpj: str, uf: str, access_key: str, homologation: bool
    ) -> DistributionQueryResult: ...

    @abstractmethod
    def parse_distribution_response(self, xml_text: str) -> DistributionQueryResult: ...

    @abstractmethod
    def healthcheck(self) -> dict[str, Any]: ...
