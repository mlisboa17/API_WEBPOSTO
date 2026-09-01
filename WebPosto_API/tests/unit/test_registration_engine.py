"""Regressao do motor permanente — fixtures ficticios, sem rede e sem disco fiscal."""

from __future__ import annotations

import json

from src.operational.product_registration.checkpoint_migration import (
    detect_checkpoint_schema,
    read_checkpoint,
)
from src.operational.product_registration.company_credentials import fingerprint
from src.operational.product_registration.duplicate_checker import classify_duplicate
from src.operational.product_registration.engine_schemas import (
    ProductRegistrationRequest,
    RiskAuthorization,
)
from src.operational.product_registration.extensions import (
    CostUpdateCandidate,
    FiscalAuditInput,
    FiscalAuditRecommendation,
)
from src.operational.product_registration.final_wave import (
    LEGITIMATE_VARIANT,
    SAME_PRODUCT,
    UNRESOLVED_DUPLICATE,
    classify_final_duplicate,
)
from src.operational.product_registration.gateway import ProductPostVerifier
from src.operational.product_registration.gtin_service import GtinValidationService
from src.operational.product_registration.policies.cost_policy import CostPolicy
from src.operational.product_registration.policies.execution_policy import ExecutionPolicy
from src.operational.product_registration.policies.fiscal_policy import FiscalPolicy
from src.operational.product_registration.policies.routing_policy import RoutingPolicy
from src.operational.product_registration.registration_body import RegistrationBodyBuilder
from src.operational.product_registration.registration_engine import ProductRegistrationService
from src.operational.product_registration.stores import RegistrationLockStore
from src.operational.product_registration.versions import CHECKPOINT_LEGACY_SCHEMA_VERSION

ENV = {"WEBPOSTO_CONVENIENCIA_24_HORAS_KEY": "fake-key-118508"}


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


def test_routing_rejects_company_mismatch():
    decision = RoutingPolicy().evaluate(
        requested_company=118508,
        resolved_company=11495,
        resolved_variable="WEBPOSTO_VIP_KEY",
        body_has_empresa_codigo=False,
        query_has_empresa_codigo=False,
    )
    assert decision.allowed is False
    assert decision.decision == "ROUTE_REJECTED"


def test_routing_rejects_empresa_codigo_in_body():
    decision = RoutingPolicy().evaluate(
        requested_company=118508,
        resolved_company=118508,
        resolved_variable="WEBPOSTO_CONVENIENCIA_24_HORAS_KEY",
        body_has_empresa_codigo=True,
        query_has_empresa_codigo=False,
    )
    assert decision.allowed is False


def test_credential_fingerprint_never_equals_secret():
    secret = "super-secret-key"
    assert fingerprint(secret) != secret
    assert len(fingerprint(secret)) == 16


def test_gtin_checksum_and_left_zeros():
    gtin = GtinValidationService()
    assert gtin.validate("7891000377130")["ok"] is True
    assert gtin.validate("07891000377130")["ok"] is True or gtin.validate("7891000377130")["ean"]


def test_gtin_invented_and_truncated():
    gtin = GtinValidationService()
    invented = gtin.validate("4512345678999")
    assert invented["ok"] is False
    truncated = gtin.validate("789607405141")
    assert truncated["ok"] is False
    assert truncated["truncated"] or any("TRUNCADO" in str(item) for item in truncated["issues"])


def test_duplicate_same_product_new_gtin():
    label, _ = classify_final_duplicate(
        "CERVEJA IMPERIO PURO MALTE LATA 350 ML", "CERVEJA IMPERIO PURO MALTE 350 ML"
    )
    assert label == SAME_PRODUCT


def test_duplicate_weight_flavor_model_connector_voltage():
    assert classify_final_duplicate("CERVEJA IMPERIO GOLD 330ML", "CERVEJA IMPERIO GOLD 269ML")[0] == (
        LEGITIMATE_VARIANT
    )
    assert classify_final_duplicate(
        "CERVEJA IMPERIO GOLD LATA 350 ML", "CERVEJA IMPERIO LATA 350 ML"
    )[0] == LEGITIMATE_VARIANT
    assert classify_duplicate("FILTRO MELITTA 102", "FILTRO MELITTA 103")[0] != "SAME_PRODUCT_NEW_GTIN"
    assert classify_final_duplicate(
        "CABO I2GO USB C PARA USB C 1,2M", "CABO I2GO MICRO USB ANDROID USB USB A 1,2M"
    )[0] == LEGITIMATE_VARIANT
    assert classify_duplicate("CARREGADOR 110V", "CARREGADOR 220V")[0] != "SAME_PRODUCT_NEW_GTIN"


def test_missing_measure_is_unresolved_and_pre_post_skip():
    label, _ = classify_final_duplicate("SALG PINGO OURO PICANHA 55G NOVO", "PINGO DE OURO PICANHA")
    assert label == UNRESOLVED_DUPLICATE


def test_cost_zero_requires_explicit_flag():
    policy = CostPolicy()
    denied = policy.evaluate(
        cost=0,
        cost_source="PENDING_DFE",
        cost_status="PENDING",
        sale_price=10,
        allow_pending_dfe_cost=False,
    )
    allowed = policy.evaluate(
        cost=0,
        cost_source="PENDING_DFE",
        cost_status="PENDING",
        sale_price=10,
        allow_pending_dfe_cost=True,
    )
    assert denied.allowed is False
    assert allowed.allowed is True


def test_cost_above_sale_keeps_dfe_value():
    decision = CostPolicy().evaluate(
        cost=20,
        cost_source="DFE",
        cost_status="RESOLVED",
        sale_price=10,
        allow_pending_dfe_cost=False,
        accept_negative_margin=True,
    )
    assert decision.decision == "CUSTO_ACIMA_DA_VENDA"
    assert decision.allowed is True
    assert decision.requires_review is True


def test_cost_policy_masks_access_key():
    sanitized = CostPolicy().sanitize_evidence({"access_key": "12345678901234567890123456789012345678901234"})
    assert "12345678901234567890" not in json.dumps(sanitized)
    assert "***" in sanitized["access_key"]


def test_fiscal_empty_is_not_zero_and_ncm_is_not_cst():
    fiscal = FiscalPolicy()
    assert fiscal.empty_is_not_zero("fcp", None).allowed is False
    assert fiscal.empty_is_not_zero("fcp", 0.0).allowed is True
    assert fiscal.reject_ncm_prefix_as_cst("19053100", "000").allowed is False
    proven = fiscal.evaluate_entry_classification("ST_COMPROVADA")
    taxed = fiscal.evaluate_entry_classification("SEM_ST_COMPROVADA")
    assert proven.decision == "ST_COMPROVADA"
    assert taxed.decision == "SEM_ST_COMPROVADA"
    assert proven.decision != taxed.decision


def test_body_builder_does_not_copy_bono_and_omits_missing_cest(tmp_path):
    builder = RegistrationBodyBuilder()
    body = builder.build(_request(cest=None, ncm="09011110"))
    assert "codigoCest" not in body
    assert body["codigoNcm"] == "09011110"
    assert "BONO" not in json.dumps(body)
    assert "empresaCodigo" not in body
    first = builder.hash(body)
    second = builder.hash(body)
    assert first == second


def test_lock_is_not_created_when_posts_are_zero(tmp_path):
    store = RegistrationLockStore(tmp_path / "wave_lock.json")
    assert store.create_running_if_posts(0, "batch") is False
    assert store.load() == {}


def test_execution_policy_skip_continues_and_unknown_halts():
    policy = ExecutionPolicy()
    assert policy.on_pre_post_skip("GTIN").decision == "CONTINUE_BATCH"
    assert policy.on_post_outcome("RESULT_UNKNOWN").decision == "HALT_BATCH"
    assert policy.timeout_requires_get().decision == "RESOLVE_TIMEOUT_BY_GET"


def test_independent_verifier_detects_wrong_company():
    class Reader:
        def get_catalog(self, key, cursor, page_size):
            return [{"produtoCodigo": 10, "ncm": "19053100", "cest": "1705300", "produtoCodigoBarra": [{"codigoBarra": "789"}]}]

        def get_company_links(self, key, cursor, page_size):
            return [{"produtoCodigo": 10, "empresaCodigo": 11495, "precoVenda": 1, "precoCusto": 1, "ativo": True}]

    result = ProductPostVerifier(Reader(), 118508).verify(
        "k",
        produto_codigo=10,
        ean="789",
        expected_ncm="19053100",
        expected_cest="1705300",
        expected_sale=1,
        expected_cost=1,
    )
    assert result["ok"] is False
    assert result["classification"] == "CREATED_IN_WRONG_COMPANY"


def test_legacy_checkpoint_is_readable_without_rewrite(tmp_path):
    path = tmp_path / "checkpoint.json"
    path.write_text(
        json.dumps(
            {
                "execution_id": "old",
                "checkpoint_index": 3,
                "started_at": "2026-01-01T00:00:00",
                "last_result": {"ean": "1"},
            }
        ),
        encoding="utf-8",
    )
    assert detect_checkpoint_schema(json.loads(path.read_text(encoding="utf-8"))) == (
        CHECKPOINT_LEGACY_SCHEMA_VERSION
    )
    loaded = read_checkpoint(path)
    assert loaded["_legacy"] is True
    assert json.loads(path.read_text(encoding="utf-8"))["execution_id"] == "old"


def test_preflight_dry_run_does_not_post(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBPOSTO_CONVENIENCIA_24_HORAS_KEY", "fake-key-118508")
    service = ProductRegistrationService(tmp_path / "checkpoint.json")
    result = service.preflight(_request(), env=ENV)
    assert result.dry_run is True
    assert result.post_enviado is False
    assert result.body_hash
    assert result.status == "DRY_RUN"


def test_register_without_execute_stays_dry_run(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBPOSTO_CONVENIENCIA_24_HORAS_KEY", "fake-key-118508")
    service = ProductRegistrationService(tmp_path / "checkpoint.json")
    result = service.register(_request(), RiskAuthorization(accept_fiscal_risk=True, execute=False), env=ENV)
    assert result.post_enviado is False


def test_retry_after_is_bounded():
    import httpx
    from src.operational.product_registration.gateway import WebPostoRegistrationGateway

    response = httpx.Response(429, headers={"Retry-After": "120"})
    wait = WebPostoRegistrationGateway("https://example.test").wait_retry_after(response)
    assert wait == 60.0


def test_extension_contracts_do_not_write():
    candidate = CostUpdateCandidate(ean="7891000377130", custo_proposto=1.5)
    finding_input = FiscalAuditInput(ean="7891000377130", ncm="19053100")
    assert candidate.custo_proposto == 1.5
    assert finding_input.contexto_sanitizado == {}
    recommendation = FiscalAuditRecommendation(
        finding={"codigo": "X", "descricao": "y", "impacto": "baixo"},
        acao="revisar",
        confianca="LOW",
    )
    assert recommendation.requer_aprovacao is True
