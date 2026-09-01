"""Ingestao incremental DF-e + recálculo. Fixtures ficticios, sem store fiscal real."""

from __future__ import annotations

import importlib.util
import io
import json
import zipfile
from decimal import Decimal
from pathlib import Path

import pytest

from src.operational.cost_update.current_cost_reader import CurrentProductCostReader
from src.operational.cost_update.proposal_store import CostProposalStore
from src.operational.cost_update.service import CostUpdateService
from src.operational.dfe import batch as batch_store
from src.operational.dfe import store
from src.operational.dfe.provider import DistributionQueryResult
from src.operational.dfe.service import import_files
from src.operational.dfe.xml_import import sha256_bytes
from src.operational.dfe_sync.lease import acquire_lease, release_lease
from src.operational.dfe_sync.local_inbox import import_local
from src.operational.dfe_sync.packaging_conversion import PackagingConversionResolver
from src.operational.dfe_sync.sefaz_once import sync_sefaz_once
from src.operational.dfe_sync.service import DfeCostSyncService
from src.operational.product_registration.dfe_cost_resolver import (
    resolve_sale_unit_quantity,
)

ROOT = Path(__file__).resolve().parents[2]
EAN = "7891000000001"
EAN_OTHER = "7891000000002"
DEST = "02080237000155"
CHAVE = "35240100000000000000550010000000019999999999"


def _nfe(
    *,
    chave: str = CHAVE,
    dest: str = DEST,
    ean: str = EAN,
    ean_trib: str | None = None,
    u_com: str = "UNI",
    q_com: str = "6.0000",
    u_trib: str = "UNI",
    q_trib: str = "6.0000",
    x_prod: str = "PRODUTO FICTICIO",
    c_prod: str = "FORN01",
    v_prod: str = "15.90",
    protocol: str = "100",
) -> bytes:
    assert len(chave) == 44
    trib = ean_trib if ean_trib is not None else ean
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe>
    <infNFe Id="NFe{chave}" versao="4.00">
      <ide><dhEmi>2026-08-01T10:00:00-03:00</dhEmi><serie>1</serie><nNF>1</nNF></ide>
      <emit><CNPJ>00000000000191</CNPJ><xNome>FORNECEDOR FICTICIO</xNome></emit>
      <dest><CNPJ>{dest}</CNPJ></dest>
      <det nItem="1">
        <prod>
          <cProd>{c_prod}</cProd>
          <cEAN>{ean}</cEAN>
          <xProd>{x_prod}</xProd>
          <NCM>19053100</NCM>
          <CEST>1705300</CEST>
          <CFOP>5405</CFOP>
          <uCom>{u_com}</uCom>
          <qCom>{q_com}</qCom>
          <vUnCom>2.65</vUnCom>
          <vProd>{v_prod}</vProd>
          <cEANTrib>{trib}</cEANTrib>
          <uTrib>{u_trib}</uTrib>
          <qTrib>{q_trib}</qTrib>
        </prod>
        <imposto><ICMS><ICMS00><orig>0</orig><CST>00</CST></ICMS00></ICMS></imposto>
      </det>
      <total><ICMSTot><vProd>{v_prod}</vProd><vNF>{v_prod}</vNF></ICMSTot></total>
    </infNFe>
  </NFe>
  <protNFe><infProt><cStat>{protocol}</cStat><nProt>135000000000000</nProt><chNFe>{chave}</chNFe></infProt></protNFe>
</nfeProc>""".encode()


def _res_nfe(chave: str = CHAVE) -> bytes:
    return (
        f'<?xml version="1.0"?><resNFe xmlns="http://www.portalfiscal.inf.br/nfe">'
        f"<chNFe>{chave}</chNFe></resNFe>"
    ).encode()


def _cancel(chave: str = CHAVE) -> bytes:
    return (
        '<?xml version="1.0"?><procEventoNFe xmlns="http://www.portalfiscal.inf.br/nfe">'
        f"<evento><infEvento><tpEvento>110111</tpEvento><chNFe>{chave}</chNFe></infEvento></evento>"
        "</procEventoNFe>"
    ).encode()


def _zip(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


@pytest.fixture()
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    store.reset_store_for_tests(tmp_path / "store")
    batch_store.reset_batches_for_tests()
    monkeypatch.delenv("DFE_VAULT_MASTER_KEY", raising=False)
    monkeypatch.setattr("src.infrastructure.config.settings.settings.dfe_vault_master_key", "")
    yield tmp_path
    store.restore_store_after_tests()


class FakeReader:
    def __init__(self, catalog, links) -> None:
        self.catalog = catalog
        self.links = links

    def get_catalog(self, key, cursor, page_size):
        return self.catalog

    def get_company_links(self, key, cursor, page_size):
        return self.links


class FakeProvider:
    def __init__(self, result: DistributionQueryResult) -> None:
        self.result = result
        self.calls = 0
        self.manifested = 0

    def query_distribution_by_last_nsu(self, **kwargs):
        self.calls += 1
        return self.result

    def query_distribution_by_key(self, **kwargs):
        self.manifested += 1
        raise AssertionError("consulta por chave exige manifestacao e esta proibida")


def _pending(root: Path, *eans: str) -> None:
    path = root / "data" / "product_registration" / "pending_cost_update_118508.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        ean: {
            "ean": ean,
            "descricao": "FICTICIO",
            "produtoCodigo": 10 + i,
            "precoCustoCadastrado": 0,
            "precoVenda": 4.9,
        }
        for i, ean in enumerate(eans)
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _reader(*eans: str) -> CurrentProductCostReader:
    catalog = []
    links = []
    for i, ean in enumerate(eans):
        catalog.append(
            {
                "produtoCodigo": 10 + i,
                "nome": "FICTICIO",
                "ncm": "19053100",
                "cest": "1705300",
                "produtoCodigoBarra": [{"codigoBarra": ean}],
            }
        )
        links.append(
            {
                "produtoCodigo": 10 + i,
                "empresaCodigo": 118508,
                "precoCusto": 0,
                "precoVenda": 4.9,
                "ativo": True,
            }
        )
    return CurrentProductCostReader(FakeReader(catalog, links))


def test_import_xml_procnfe_and_hash(isolated):
    xml = _nfe()
    digest = sha256_bytes(xml)
    out = import_files(company_code=118508, company_cnpj=DEST, files=[("nfe.xml", xml)])
    assert out["imported"] == 1
    assert out["webpostoWrites"] == 0
    assert out["manifestation"] == 0
    assert out["results"][0]["sha256"] == digest
    assert out["results"][0]["accessKeyMasked"] != CHAVE
    items = store.load_items(out["results"][0]["documentId"])
    norm = items[0]["normalized_json"]
    assert norm["c_ean"] == EAN
    assert norm["c_ean_trib"] == EAN
    assert norm["ncm"] == "19053100"
    assert norm["cest"] == "1705300"
    assert norm["cfop"] == "5405"


def test_import_zip_and_resumo(isolated):
    zipped = _zip({"lote/nfe.xml": _nfe(), "lote/res.xml": _res_nfe()})
    out = import_files(company_code=118508, company_cnpj=DEST, files=[("lote.zip", zipped)])
    types = {row["documentType"] for row in out["results"] if row.get("ok")}
    assert "PROC_NFE" in types
    assert "RES_NFE" in types
    assert out["webpostoWrites"] == 0


def test_cancel_event_marks_original(isolated):
    first = import_files(company_code=118508, company_cnpj=DEST, files=[("nfe.xml", _nfe())])
    doc_id = first["results"][0]["documentId"]
    cancel = import_files(company_code=118508, company_cnpj=DEST, files=[("canc.xml", _cancel())])
    assert cancel["cancelled"] == 1
    assert cancel["results"][0]["status"] == "CANCELLED"
    assert store.load_document(doc_id)["protocol"]["cancelled"] is True


def test_wrong_recipient_and_invalid_go_to_quarantine(isolated):
    inbox = isolated / "data" / "dfe" / "inbox" / "118508"
    inbox.mkdir(parents=True)
    (inbox / "wrong.xml").write_bytes(_nfe(dest="11495000000100"))
    (inbox / "bad.xml").write_bytes(b"<not-xml")
    out = import_local(root=isolated)
    assert out["found"] == 2
    assert out["imported"] == 0
    assert out["recipient_mismatch"] == 1
    assert out["invalid"] >= 1
    assert out["quarantined"] == 2
    reasons = list((isolated / "data" / "dfe" / "quarantine" / "118508").glob("*.reason.json"))
    assert reasons
    assert (inbox / "wrong.xml").is_file()


def test_duplicate_and_original_untouched(isolated):
    inbox = isolated / "data" / "dfe" / "inbox" / "118508"
    inbox.mkdir(parents=True)
    xml = _nfe()
    original = inbox / "nfe.xml"
    original.write_bytes(xml)
    first = import_local(root=isolated)
    second = import_local(root=isolated)
    assert first["imported"] == 1
    assert second["duplicates"] == 1
    assert original.read_bytes() == xml


def test_resume_after_failed_import_does_not_advance_nsu(isolated):
    store.save_sync_state(
        {
            "company_code": 118508,
            "environment": "PRODUCTION",
            "last_nsu": "000000000000042",
            "max_nsu": "000000000000100",
        }
    )
    provider = FakeProvider(
        DistributionQueryResult(
            c_stat="138",
            x_motivo="Documentos localizados",
            ult_nsu="000000000000050",
            max_nsu="000000000000100",
            documents=[{"nsu": "000000000000050", "xml_bytes": b"<not-xml"}],
        )
    )
    out = sync_sefaz_once(provider=provider)
    assert out["current_nsu"] == "000000000000042"
    assert out["ok"] is False
    assert provider.calls == 1
    assert provider.manifested == 0


def test_last_nsu_advances_only_after_safe_import(isolated):
    store.save_sync_state(
        {
            "company_code": 118508,
            "environment": "PRODUCTION",
            "last_nsu": "000000000000010",
            "max_nsu": "000000000000100",
        }
    )
    provider = FakeProvider(
        DistributionQueryResult(
            c_stat="138",
            x_motivo="Documentos localizados",
            ult_nsu="000000000000020",
            max_nsu="000000000000100",
            documents=[{"nsu": "000000000000020", "xml_bytes": _nfe()}],
        )
    )
    out = sync_sefaz_once(provider=provider)
    assert out["previous_nsu"] == "000000000000010"
    assert out["current_nsu"] == "000000000000020"
    assert out["imported"] == 1
    assert out["sefaz_queries"] == 1
    assert out["manifestation"] == 0
    assert EAN in out["affected_eans"]


def test_cstat_656_sets_cooldown_and_keeps_nsu(isolated):
    store.save_sync_state(
        {
            "company_code": 118508,
            "environment": "PRODUCTION",
            "last_nsu": "000000000000007",
            "max_nsu": "000000000000100",
        }
    )
    provider = FakeProvider(
        DistributionQueryResult(
            c_stat="656",
            x_motivo="Consumo indevido",
            ult_nsu="000000000000099",
            max_nsu="000000000000100",
        )
    )
    first = sync_sefaz_once(provider=provider)
    assert first["reason"] == "SEFAZ_656"
    assert first["current_nsu"] == "000000000000007"
    second = sync_sefaz_once(provider=provider)
    assert second["reason"] == "SEFAZ_COOLDOWN_ACTIVE"
    assert second["sefaz_queries"] == 0
    assert provider.calls == 1


def test_lease_blocks_two_runs(isolated):
    first = acquire_lease(118508)
    second = acquire_lease(118508)
    assert first["ok"] is True
    assert second["ok"] is False
    release_lease(118508, first["owner"])
    third = acquire_lease(118508)
    assert third["ok"] is True


def test_packaging_qtrib_uni_and_cx12():
    resolver = PackagingConversionResolver()
    uni = resolver.resolve({"u_com": "CX", "q_com": "1", "u_trib": "UNI", "q_trib": "12", "x_prod": "X"})
    assert uni["ok"] is True
    assert uni["factor"] == Decimal(12)
    named = resolver.resolve({"u_com": "CX12", "q_com": "2", "u_trib": "CX12", "q_trib": "2", "x_prod": "X"})
    assert named["factor"] == Decimal(12)
    qty, origin = resolve_sale_unit_quantity({"u_com": "CX12", "q_com": "2", "u_trib": "CX12", "q_trib": "2"})
    assert qty == Decimal(24)
    assert origin == "packaging_conversion"


def test_packaging_dp_kg_and_description_suggestion():
    resolver = PackagingConversionResolver()
    display = resolver.resolve({"u_com": "DP", "q_com": "1", "u_trib": "DP", "q_trib": "1", "x_prod": "DISPLAY C/30"})
    assert display["ok"] is False
    assert display["status"] == "REVIEW_REQUIRED"
    assert display["suggested_factor"] == Decimal(30)
    kilo = resolver.resolve({"u_com": "KG", "q_com": "3.6", "u_trib": "KG", "q_trib": "3.6", "x_prod": "QUEIJO"})
    assert kilo["ok"] is False
    assert "KG" in kilo["calculo"]


def test_manual_versioned_factor():
    resolver = PackagingConversionResolver(
        [
            {
                "supplier_cnpj": "00000000000191",
                "supplier_item_code": "FORN01",
                "ean": EAN,
                "units_per_package": "12",
            }
        ]
    )
    resolved = resolver.resolve(
        {"u_com": "CX", "q_com": "1", "u_trib": "CX", "q_trib": "1", "c_ean": EAN, "c_prod": "FORN01"},
        supplier_cnpj="00000000000191",
    )
    assert resolved["ok"] is True
    assert resolved["factor"] == Decimal(12)
    assert "tabela manual versionada" in resolved["evidences"]


def test_recalculate_only_affected_ean_and_supersede(isolated):
    _pending(isolated, EAN, EAN_OTHER)
    service = DfeCostSyncService(isolated, output_dir=isolated / "out")
    reader = _reader(EAN, EAN_OTHER)
    first = service.recalculate({EAN, EAN_OTHER}, key="fake", reader=reader)
    assert first["recalculated"] == 2
    assert first["counts"]["DFE_NOT_FOUND"] == 2
    assert first["event"] == "DFE_IMPORTED_COST_REEVALUATED"
    inbox = isolated / "data" / "dfe" / "inbox" / "118508"
    inbox.mkdir(parents=True)
    (inbox / "nfe.xml").write_bytes(_nfe())
    imported = service.import_local()
    assert imported["imported"] == 1
    second = service.recalculate(set(imported["affected_eans"]), key="fake", reader=reader)
    assert second["recalculated"] == 1
    assert second["affected_pending"] == [EAN]
    assert second["webposto_writes"] == 0
    history = CostProposalStore(isolated / "out")
    versions = history.load_index()["by_ean"][EAN]
    assert len(versions) == 2
    old = history.get_by_hash(versions[0])
    assert old["lifecycle"] == "SUPERSEDED"
    assert old["status"] == "DFE_NOT_FOUND"
    latest = history.latest_for_ean(EAN)
    assert latest["status"] in {"PROPOSED", "REVIEW_REQUIRED", "NO_CHANGE"}
    other = history.latest_for_ean(EAN_OTHER)
    assert other["status"] == "DFE_NOT_FOUND"


def test_run_once_lease_and_no_writes(isolated):
    _pending(isolated, EAN)
    provider = FakeProvider(
        DistributionQueryResult(
            c_stat="137",
            x_motivo="Nenhum documento",
            ult_nsu="000000000000003",
            max_nsu="000000000000003",
        )
    )
    service = DfeCostSyncService(isolated, output_dir=isolated / "out")
    out = service.run_once(provider=provider, key="fake", reader=_reader(EAN))
    assert out["ok"] is True
    assert out["webposto_writes"] == 0
    assert out["manifestation"] == 0
    assert out["sefaz"]["sefaz_queries"] == 1
    held = service.run_once(provider=provider, key="fake", reader=_reader(EAN))
    # lease ja liberado; segunda execucao pega lease de novo
    assert held["ok"] is True
    acquire_lease(118508)
    blocked = service.run_once(provider=provider, key="fake", reader=_reader(EAN))
    assert blocked["reason"] == "LEASE_HELD"


def test_cli_execute_refused():
    path = ROOT / "scripts" / "dfe_cost_sync_118508.py"
    spec = importlib.util.spec_from_file_location("dfe_cost_sync_cli", path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    import sys

    sys.argv = ["dfe_cost_sync_118508.py", "--execute", "status"]
    assert cli.main() == 5


def test_incremental_propose_does_not_rewrite_aggregates(isolated, tmp_path):
    pending = tmp_path / "pending.json"
    pending.write_text(
        json.dumps(
            {
                EAN: {"ean": EAN, "produtoCodigo": 10, "precoCustoCadastrado": 0, "precoVenda": 4.9},
                EAN_OTHER: {
                    "ean": EAN_OTHER,
                    "produtoCodigo": 11,
                    "precoCustoCadastrado": 0,
                    "precoVenda": 4.9,
                },
            }
        ),
        encoding="utf-8",
    )
    missing = tmp_path / "missing.json"
    service = CostUpdateService(
        tmp_path / "out",
        reader=_reader(EAN, EAN_OTHER),
        pending_path=pending,
        price_review_path=missing,
        checkpoint_path=missing,
        accountant_path=missing,
    )
    service.propose("fake")
    (tmp_path / "out" / "cost_update_dfe_not_found.json").write_text(
        json.dumps({"items": [{"ean": "KEEP"}]}),
        encoding="utf-8",
    )
    service.propose("fake", eans={EAN}, persist_aggregates=False, event="DFE_IMPORTED_COST_REEVALUATED")
    kept = json.loads((tmp_path / "out" / "cost_update_dfe_not_found.json").read_text(encoding="utf-8"))
    assert kept["items"][0]["ean"] == "KEEP"
    assert (tmp_path / "out" / "recalculate_delta.json").is_file()
