"""Migracao final: executores passam pela fachada. Sem rede e sem escrita em data/."""

from __future__ import annotations

import ast
import json
import warnings
from pathlib import Path

import pytest

from src.operational.product_registration.body_builder import (
    create_registration_request,
    get_default_bono_template,
)
from src.operational.product_registration.compatibility import (
    create_registration_request as compat_create_request,
    post_product as compat_post_product,
    validate_cost,
)
from src.operational.product_registration.engine_schemas import (
    ProductRegistrationRequest,
    RiskAuthorization,
)
from src.operational.product_registration.registration_engine import ProductRegistrationService
from src.operational.product_registration.schemas import ProductAnalysis
from src.operational.product_registration.stores import RegistrationLockStore, interpret_lock

ROOT = Path(__file__).resolve().parents[2]

WRITE_EXECUTORS = (
    ROOT / "scripts" / "execute_wave_118508.py",
    ROOT / "scripts" / "execute_microbatch_118508.py",
    ROOT / "scripts" / "execute_negresco_pilot_118508.py",
    ROOT / "scripts" / "execute_ready_products_118508.py",
    ROOT / "src" / "operational" / "product_registration" / "registration_executor.py",
)

OPERATIONAL_SCRIPTS = WRITE_EXECUTORS + (
    ROOT / "scripts" / "product_registration.py",
)


def _request(**overrides) -> ProductRegistrationRequest:
    payload = dict(
        empresa=118508,
        centro=24886,
        ean="7891000377130",
        descricao="PRODUTO TESTE 350ML",
        preco_venda=9.9,
        ncm="19053100",
        cest="1705300",
        custo=4.5,
        cost_source="DFE",
        cost_status="RESOLVED",
        authorization=RiskAuthorization(accept_fiscal_risk=True),
        perfil_fiscal={
            "cfop_entrada": "1.102",
            "cfop_saida": "5.405",
            "tributacao_monofasica": 0,
            "tributo_icms": {"cstEntrada": "060", "cstSaida": "060", "dsCsosnEntrada": "0"},
            "tributo_pis_cofins": {"cstPisSaida": "01"},
        },
    )
    payload.update(overrides)
    return ProductRegistrationRequest(**payload)


def _analysis() -> ProductAnalysis:
    return ProductAnalysis(
        ean="7891000377130",
        descricao="PRODUTO TESTE 350ML",
        preco_venda=9.9,
        gate="EAN_OK",
        status="READY_TO_CREATE",
        confidence="ALTA",
        risk_level="BAIXO_RISCO",
        ncm="19053100",
        cest="1705300",
        grupo_api_codigo=55446,
        centro_api_codigo=24886,
        tributo_icms={"cstSaida": "060"},
        tributo_pis_cofins={"cstPisSaida": "01"},
    )


def _direct_client_posts(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "post":
            continue
        owner = node.func.value
        if isinstance(owner, ast.Name) and owner.id in {"client", "resp"}:
            hits.append(f"{path.name}:{node.lineno}")
        if isinstance(owner, ast.Attribute) and owner.attr == "client":
            hits.append(f"{path.name}:{node.lineno}")
    return hits


def test_no_write_executor_posts_outside_facade():
    for path in WRITE_EXECUTORS:
        source = path.read_text(encoding="utf-8")
        assert "ProductRegistrationService" in source
        assert not _direct_client_posts(path), path.name
        assert "WebPostoRegistrationGateway" not in source


def test_operational_scripts_do_not_import_gateway():
    for path in OPERATIONAL_SCRIPTS:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "product_registration.gateway" not in node.module
                assert node.module != "gateway"


def test_body_builder_is_deprecated_and_does_not_inherit_bono():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        template = get_default_bono_template()
    assert any(item.category is DeprecationWarning for item in caught)
    assert template["body"] == {}
    assert template["meta"]["inherits_bono"] is False
    assert "codigoNcm" not in template["body"]
    assert "precoCusto" not in template["body"]
    assert "grupoCodigo" not in template["body"]


def test_compatibility_preserves_legacy_scripts():
    allowed, decision = validate_cost(
        2.65,
        {"source": "DFE", "cost_status": "RESOLVED"},
        allow_pending_dfe_cost=False,
    )
    assert allowed is True
    assert decision == "CUSTO_DFE"

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        request = compat_create_request(_analysis(), template={"body": {"codigoNcm": "00000000"}})
    assert request.body["codigoNcm"] == "19053100"
    assert request.body["codigoNcm"] != "00000000"
    assert request.body.get("cdCfopEntrada") is None
    assert "BONO" not in json.dumps(request.body)


def test_compatibility_post_product_reaches_facade(tmp_path, monkeypatch):
    called: dict[str, object] = {}

    def fake_post(self, client, reader, key, body, *, ean, from_code, pause_seconds=1.5):
        called["ean"] = ean
        called["from_code"] = from_code
        return "RESPONSE", None, None, None

    monkeypatch.setattr(ProductRegistrationService, "post_product", fake_post)
    outcome = compat_post_product(
        object(),
        object(),
        "fake",
        {"descricao": "X"},
        ean="7891000377130",
        checkpoint_path=tmp_path / "cp.json",
    )
    assert called["ean"] == "7891000377130"
    assert outcome[0] == "RESPONSE"


def test_legacy_lock_is_readable_without_rewrite(tmp_path):
    path = tmp_path / "wave_01_118508.json"
    original = {"postCount": 11, "executedAt": "2026-08-01T00:00:00Z"}
    path.write_text(json.dumps(original), encoding="utf-8")
    viewed = interpret_lock(json.loads(path.read_text(encoding="utf-8")))
    assert viewed["status"] == "COMPLETED"
    assert viewed["reexecution"] == "LOCKED"
    assert viewed["status_inferred"] is True
    assert json.loads(path.read_text(encoding="utf-8")) == original

    store = RegistrationLockStore(path)
    loaded = store.load()
    assert loaded["status"] == "COMPLETED"
    assert json.loads(path.read_text(encoding="utf-8")) == original


def test_new_lock_requires_explicit_status(tmp_path):
    store = RegistrationLockStore(tmp_path / "new_lock.json")
    with pytest.raises(ValueError, match="status explicito"):
        store.persist(
            status="",
            post_count=1,
            created=0,
            skipped=0,
            halted_reason=None,
            batch_id="x",
        )


def test_dry_run_does_not_write(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBPOSTO_CONVENIENCIA_24_HORAS_KEY", "fake-key-118508")

    class Gateway:
        called = False

        def post_once(self, *args, **kwargs):
            self.called = True
            raise AssertionError("dry-run nao pode postar")

    gateway = Gateway()
    checkpoint = tmp_path / "checkpoint.json"
    service = ProductRegistrationService(checkpoint, gateway=gateway)
    result = service.register(
        _request(),
        RiskAuthorization(accept_fiscal_risk=True, execute=False),
        env={"WEBPOSTO_CONVENIENCIA_24_HORAS_KEY": "fake-key-118508"},
    )
    assert result.post_enviado is False
    assert result.dry_run is True
    assert gateway.called is False
    assert not checkpoint.exists()


def test_register_execute_does_not_reach_gateway(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBPOSTO_CONVENIENCIA_24_HORAS_KEY", "fake-key-118508")

    class Gateway:
        called = False

        def post_once(self, *args, **kwargs):
            self.called = True
            raise AssertionError("API writes devem ser 0")

    service = ProductRegistrationService(tmp_path / "checkpoint.json", gateway=Gateway())
    with pytest.raises(RuntimeError, match="post_product"):
        service.register(
            _request(),
            RiskAuthorization(accept_fiscal_risk=True, execute=True),
            env={"WEBPOSTO_CONVENIENCIA_24_HORAS_KEY": "fake-key-118508"},
        )


def test_cli_execute_is_refused(monkeypatch):
    import importlib.util
    import sys

    path = ROOT / "scripts" / "product_registration.py"
    spec = importlib.util.spec_from_file_location("product_registration_cli_migration", path)
    cli = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = cli
    spec.loader.exec_module(cli)
    monkeypatch.setattr(
        cli.sys,
        "argv",
        [
            "product_registration.py",
            "--empresa",
            "118508",
            "--ean",
            "7891000377130",
            "--descricao",
            "TESTE",
            "--ncm",
            "19053100",
            "--preco-venda",
            "1",
            "--accept-fiscal-risk",
            "--execute",
            "register-one",
        ],
    )
    assert cli.main() == 5


def test_body_builder_legacy_import_still_exists():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        request = create_registration_request(_analysis())
    assert request.body["codigoExterno"] == "7891000377130"
    assert request.body_hash


def _module_import_hits(module: str) -> list[str]:
    hits: list[str] = []
    roots = (
        ROOT / "src" / "operational" / "product_registration",
        ROOT / "scripts",
        ROOT / "tests" / "unit",
    )
    for root in roots:
        for path in root.rglob("*.py"):
            if ".pytest" in str(path) or path.name == "test_registration_migration.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom) or not node.module:
                    continue
                if node.module == module or node.module.endswith(f".{module}"):
                    hits.append(str(path.relative_to(ROOT)).replace("\\", "/"))
                    break
    return sorted(hits)


def test_legacy_imports_are_mapped_and_contained():
    body_builder_hits = _module_import_hits("body_builder")
    assert body_builder_hits == [
        "src/operational/product_registration/compatibility.py",
        "src/operational/product_registration/service.py",
    ]
    assert "src/operational/product_registration/service.py" in _module_import_hits(
        "registration_executor"
    )
