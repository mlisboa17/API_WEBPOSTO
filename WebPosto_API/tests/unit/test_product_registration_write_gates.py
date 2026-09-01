"""Gates de escrita do cadastro em massa da empresa 118508 (sem rede, sem escrita).

Cobre as protecoes que impedem repetir o incidente 2481344:
credencial por empresa, base fiscal aprovada e EANs permanentemente excluidos.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from src.core.config import OFFICIAL_COMPANY_CREDENTIAL_ALIASES
from src.operational.product_registration.company_credentials import (
    CompanyCredentialError,
    resolve_credential,
)
from src.operational.product_registration.product_family import family

ROOT = Path(__file__).resolve().parents[2]
EXECUTOR_PATH = ROOT / "scripts" / "execute_ready_products_118508.py"


def _load_executor_module():
    spec = importlib.util.spec_from_file_location("execute_ready_products_118508", EXECUTOR_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


executor_module = _load_executor_module()
Executor = executor_module.ProductRegistrationExecutor

BONO_EAN = "7891000376928"
INCIDENT_EAN = "7891962076317"


def _approved_product(ean: str = "7891000377130") -> dict:
    return {
        "ean": ean,
        "descricao": "BISCOITO NEGRESCO RECHEADO CHOCOLATE 90G",
        "preco_venda": 4.9,
        "grupo_codigo_api": 55446,
        "tax_basis_status": "APPROVED",
        "ncm": "19053100",
        "cest": "1705300",
        "tributoIcms": {"cstSaida": "060", "dsCsosnSaida": "0"},
        "tributoPisCofins": {"cstPisSaida": "01"},
        "cost_source": "DFE",
        "dfe_cost_evidence": {"numero": "2400289", "serie": "1", "precoCusto": 2.6517},
        "preco_custo": 2.6517,
        "body_preparado": {"precoCompra": 2.6517, "precoCusto": 2.6517},
    }


# --- Roteamento de credencial -------------------------------------------------


def test_118508_does_not_accept_74014_aliases():
    """A chave do Real Doze enxerga 118508 na API, mas nao pode resolver a empresa."""
    aliases_74014 = OFFICIAL_COMPANY_CREDENTIAL_ALIASES[74014]
    env = {alias: "key-real-doze" for alias in aliases_74014}

    with pytest.raises(CompanyCredentialError, match="Nenhuma credencial declarada"):
        resolve_credential(118508, env=env)

    for alias in aliases_74014:
        assert alias not in OFFICIAL_COMPANY_CREDENTIAL_ALIASES[118508]


def test_unknown_company_gets_no_generic_fallback():
    env = {
        "WEBPOSTO_API_KEY": "generic",
        "WEBPOSTO_TOKEN": "generic",
        "WEBPOSTO_CHAVE": "generic",
        "WEBPOSTO_CONVENIENCIA_24_HORAS_KEY": "key-118508",
    }

    with pytest.raises(CompanyCredentialError, match="nao possui aliases declarados"):
        resolve_credential(999999, env=env)


# --- Gate de base fiscal ------------------------------------------------------


def test_body_rejected_without_approved_tax_basis():
    product = _approved_product()
    product["tax_basis_status"] = "REVIEW_REQUIRED"

    with pytest.raises(ValueError, match="Base fiscal não aprovada"):
        Executor.rebuild_body(None, product)


def test_body_rejected_when_tax_basis_status_absent():
    product = _approved_product()
    del product["tax_basis_status"]

    with pytest.raises(ValueError, match="status=MISSING"):
        Executor.rebuild_body(None, product)


@pytest.mark.parametrize("field", ["ncm", "cest", "tributoIcms", "tributoPisCofins"])
def test_body_rejected_when_any_required_tax_field_missing(field):
    product = _approved_product()
    product[field] = None

    with pytest.raises(ValueError, match="Base fiscal incompleta"):
        Executor.rebuild_body(None, product)


def test_approved_body_keeps_critical_serialization():
    body = Executor.rebuild_body(None, _approved_product())

    assert body["codigoExterno"] == body["codigoBarras"] == "7891000377130"
    assert body["utilizaCodigoBarras"] is True
    assert body["Tributação Monofásica"] == 0
    assert body["codigoNcm"] == "19053100"
    assert body["centroCustoCodigo"] == 24886
    assert "empresaCodigo" not in body


# --- EANs permanentemente excluidos -------------------------------------------


@pytest.mark.parametrize("ean", [BONO_EAN, INCIDENT_EAN])
def test_permanently_excluded_eans_never_build_a_body(ean):
    product = _approved_product(ean=ean)

    with pytest.raises(ValueError, match="permanentemente excluído"):
        Executor.rebuild_body(None, product)


def test_loader_drops_bono_and_incident_product(tmp_path):
    payload = [
        {"ean": BONO_EAN, "descricao": "BONO", "classificacao_fase6": "READY_TO_CREATE"},
        {"ean": INCIDENT_EAN, "descricao": "SPECULOS", "classificacao_fase6": "READY_TO_CREATE"},
        {"ean": "7891000377130", "descricao": "NEGRESCO", "classificacao_fase6": "READY_TO_CREATE"},
        {"ean": "7896336000578", "descricao": "AMENDOIM", "classificacao_fase6": "REVIEW_REQUIRED"},
    ]
    source = tmp_path / "fase6.json"
    source.write_text(json.dumps(payload), encoding="utf-8")

    ready = Executor.load_ready_products(None, source)

    assert [p["ean"] for p in ready] == ["7891000377130"]


def test_incident_product_is_in_terminal_checkpoint_states():
    """Retomada nao pode reenviar item criado na empresa errada."""
    assert "CREATED_IN_WRONG_COMPANY" in executor_module.TERMINAL_CHECKPOINT_STATES
    assert "RESULT_UNKNOWN" in executor_module.TERMINAL_CHECKPOINT_STATES
    assert "POST_SENT" in executor_module.TERMINAL_CHECKPOINT_STATES


# --- Familia fiscal -----------------------------------------------------------


@pytest.mark.parametrize(
    "description,expected",
    [
        ("BISCOITO NEGRESCO RECHEADO CHOCOLATE 90G", "BISCOITOS"),
        ("BISCOITO COOKIE GAROTO CROCANTE 60GR", "BISCOITOS"),
        ("AMENDOIM ELMA CHIPS OVINHOS 65G", "AMENDOINS"),
        ("BATATA ORIGINAL RUFFLES 115G", "SALGADINHOS_INDUSTRIALIZADOS"),
        ("CHIPS DE BATATA DOCE 50G", "CHIPS_BATATA_DOCE"),
        ("CHIPS DE MACAXEIRA 45G", "CHIPS_MACAXEIRA"),
        ("CHIPS DE BANANA 50G", "CHIPS_BANANA"),
    ],
)
def test_family_classification_separates_root_vegetables_from_potato_snacks(description, expected):
    assert family(description) == expected
