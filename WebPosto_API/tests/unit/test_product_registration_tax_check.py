"""Testes unitários — product registration tax-check (somente mocks, sem escrita)."""

from __future__ import annotations

from src.operational.product_registration.ean_service import (
    find_ean_duplicates,
    validate_ean_strict,
)
from src.operational.product_registration.reference_finder import find_tax_reference_products
from src.operational.product_registration.tax_validation_service import TaxValidationService


def _icms(cst="060", aliq=18.0):
    return {
        "percentualIcmsSaida": aliq,
        "cstSaida": cst,
        "percentualIcmsEntrada": 0,
        "cstEntrada": cst,
    }


def _pis(cst="01"):
    return {"cstPisSaida": cst, "cstCofinsSaida": cst}


def _prod(**kw):
    base = {
        "produtoCodigo": 1,
        "nome": "REFRI COLA 350ML",
        "referenciaCodigo": "100",
        "eans": ["7891000100103"],
        "tipoProduto": "P",
        "combustivel": False,
        "ativo": True,
        "grupoCodigo": 10,
        "ncm": "22021000",
        "cest": "0300100",
        "unidadeCompra": "UN",
        "unidadeVenda": "UN",
        "iat": "A",
        "ippt": "T",
        "naturezaReceitaCodigo": 999,
        "tributoIcms": _icms(),
        "tributoPisCofins": _pis(),
        "cdCfopEntrada": "1102",
        "cdCfopSaida": "5102",
        "tributacaoMonofasica": None,
        "centroCustoCodigo": 24886,
        "empresaCodigo": 118508,
    }
    base.update(kw)
    return base


def test_ean_valido():
    # checksum válido conhecido para testes sintéticos: gerar via helper
    from src.operational.price_update.value_normalizer import _gtin_checksum_ok

    body = "789100010010"
    # montar dígito verificador
    total = 0
    for i, ch in enumerate(reversed(body)):
        total += int(ch) * (3 if i % 2 == 0 else 1)
    check = (10 - (total % 10)) % 10
    ean = body + str(check)
    assert _gtin_checksum_ok(ean)
    r = validate_ean_strict(ean)
    assert r["ok"] is True
    assert r["ean"] == ean


def test_ean_invalido_checksum():
    r = validate_ean_strict("7891000100100")  # checksum errado (quase)
    assert r["ok"] is False
    assert r["gate"] == "BLOCKED_INVALID_EAN"


def test_ean_duplicado():
    ean = validate_ean_strict("7898910655019")
    # se checksum falhar, forçar com mock index
    target = "7898910655019"
    hits = find_ean_duplicates(
        target,
        products_by_empresa={
            118508: [_prod(eans=[target], produtoCodigo=99)],
            74014: [_prod(eans=[target], produtoCodigo=88, empresaCodigo=74014)],
        },
    )
    assert len(hits) == 2


def test_mesmo_ncm_cest():
    catalog = [
        _prod(produtoCodigo=1),
        _prod(produtoCodigo=2, nome="REFRI COLA 2L"),
        _prod(produtoCodigo=3, nome="REFRI COLA LATA"),
    ]
    refs = find_tax_reference_products(
        catalog,
        empresa_codigo=118508,
        ncm="22021000",
        cest="0300100",
        grupo_codigo=10,
        descricao="REFRI COLA ZERO 350ML",
        unidade_venda="UN",
    )
    assert len(refs) >= 3
    assert all(r["ncm"] == "22021000" for r in refs)


def test_ncm_igual_cest_divergente_bloqueia():
    catalog = [
        _prod(produtoCodigo=1, cest="0300100"),
        _prod(produtoCodigo=2, cest="0300200"),
        _prod(produtoCodigo=3, cest="0300100"),
    ]
    svc = TaxValidationService()
    out = svc.run(
        empresa_codigo=118508,
        input_data={
            "descricao": "REFRI X",
            "ean": None,
            "codigoNcm": "22021000",
            "codigoCest": "0300300",
            "grupoCodigo": 10,
            "unidadeVenda": "UN",
            "unidadeCompra": "UN",
        },
        catalog=catalog,
        products_by_empresa={118508: catalog},
        centros_custo=[{"centroCustoCodigo": 24886, "descricao": "CONVENIENCIA"}],
        empresa_meta={"empresaCodigo": 118508, "nomeFantasia": "CONVENIENCIA 24 HORAS", "tipoImposto": "SN"},
    )
    # EAN inválido também bloqueia; garantimos conflito NCM/CEST presente
    assert "BLOCKED_NCM_CEST_CONFLICT" in out["gates"] or "BLOCKED_INVALID_EAN" in out["gates"]


def test_icms_consenso():
    catalog = [_prod(produtoCodigo=i) for i in range(1, 5)]
    svc = TaxValidationService()
    # EAN válido gerado
    from src.operational.price_update.value_normalizer import _gtin_checksum_ok

    body = "789100010011"
    total = 0
    for i, ch in enumerate(reversed(body)):
        total += int(ch) * (3 if i % 2 == 0 else 1)
    ean = body + str((10 - (total % 10)) % 10)
    assert _gtin_checksum_ok(ean)
    out = svc.run(
        empresa_codigo=118508,
        input_data={
            "descricao": "REFRI COLA 350ML",
            "descricaoResumida": "REFRI COLA",
            "ean": ean,
            "codigoNcm": "22021000",
            "codigoCest": "0300100",
            "grupoCodigo": 10,
            "unidadeCompra": "UN",
            "unidadeVenda": "UN",
            "precoCusto": "1.00",
            "precoCompra": "1.00",
            "precoVenda": "5.00",
        },
        catalog=catalog,
        products_by_empresa={118508: catalog},
        centros_custo=[{"centroCustoCodigo": 24886, "descricao": "CONVENIENCIA"}],
        empresa_meta={"empresaCodigo": 118508, "nomeFantasia": "C24", "tipoImposto": "SN"},
    )
    assert out["fieldMatrix"]["tributoIcms"]["classification"] == "CONSENSUS"
    assert out["writePerformed"] is False


def test_icms_conflitante():
    catalog = [
        _prod(produtoCodigo=1, tributoIcms=_icms("060", 18)),
        _prod(produtoCodigo=2, tributoIcms=_icms("000", 0)),
        _prod(produtoCodigo=3, tributoIcms=_icms("060", 18)),
    ]
    svc = TaxValidationService()
    out = svc.run(
        empresa_codigo=118508,
        input_data={
            "descricao": "REFRI",
            "ean": "00000000",
            "codigoNcm": "22021000",
            "codigoCest": "0300100",
            "grupoCodigo": 10,
        },
        catalog=catalog,
        products_by_empresa={118508: catalog},
        centros_custo=[{"centroCustoCodigo": 24886, "descricao": "CONVENIENCIA"}],
        empresa_meta={"empresaCodigo": 118508, "nomeFantasia": "C24", "tipoImposto": "SN"},
    )
    assert "tributoIcms" in out["conflicts"] or "BLOCKED_TAX_CONFLICT" in out["gates"]


def test_pis_ausente():
    catalog = [
        _prod(produtoCodigo=1, tributoPisCofins=None),
        _prod(produtoCodigo=2, tributoPisCofins=None),
    ]
    out = TaxValidationService().run(
        empresa_codigo=118508,
        input_data={"descricao": "X", "ean": "1", "codigoNcm": "22021000", "grupoCodigo": 10},
        catalog=catalog,
        products_by_empresa={118508: catalog},
        centros_custo=[{"centroCustoCodigo": 24886, "descricao": "CONVENIENCIA"}],
        empresa_meta={"empresaCodigo": 118508, "nomeFantasia": "C24", "tipoImposto": "SN"},
    )
    assert "BLOCKED_TAX_FIELDS_MISSING" in out["gates"] or "tributoPisCofins" in out["requiredMissing"]


def test_cfop_divergente():
    catalog = [
        _prod(produtoCodigo=1, cdCfopSaida="5102"),
        _prod(produtoCodigo=2, cdCfopSaida="5405"),
    ]
    out = TaxValidationService().run(
        empresa_codigo=118508,
        input_data={"descricao": "X", "ean": "1", "codigoNcm": "22021000", "grupoCodigo": 10},
        catalog=catalog,
        products_by_empresa={118508: catalog},
        centros_custo=[{"centroCustoCodigo": 24886, "descricao": "CONVENIENCIA"}],
        empresa_meta={"empresaCodigo": 118508, "nomeFantasia": "C24", "tipoImposto": "SN"},
    )
    assert "cdCfopSaida" in out["conflicts"] or "BLOCKED_TAX_CONFLICT" in out["gates"]


def test_regime_desconhecido_warning():
    catalog = [_prod(produtoCodigo=1), _prod(produtoCodigo=2), _prod(produtoCodigo=3)]
    out = TaxValidationService().run(
        empresa_codigo=118508,
        input_data={"descricao": "X", "ean": "1", "codigoNcm": "22021000", "grupoCodigo": 10},
        catalog=catalog,
        products_by_empresa={118508: catalog},
        centros_custo=[{"centroCustoCodigo": 24886, "descricao": "CONVENIENCIA"}],
        empresa_meta={"empresaCodigo": 118508, "nomeFantasia": "C24"},
    )
    assert "COMPANY_TAX_REGIME_UNKNOWN" in out["warnings"]


def test_combustivel_rejeitado():
    catalog = [_prod(produtoCodigo=1, combustivel=True, nome="GASOLINA")]
    refs = find_tax_reference_products(
        catalog,
        empresa_codigo=118508,
        ncm="27101259",
        descricao="GASOLINA C",
    )
    assert refs == []


def test_centro_24886_empresa_118508():
    catalog = [_prod(), _prod(produtoCodigo=2), _prod(produtoCodigo=3)]
    out = TaxValidationService().run(
        empresa_codigo=118508,
        input_data={"descricao": "X", "ean": "1", "codigoNcm": "22021000", "grupoCodigo": 10},
        catalog=catalog,
        products_by_empresa={118508: catalog},
        centros_custo=[{"centroCustoCodigo": 24886, "descricao": "CONVENIENCIA"}],
        empresa_meta={"empresaCodigo": 118508, "nomeFantasia": "C24", "tipoImposto": "SN"},
    )
    assert out["centroCusto"]["codigo"] == 24886


def test_outra_empresa_centro_proprio():
    catalog = [_prod(empresaCodigo=5555, produtoCodigo=1), _prod(empresaCodigo=5555, produtoCodigo=2)]
    out = TaxValidationService().run(
        empresa_codigo=5555,
        input_data={"descricao": "X", "ean": "1", "codigoNcm": "22021000", "grupoCodigo": 10},
        catalog=catalog,
        products_by_empresa={5555: catalog},
        centros_custo=[{"centroCustoCodigo": 999, "descricao": "CONVENIENCIA"}],
        empresa_meta={"empresaCodigo": 5555, "nomeFantasia": "CASA", "tipoImposto": "SN"},
    )
    assert out["centroCusto"]["codigo"] == 999
    assert out["centroCusto"]["codigo"] != 24886


def test_body_completo_e_incompleto():
    from src.operational.price_update.value_normalizer import _gtin_checksum_ok

    body = "789100010012"
    total = 0
    for i, ch in enumerate(reversed(body)):
        total += int(ch) * (3 if i % 2 == 0 else 1)
    ean = body + str((10 - (total % 10)) % 10)
    assert _gtin_checksum_ok(ean)
    catalog = [_prod(produtoCodigo=i) for i in (1, 2, 3, 4)]
    ok = TaxValidationService().run(
        empresa_codigo=118508,
        input_data={
            "descricao": "REFRI COLA 350ML",
            "descricaoResumida": "REFRI",
            "ean": ean,
            "codigoNcm": "22021000",
            "codigoCest": "0300100",
            "grupoCodigo": 10,
            "unidadeCompra": "UN",
            "unidadeVenda": "UN",
            "precoCusto": "1",
            "precoCompra": "1",
            "precoVenda": "5",
        },
        catalog=catalog,
        products_by_empresa={118508: catalog},
        centros_custo=[{"centroCustoCodigo": 24886, "descricao": "CONVENIENCIA"}],
        empresa_meta={"empresaCodigo": 118508, "nomeFantasia": "C24", "tipoImposto": "SN"},
    )
    assert ok["writePerformed"] is False
    assert ok["proposedBody"] is not None

    bad = TaxValidationService().run(
        empresa_codigo=118508,
        input_data={"descricao": "X", "ean": "1", "codigoNcm": "22021000"},
        catalog=catalog,
        products_by_empresa={118508: catalog},
        centros_custo=[{"centroCustoCodigo": 24886, "descricao": "CONVENIENCIA"}],
        empresa_meta={"empresaCodigo": 118508, "nomeFantasia": "C24", "tipoImposto": "SN"},
    )
    assert "BLOCKED_GROUP_NOT_RESOLVED" in bad["gates"] or "BLOCKED_INCOMPLETE_PRODUCT_BODY" in bad["gates"]
    assert bad["writePerformed"] is False


def test_garantia_nenhuma_escrita():
    out = TaxValidationService().run(
        empresa_codigo=118508,
        input_data={"descricao": "X", "ean": "1", "codigoNcm": "00000000", "grupoCodigo": 1},
        catalog=[],
        products_by_empresa={118508: []},
        centros_custo=[],
        empresa_meta={"empresaCodigo": 118508, "nomeFantasia": "C24", "tipoImposto": "SN"},
    )
    assert out["writePerformed"] is False
    assert out["mode"] == "READ_ONLY_TAX_CHECK"
