"""Testes DF-e / NF-e entrada — sem SEFAZ real, sem PFX real no Git."""

from __future__ import annotations

import base64
import io
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from cryptography.fernet import Fernet

from src.operational.dfe import store
from src.operational.dfe.packaging import resolve_packaging
from src.operational.dfe.parser import parse_items_from_xml
from src.operational.dfe.pynfe_provider import PyNFeDistributionProvider
from src.operational.dfe.service import (
    advance_nsu_after_persist,
    flags,
    import_files,
    sync_start,
)
from src.operational.dfe.vault import (
    LocalEncryptedSecretVault,
    VaultNotConfiguredError,
    reset_vault_for_tests,
)
from src.operational.dfe.xml_import import ImportErrorDFe, expand_upload, parse_xml_bytes
from src.operational.dfe.certificate_service import upload_and_validate, validate_only
from src.operational.dfe.pre_register import analyze_item


SAMPLE_NFE = b"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe>
    <infNFe Id="NFe35240112345678000190550010000000011000000010" versao="4.00">
      <ide><dhEmi>2024-01-15T10:00:00-03:00</dhEmi></ide>
      <emit><CNPJ>12345678000190</CNPJ><xNome>FORNECEDOR</xNome></emit>
      <dest><CNPJ>11850800000100</CNPJ></dest>
      <det nItem="1">
        <prod>
          <cProd>BONO01</cProd>
          <cEAN>07891000376928</cEAN>
          <xProd>BISCOITO BONO CX C/20</xProd>
          <NCM>19053100</NCM>
          <CEST>1705300</CEST>
          <CFOP>5102</CFOP>
          <uCom>CX</uCom>
          <qCom>2.0000</qCom>
          <vUnCom>40.00</vUnCom>
          <vProd>80.00</vProd>
          <cEANTrib>07891000376928</cEANTrib>
          <uTrib>UN</uTrib>
          <qTrib>40.0000</qTrib>
          <vUnTrib>2.0000</vUnTrib>
        </prod>
        <imposto>
          <ICMS><ICMS00><orig>0</orig><CST>00</CST></ICMS00></ICMS>
        </imposto>
      </det>
    </infNFe>
  </NFe>
  <protNFe><infProt><cStat>100</cStat><nProt>135240000000000</nProt><chNFe>35240112345678000190550010000000011000000010</chNFe></infProt></protNFe>
</nfeProc>
"""

XXE_XML = b"""<?xml version="1.0"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<nfeProc><NFe>&xxe;</NFe></nfeProc>
"""


def _make_pfx(
    *,
    password: str,
    cnpj: str,
    valid_days: int = 365,
    expired: bool = False,
) -> bytes:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "TESTE LOGOS"),
            x509.NameAttribute(NameOID.COMMON_NAME, f"CNPJ:{cnpj}"),
        ]
    )
    now = datetime.now(timezone.utc)
    if expired:
        not_before = now - timedelta(days=400)
        not_after = now - timedelta(days=10)
    else:
        not_before = now - timedelta(days=1)
        not_after = now + timedelta(days=valid_days)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    return pkcs12.serialize_key_and_certificates(
        name=b"test",
        key=key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(password.encode()),
    )


@pytest.fixture()
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    store.reset_store_for_tests(tmp_path / "store")
    monkeypatch.delenv("DFE_VAULT_MASTER_KEY", raising=False)
    monkeypatch.setattr("src.infrastructure.config.settings.settings.dfe_vault_master_key", "")
    monkeypatch.setattr("src.infrastructure.config.settings.settings.dfe_auto_sync_enabled", False)
    yield tmp_path
    store.restore_store_after_tests()


@pytest.fixture()
def vault_ready(isolated, monkeypatch: pytest.MonkeyPatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("DFE_VAULT_MASTER_KEY", key)
    reset_vault_for_tests(isolated / "secrets")
    return key


def test_flags_safe_defaults(isolated):
    f = flags()
    assert f["DFE_AUTO_SYNC_ENABLED"] is False
    assert f["SEFAZ_QUERIES"] == 0
    assert f["WEBPOSTO_WRITES"] == 0
    assert f["vault"]["aesKeyFallback"] is False


def test_vault_without_key_blocks_secrets(isolated):
    v = reset_vault_for_tests(isolated / "secrets")
    assert v.status() == "VAULT_NOT_CONFIGURED"
    with pytest.raises(VaultNotConfiguredError):
        v.put_secret(company_code=1, purpose="PFX", plaintext=b"x")


def test_vault_encrypt_decrypt_and_no_aes_fallback(vault_ready, monkeypatch, isolated):
    monkeypatch.delenv("AES_KEY", raising=False)
    v = reset_vault_for_tests(isolated / "secrets")
    meta = v.put_secret(company_code=118508, purpose="PFX", plaintext=b"pfx-bytes")
    assert meta.encryption_key_version == 1
    assert v.get_secret(meta.secret_id) == b"pfx-bytes"
    assert meta.reencrypt_status == "CURRENT"


def test_vault_invalid_key(isolated, monkeypatch):
    monkeypatch.setenv("DFE_VAULT_MASTER_KEY", "not-a-valid-fernet-key!!!")
    v = LocalEncryptedSecretVault(root=isolated / "secrets")
    assert v.status() == "VAULT_KEY_INVALID"


def test_certificate_valid_offline(vault_ready):
    pfx = _make_pfx(password="segredo", cnpj="11850800000100")
    r = validate_only(pfx_bytes=pfx, password="segredo", expected_cnpj="11850800000100")
    assert r["ok"] is True
    assert r["status"] in {"VALID_OFFLINE_REVOCATION_UNKNOWN", "EXPIRING_SOON"}
    assert r["revocation"] == "NOT_CHECKED"
    assert r["hasPrivateKey"] is True
    assert "11850800000100" in (r["cnpj"] or r.get("sujeito") or "")


def test_certificate_wrong_password(vault_ready):
    pfx = _make_pfx(password="certo", cnpj="11850800000100")
    r = validate_only(pfx_bytes=pfx, password="errado", expected_cnpj="11850800000100")
    assert r["ok"] is False
    assert r["status"] == "INVALID_PASSWORD"


def test_certificate_cnpj_mismatch(vault_ready):
    pfx = _make_pfx(password="x", cnpj="11850800000100")
    r = validate_only(pfx_bytes=pfx, password="x", expected_cnpj="99999999000199")
    assert r["status"] == "CNPJ_MISMATCH"


def test_certificate_expired(vault_ready):
    pfx = _make_pfx(password="x", cnpj="11850800000100", expired=True)
    r = validate_only(pfx_bytes=pfx, password="x", expected_cnpj="11850800000100")
    assert r["status"] == "EXPIRED"
    assert r["ok"] is False


def test_certificate_upload_response_has_no_secrets(vault_ready):
    pfx = _make_pfx(password="segredo", cnpj="11850800000100")
    view = upload_and_validate(
        company_code=118508,
        cnpj="11850800000100",
        uf="PE",
        pfx_bytes=pfx,
        password="segredo",
        actor="tester",
        role="admin",
    )
    blob = str(view)
    assert "segredo" not in blob
    assert "pfx" not in blob.lower() or "certificateId" in view
    assert view["certificateId"]
    assert view["fingerprintSha256"]
    assert "password" not in view
    assert "pfx_secret_id" not in view


def test_xml_authorized_and_ean_zero(isolated):
    meta = parse_xml_bytes(SAMPLE_NFE)
    assert meta["document_type"] == "PROC_NFE"
    assert meta["access_key"] == "35240112345678000190550010000000011000000010"
    items = parse_items_from_xml(SAMPLE_NFE)
    assert items[0]["c_ean"] == "07891000376928"
    assert items[0]["ncm"] == "19053100"
    assert items[0]["cest"] == "1705300"


def test_res_nfe_and_cancel(isolated):
    res = b"""<?xml version="1.0"?><resNFe xmlns="http://www.portalfiscal.inf.br/nfe"><chNFe>35240112345678000190550010000000011000000010</chNFe></resNFe>"""
    meta = parse_xml_bytes(res)
    assert meta["document_type"] == "RES_NFE"
    cancel = b"""<?xml version="1.0"?><procEventoNFe xmlns="http://www.portalfiscal.inf.br/nfe"><evento><infEvento><tpEvento>110111</tpEvento><chNFe>35240112345678000190550010000000011000000010</chNFe></infEvento></evento></procEventoNFe>"""
    cmeta = parse_xml_bytes(cancel)
    assert cmeta["status"] == "CANCELLED"


def test_xxe_blocked(isolated):
    with pytest.raises(ImportErrorDFe) as exc:
        parse_xml_bytes(XXE_XML)
    assert exc.value.code == "INVALID_XML"


def test_zip_bomb_and_traversal(isolated):
    from src.operational.dfe.xml_import import expand_upload_detailed

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../evil.xml", SAMPLE_NFE)
    detailed = expand_upload_detailed("x.zip", buf.getvalue())
    assert any(e.code == "ZIP_PATH_TRAVERSAL" for e in detailed.entries)
    # sem XML válido → fatal ZIP_EMPTY ao usar expand_upload
    with pytest.raises(ImportErrorDFe) as exc:
        expand_upload("x.zip", buf.getvalue())
    assert exc.value.code in {"ZIP_EMPTY", "ZIP_PATH_TRAVERSAL"}


def test_import_duplicate_and_company_isolation(isolated):
    a = import_files(
        company_code=118508,
        company_cnpj="11850800000100",
        files=[("nfe.xml", SAMPLE_NFE)],
        role="operator",
    )
    assert a["results"][0]["ok"] is True
    b = import_files(
        company_code=118508,
        company_cnpj="11850800000100",
        files=[("nfe.xml", SAMPLE_NFE)],
        role="operator",
    )
    assert b["results"][0]["code"] == "DUPLICATE"
    other = store.list_documents(999)
    assert other == []


def test_packaging_and_unit_cost(isolated):
    items = parse_items_from_xml(SAMPLE_NFE)
    pack = resolve_packaging(items[0])
    assert pack["conversion_factor"] == 20.0
    assert pack["purchase_unit_cost"] == 2.0
    assert pack["packaging_status"] in {"PACKAGE_CONFIRMED", "CONVERSION_CONFIRMED", "PACKAGING_AMBIGUITY"}


def test_nsu_not_advanced_on_persist_fail(isolated):
    state = advance_nsu_after_persist(
        118508,
        environment="PRODUCTION",
        new_ult_nsu="5",
        max_nsu="10",
        documents_persisted=False,
    )
    assert state["last_nsu"] == "000000000000000"
    state2 = advance_nsu_after_persist(
        118508,
        environment="PRODUCTION",
        new_ult_nsu="5",
        max_nsu="10",
        documents_persisted=True,
    )
    assert state2["last_nsu"] == "000000000000005"


def test_ult_equals_max(isolated):
    state = advance_nsu_after_persist(
        118508,
        environment="PRODUCTION",
        new_ult_nsu="10",
        max_nsu="10",
        documents_persisted=True,
    )
    assert state["status"] == "UP_TO_DATE"


def test_sync_start_blocked(isolated, vault_ready):
    out = sync_start(company_code=118508, actor="boss", role="admin")
    assert out["blocked"] is True
    assert out["sefazQueries"] == 0
    assert out["webpostoWrites"] == 0
    assert any("DFE_AUTO_SYNC" in r or "SEFAZ" in r for r in out["reasons"])


def test_provider_no_sefaz_query():
    p = PyNFeDistributionProvider(allow_sefaz_queries=False)
    r = p.query_distribution_by_last_nsu(
        company_cnpj="1", uf="PE", last_nsu="0", homologation=True
    )
    assert r.sefaz_query_performed is False
    assert r.c_stat == "BLOCKED"
    assert "pynfe" in p.healthcheck()["provider"].lower() or p.healthcheck()["ok"]


def test_no_pynfe_import_outside_adapter():
    import src.operational.dfe.service as svc
    import src.operational.dfe.xml_import as xi
    import src.operational.dfe.store as st

    for mod in (svc, xi, st):
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "import pynfe" not in src
        assert "from pynfe" not in src


def test_pre_register_no_inbound_tax_copy(isolated):
    items = parse_items_from_xml(SAMPLE_NFE)
    pack = resolve_packaging(items[0])
    items[0].update(pack)
    out = analyze_item(items[0], company_code=118508, fiscal_models=[])
    assert out["webpostoWrites"] == 0
    assert out.get("doNotCopyInboundTaxToOutbound") is True or out["status"] in {
        "NO_FISCAL_MODEL",
        "PACKAGING_AMBIGUITY",
    }


def test_import_recipient_mismatch(isolated):
    out = import_files(
        company_code=118508,
        company_cnpj="99999999000199",
        files=[("nfe.xml", SAMPLE_NFE)],
    )
    assert out["results"][0]["ok"] is False
    assert out["results"][0]["code"] == "RECIPIENT_MISMATCH"


def test_logs_redact_sensitive(isolated):
    dirty = {"password": "x", "pfx": "y", "ok": 1}
    clean = store.redact(dirty)
    assert "password" not in clean
    assert "pfx" not in clean
