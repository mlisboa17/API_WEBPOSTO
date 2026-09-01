"""Único módulo autorizado a importar PyNFe."""

from __future__ import annotations

import base64
import gzip
import hashlib
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography import x509
import httpx
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, pkcs12

from src.operational.dfe.provider import (
    CertificateValidationResult,
    DFeDistributionProvider,
    DistributionQueryResult,
)

_CNPJ_RE = re.compile(r"(\d{14})")


def _digits(value: str | None) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _cnpj_from_subject(subject: str) -> str | None:
    # e-CNPJ ICP-Brasil: prioriza os 14 dígitos após ':' no Common Name.
    m = re.search(r"CN=[^,]*:(\d{14})(?:,|$)", subject, flags=re.IGNORECASE)
    if m:
        return m.group(1)
    m = _CNPJ_RE.search(_digits(subject))
    if m:
        return m.group(1)
    return None


class PyNFeDistributionProvider(DFeDistributionProvider):
    """Adaptador PyNFe 0.6.5. Consultas SEFAZ desabilitadas nesta entrega."""

    PRODUCTION_URL = "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx"
    HOMOLOGATION_URL = "https://hom.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx"
    UF_CODES = {"PE": "26"}

    def __init__(self, *, allow_sefaz_queries: bool = False, pfx_bytes: bytes | None = None, password: str | None = None, timeout_seconds: float = 30.0) -> None:
        self.allow_sefaz_queries = allow_sefaz_queries
        self.pfx_bytes = pfx_bytes
        self.password = password
        self.timeout_seconds = timeout_seconds

    def validate_certificate(
        self,
        pfx_bytes: bytes,
        password: str,
        *,
        expected_cnpj: str | None = None,
    ) -> CertificateValidationResult:
        tmp_path: Path | None = None
        try:
            pwd = password.encode("utf-8") if isinstance(password, str) else password
            try:
                key, cert, additional = pkcs12.load_key_and_certificates(pfx_bytes, pwd)
            except ValueError:
                return CertificateValidationResult(
                    ok=False,
                    status="INVALID_PASSWORD",
                    error_sanitized="senha incorreta ou PKCS#12 inválido",
                )
            except Exception:
                return CertificateValidationResult(
                    ok=False,
                    status="INVALID_PASSWORD",
                    error_sanitized="falha ao abrir PKCS#12",
                )

            if cert is None:
                return CertificateValidationResult(
                    ok=False,
                    status="CHAIN_INVALID",
                    error_sanitized="certificado ausente no PKCS#12",
                )

            has_key = key is not None
            if not has_key:
                return CertificateValidationResult(
                    ok=False,
                    status="CHAIN_INVALID",
                    error_sanitized="chave privada ausente",
                    has_private_key=False,
                )

            subject = cert.subject.rfc4514_string()
            issuer = cert.issuer.rfc4514_string()
            serial = format(cert.serial_number, "x")
            valid_from = cert.not_valid_before_utc.isoformat()
            valid_to = cert.not_valid_after_utc.isoformat()
            fp = hashlib.sha256(cert.public_bytes(Encoding.DER)).hexdigest()

            extracted = _cnpj_from_subject(subject)
            # tenta SAN / atributos BR
            try:
                for attr in cert.subject:
                    oid_digits = _digits(attr.value)
                    if not extracted and attr.oid.dotted_string == "2.16.76.1.3.3" and len(oid_digits) == 14:
                        extracted = oid_digits
            except Exception:
                pass

            now = datetime.now(timezone.utc)
            days = (cert.not_valid_after_utc - now).days
            if now > cert.not_valid_after_utc:
                status = "EXPIRED"
                ok = False
            elif days <= 30:
                status = "VALID_OFFLINE_REVOCATION_UNKNOWN"
                ok = True
                # expiring soon still valid offline
                if days <= 30:
                    status = "EXPIRING_SOON" if days >= 0 else status
            else:
                status = "VALID_OFFLINE_REVOCATION_UNKNOWN"
                ok = True

            # Client Auth EKU when available
            client_auth: bool | None = None
            try:
                eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
                client_auth = x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH in eku.value
            except x509.ExtensionNotFound:
                client_auth = None
            except Exception:
                client_auth = None

            chain_ok: bool | None = None
            if additional:
                chain_ok = True  # presença de cadeia local; sem validação completa de âncora

            exp = _digits(expected_cnpj)
            if exp and extracted and exp != extracted:
                return CertificateValidationResult(
                    ok=False,
                    status="CNPJ_MISMATCH",
                    serial_number=serial,
                    issuer=issuer,
                    subject=subject,
                    extracted_cnpj=extracted,
                    valid_from=valid_from,
                    valid_to=valid_to,
                    fingerprint_sha256=fp,
                    days_to_expiry=days,
                    has_private_key=has_key,
                    client_auth=client_auth,
                    chain_ok=chain_ok,
                    error_sanitized="CNPJ do certificado diverge da empresa",
                )

            if status == "EXPIRED":
                return CertificateValidationResult(
                    ok=False,
                    status=status,
                    serial_number=serial,
                    issuer=issuer,
                    subject=subject,
                    extracted_cnpj=extracted,
                    valid_from=valid_from,
                    valid_to=valid_to,
                    fingerprint_sha256=fp,
                    days_to_expiry=days,
                    has_private_key=has_key,
                    client_auth=client_auth,
                    chain_ok=chain_ok,
                    error_sanitized="certificado expirado",
                )

            # PyNFe path opcional (temp seguro) — só para health da lib, não SEFAZ
            try:
                import pynfe  # noqa: F401 — garante presença da lib no adaptador
            except ImportError:
                pass

            # EXPIRING_SOON still offline-valid with unknown revocation
            if 0 <= days <= 30:
                status = "EXPIRING_SOON"

            return CertificateValidationResult(
                ok=ok,
                status=status,
                serial_number=serial,
                issuer=issuer,
                subject=subject,
                extracted_cnpj=extracted,
                valid_from=valid_from,
                valid_to=valid_to,
                fingerprint_sha256=fp,
                days_to_expiry=days,
                has_private_key=has_key,
                client_auth=client_auth,
                chain_ok=chain_ok,
                details={"revocation": "NOT_CHECKED", "offline": True},
            )
        finally:
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    def _blocked_query(self) -> DistributionQueryResult:
        return DistributionQueryResult(
            c_stat="BLOCKED",
            x_motivo="SEFAZ queries desabilitadas nesta entrega (SEFAZ_QUERIES=0)",
            ult_nsu="000000000000000",
            max_nsu="000000000000000",
            sefaz_query_performed=False,
        )

    def query_distribution_by_last_nsu(self, **kwargs: Any) -> DistributionQueryResult:
        if not self.allow_sefaz_queries:
            return self._blocked_query()
        raise NotImplementedError("Consulta SEFAZ requer autorização explícita")

    def query_distribution_by_nsu(self, **kwargs: Any) -> DistributionQueryResult:
        if not self.allow_sefaz_queries:
            return self._blocked_query()
        raise NotImplementedError("Consulta SEFAZ requer autorização explícita")

    def query_distribution_by_key(self, **kwargs: Any) -> DistributionQueryResult:
        if not self.allow_sefaz_queries:
            return self._blocked_query()
        raise NotImplementedError("Consulta SEFAZ requer autorização explícita")

    def _live_query(self, *, selector: str, company_cnpj: str, uf: str, homologation: bool) -> DistributionQueryResult:
        if not self.pfx_bytes or self.password is None:
            raise RuntimeError("certificado A1 não carregado")
        cnpj = _digits(company_cnpj)
        c_uf = self.UF_CODES.get(uf.upper())
        if len(cnpj) != 14 or not c_uf:
            raise ValueError("CNPJ ou UF inválido")
        dist = ('<distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">'
                f'<tpAmb>{2 if homologation else 1}</tpAmb><cUFAutor>{c_uf}</cUFAutor>'
                f'<CNPJ>{cnpj}</CNPJ>{selector}</distDFeInt>')
        envelope = ('<?xml version="1.0" encoding="utf-8"?>'
                    '<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
                    '<soap12:Body><nfeDistDFeInteresse xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">'
                    f'<nfeDadosMsg>{dist}</nfeDadosMsg></nfeDistDFeInteresse></soap12:Body></soap12:Envelope>')
        private_key, certificate, _ = pkcs12.load_key_and_certificates(
            self.pfx_bytes, self.password.encode("utf-8")
        )
        if private_key is None or certificate is None:
            raise RuntimeError("certificado A1 sem chave privada")
        with tempfile.TemporaryDirectory(prefix="dfe_mtls_") as tmp:
            cert_path, key_path = Path(tmp) / "cert.pem", Path(tmp) / "key.pem"
            cert_path.write_bytes(certificate.public_bytes(Encoding.PEM))
            key_path.write_bytes(private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()))
            try:
                os.chmod(cert_path, 0o600); os.chmod(key_path, 0o600)
            except OSError:
                pass
            url = self.HOMOLOGATION_URL if homologation else self.PRODUCTION_URL
            with httpx.Client(cert=(str(cert_path), str(key_path)), timeout=self.timeout_seconds) as client:
                response = client.post(url, content=envelope.encode(), headers={"Content-Type": "application/soap+xml; charset=utf-8"})
                response.raise_for_status()
        from lxml import etree
        parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
        root = etree.fromstring(response.content, parser=parser)
        nodes = root.xpath("//*[local-name()='nfeDistDFeInteresseResult']")
        if not nodes:
            raise RuntimeError("resposta SEFAZ inválida")
        result_node = nodes[0]
        ret = next((x for x in result_node if etree.QName(x).localname == "retDistDFeInt"), None)
        if ret is None and result_node.text:
            ret = etree.fromstring(result_node.text.encode(), parser=parser)
        if ret is None:
            raise RuntimeError("retDistDFeInt ausente")
        def value(name: str, default: str = "") -> str:
            found = ret.xpath(f".//*[local-name()='{name}']/text()")
            return str(found[0]).strip() if found else default
        documents = []
        for doc in ret.xpath(".//*[local-name()='docZip']"):
            raw = base64.b64decode((doc.text or "").strip(), validate=True)
            documents.append({"nsu": str(doc.get("NSU") or "").zfill(15), "schema": doc.get("schema"), "xml_bytes": gzip.decompress(raw)})
        return DistributionQueryResult(
            c_stat=value("cStat"), x_motivo=value("xMotivo"),
            ult_nsu=value("ultNSU", "0").zfill(15), max_nsu=value("maxNSU", "0").zfill(15),
            documents=documents, raw_sanitized={"http_status": response.status_code, "document_count": len(documents)},
            sefaz_query_performed=True,
        )

    def query_distribution_by_last_nsu(self, *, company_cnpj: str, uf: str, last_nsu: str, homologation: bool) -> DistributionQueryResult:
        if not self.allow_sefaz_queries:
            return self._blocked_query()
        return self._live_query(selector=f"<distNSU><ultNSU>{str(last_nsu).zfill(15)}</ultNSU></distNSU>", company_cnpj=company_cnpj, uf=uf, homologation=homologation)

    def query_distribution_by_nsu(self, *, company_cnpj: str, uf: str, nsu: str, homologation: bool) -> DistributionQueryResult:
        if not self.allow_sefaz_queries:
            return self._blocked_query()
        return self._live_query(selector=f"<consNSU><NSU>{str(nsu).zfill(15)}</NSU></consNSU>", company_cnpj=company_cnpj, uf=uf, homologation=homologation)

    def query_distribution_by_key(self, *, company_cnpj: str, uf: str, access_key: str, homologation: bool) -> DistributionQueryResult:
        if not self.allow_sefaz_queries:
            return self._blocked_query()
        key = _digits(access_key)
        if len(key) != 44:
            raise ValueError("chave deve conter 44 dígitos")
        return self._live_query(selector=f"<consChNFe><chNFe>{key}</chNFe></consChNFe>", company_cnpj=company_cnpj, uf=uf, homologation=homologation)

    def parse_distribution_response(self, xml_text: str) -> DistributionQueryResult:
        """Parse offline de retDistDFeInt (sem rede)."""
        from lxml import etree

        parser = etree.XMLParser(resolve_entities=False, no_network=True, dtd_validation=False)
        root = etree.fromstring(xml_text.encode("utf-8"), parser=parser)
        ns = {"n": "http://www.portalfiscal.inf.br/nfe"}

        def _t(xpath: str, default: str = "") -> str:
            nodes = root.xpath(xpath, namespaces=ns)
            if nodes:
                return str(nodes[0]).strip()
            # fallback sem ns
            nodes = root.xpath(xpath.replace("n:", ""))
            return str(nodes[0]).strip() if nodes else default

        c_stat = _t("//n:cStat") or _t("//cStat")
        x_motivo = _t("//n:xMotivo") or _t("//xMotivo")
        ult = (_t("//n:ultNSU") or _t("//ultNSU") or "0").zfill(15)
        mx = (_t("//n:maxNSU") or _t("//maxNSU") or "0").zfill(15)
        docs: list[dict[str, Any]] = []
        for doc in root.xpath("//n:docZip", namespaces=ns) or root.xpath("//docZip"):
            docs.append(
                {
                    "nsu": str(doc.get("NSU") or "").zfill(15),
                    "schema": doc.get("schema"),
                    "content_b64": None,  # não ecoar payload bruto em logs
                }
            )
        return DistributionQueryResult(
            c_stat=c_stat,
            x_motivo=x_motivo,
            ult_nsu=ult,
            max_nsu=mx,
            documents=docs,
            sefaz_query_performed=False,
        )

    def healthcheck(self) -> dict[str, Any]:
        try:
            import pynfe

            ver = getattr(pynfe, "__version__", "0.6.5")
            return {
                "ok": True,
                "provider": "PyNFeDistributionProvider",
                "pynfe_version": ver,
                "sefaz_queries_allowed": self.allow_sefaz_queries,
            }
        except ImportError:
            return {"ok": False, "provider": "PyNFeDistributionProvider", "error": "pynfe missing"}


def secure_temp_pfx(pfx_bytes: bytes) -> Path:
    """Arquivo temporário seguro — caller deve remover em finally."""
    fd, name = tempfile.mkstemp(prefix="dfe_pfx_", suffix=".pfx")
    path = Path(name)
    try:
        import os

        with os.fdopen(fd, "wb") as fh:
            fh.write(pfx_bytes)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return path
    except Exception:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        raise
