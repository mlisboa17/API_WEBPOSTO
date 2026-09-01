"""Testes ZIP/lote DF-e — fixtures sintéticas, sem XML real."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from src.operational.dfe import batch as batch_store
from src.operational.dfe import store
from src.operational.dfe.service import import_files
from src.operational.dfe.xml_import import (
    ImportErrorDFe,
    expand_upload,
    expand_upload_detailed,
    parse_xml_bytes,
)


def _nfe(chave_suffix: str = "0000000011", dest: str = "02080237000155") -> bytes:
    # 44 dígitos fixos — varia os 10 finais
    chave = f"3524011234567800019055001000000000{chave_suffix.zfill(10)}"
    assert len(chave) == 44, len(chave)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe>
    <infNFe Id="NFe{chave}" versao="4.00">
      <ide><dhEmi>2024-01-15T10:00:00-03:00</dhEmi><serie>1</serie><nNF>{chave_suffix[-3:]}</nNF></ide>
      <emit><CNPJ>12345678000190</CNPJ><xNome>FORNECEDOR TESTE</xNome></emit>
      <dest><CNPJ>{dest}</CNPJ></dest>
      <det nItem="1">
        <prod>
          <cProd>P1</cProd><cEAN>07891000376928</cEAN><xProd>ITEM PACOTE</xProd>
          <NCM>19053100</NCM><CEST>1705300</CEST><CFOP>5102</CFOP>
          <uCom>PCT</uCom><qCom>1.0000</qCom><vUnCom>17.44</vUnCom><vProd>17.44</vProd>
          <cEANTrib>07891000376928</cEANTrib><uTrib>UN</uTrib><qTrib>12.0000</qTrib>
        </prod>
      </det>
      <total><ICMSTot><vNF>17.44</vNF></ICMSTot></total>
    </infNFe>
  </NFe>
  <protNFe><infProt><cStat>100</cStat><chNFe>{chave}</chNFe></infProt></protNFe>
</nfeProc>""".encode()


@pytest.fixture()
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    store.reset_store_for_tests(tmp_path / "store")
    batch_store.reset_batches_for_tests()
    monkeypatch.delenv("DFE_VAULT_MASTER_KEY", raising=False)
    monkeypatch.setattr("src.infrastructure.config.settings.settings.dfe_vault_master_key", "")
    yield tmp_path
    store.restore_store_after_tests()


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_single_xml(isolated):
    out = import_files(
        company_code=118508,
        company_cnpj="02080237000155",
        files=[("nfe.xml", _nfe())],
    )
    assert out["imported"] == 1
    assert out["xmlEntriesFound"] == 1
    assert out["webpostoWrites"] == 0
    assert out["sefazQueries"] == 0
    assert out["results"][0]["accessKeyMasked"]


def test_multiple_xmls(isolated):
    out = import_files(
        company_code=118508,
        company_cnpj="02080237000155",
        files=[
            ("a.xml", _nfe("0000000011")),
            ("b.xml", _nfe("0000000022")),
        ],
    )
    assert out["sourceFiles"] == 2
    assert out["imported"] == 2


def test_zip_with_subfolders_and_partial(isolated):
    z = _zip_bytes(
        {
            "a.xml": _nfe("0000000011"),
            "sub/b.XML": _nfe("0000000022"),
            "readme.txt": b"ignore me",
            "bad.xml": b"<not-valid",
            "dup/a.xml": _nfe("0000000011"),  # same as a — duplicate content/key
        }
    )
    detailed = expand_upload_detailed("lote.ZIP", z)
    assert len(detailed.xml_ready) == 4  # a, b, bad, dup
    assert any(e.status == "IGNORED_NON_XML" for e in detailed.entries)

    out = import_files(
        company_code=118508,
        company_cnpj="02080237000155",
        files=[("lote.ZIP", z)],
    )
    assert out["xmlEntriesFound"] == 4
    assert out["imported"] >= 1
    assert out["ignored"] >= 1
    assert out["invalid"] >= 1 or any(r.get("status") == "INVALID_XML" for r in out["results"])
    assert out["duplicates"] >= 1
    assert out["batchStatus"] in {"COMPLETED", "COMPLETED_WITH_ERRORS"}
    assert out["webpostoWrites"] == 0


def test_uppercase_extensions(isolated):
    z = _zip_bytes({"nota.XML": _nfe("0000000033")})
    ready = expand_upload("LOTE.ZIP", z)
    assert len(ready) == 1


def test_path_traversal_does_not_abort_valid_xmls(isolated):
    z = _zip_bytes(
        {
            "../evil.xml": _nfe("0000000044"),
            "ok.xml": _nfe("0000000055"),
        }
    )
    detailed = expand_upload_detailed("x.zip", z)
    assert any(e.relative_path == "ok.xml" and e.status == "READY" for e in detailed.entries)
    assert any(e.code == "ZIP_PATH_TRAVERSAL" for e in detailed.entries)


def test_zip_invalid(isolated):
    with pytest.raises(ImportErrorDFe) as exc:
        expand_upload("x.zip", b"not-a-zip")
    assert exc.value.code == "ZIP_INVALID"


def test_xxe_invalid(isolated):
    xxe = b"""<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><nfeProc>&xxe;</nfeProc>"""
    with pytest.raises(ImportErrorDFe):
        parse_xml_bytes(xxe)


def test_recipient_mismatch(isolated):
    out = import_files(
        company_code=118508,
        company_cnpj="99999999000199",
        files=[("nfe.xml", _nfe())],
    )
    assert out["imported"] == 0
    assert out["recipientMismatch"] == 1


def test_idempotency_duplicate(isolated):
    xml = _nfe("0000000066")
    a = import_files(company_code=118508, company_cnpj="02080237000155", files=[("1.xml", xml)])
    b = import_files(company_code=118508, company_cnpj="02080237000155", files=[("2.xml", xml)])
    assert a["imported"] == 1
    assert b["duplicates"] == 1


def test_packaging_decimal_cost(isolated):
    out = import_files(
        company_code=118508,
        company_cnpj="02080237000155",
        files=[("nfe.xml", _nfe("0000000077"))],
    )
    item = out["results"][0]["items"][0]
    assert item["conversionFactor"] == 12.0
    assert abs(float(item["purchaseUnitCost"]) - (17.44 / 12)) < 1e-6
    assert "R$" in (item["packagingExplain"]["custoUnitario"] or "")


def test_no_sefaz_no_webposto_writes(isolated):
    z = _zip_bytes({"a.xml": _nfe("0000000088"), "b.xml": _nfe("0000000099")})
    out = import_files(
        company_code=118508,
        company_cnpj="02080237000155",
        files=[("lote.zip", z)],
    )
    assert out["sefazQueries"] == 0
    assert out["webpostoWrites"] == 0
    assert out["manifestation"] == 0
