"""Fila da onda e aderencia ao perfil aprovado (sem rede, sem escrita)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]


def _load_executor():
    """Carrega o executor por caminho: scripts/ nao e pacote importavel."""
    path = ROOT / "scripts" / "execute_wave_118508.py"
    spec = importlib.util.spec_from_file_location("execute_wave_118508", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


executor = _load_executor()

ICMS = {"cstIcmsSaida": "060"}
PIS = {"cstPisSaida": "01"}


def _profile(
    profile_id,
    *,
    level="PROFILE_C",
    eans,
    canary_status="PENDING",
    canary=None,
    ncm="19053100",
    cest="1705300",
    cfop_saida="5.405",
    icms=None,
):
    return {
        "profile_id": profile_id,
        "level": level,
        "ncms": [ncm],
        "cests": [cest] if cest else [],
        "tributo_icms": icms or ICMS,
        "tributo_pis_cofins": PIS,
        "cfop_entrada": "1.102",
        "cfop_saida": cfop_saida,
        "tributacao_monofasica": 0,
        "referencia_icms": "0000000061",
        "referencia_pis_cofins": "0000000007",
        "quantidade_candidatos": len(eans),
        "profile_canary_status": canary_status,
        "produto_canario": canary,
        "produtos": [{"ean": ean, "precoVenda": 5.0 + index} for index, ean in enumerate(eans)],
    }


def _body(**overrides):
    body = {
        "codigoNcm": "19053100",
        "codigoCest": "1705300",
        "tributoIcms": ICMS,
        "tributoPisCofins": PIS,
        "cdCfopEntrada": "1.102",
        "cdCfopSaida": "5.405",
        "Tributação Monofásica": 0,
    }
    body.update(overrides)
    return body


def test_first_product_of_a_pending_profile_is_the_canary():
    queue = executor.build_queue([_profile("P1", eans=["1", "2", "3"])], {"PROFILE_C"}, 20)

    assert [item["is_canary"] for item in queue] == [True, False, False]


def test_declared_canary_goes_first_even_if_not_the_cheapest():
    profile = _profile("P1", eans=["1", "2", "3"], canary="3")

    queue = executor.build_queue([profile], {"PROFILE_C"}, 20)

    assert queue[0]["product"]["ean"] == "3"
    assert queue[0]["is_canary"] is True


def test_verified_profile_does_not_need_a_new_canary():
    profile = _profile("P1", eans=["1", "2"], canary_status="VERIFIED")

    queue = executor.build_queue([profile], {"PROFILE_C"}, 20)

    assert [item["is_canary"] for item in queue] == [False, False]


def test_bigger_profiles_come_first_so_one_approval_yields_more():
    small = _profile("SMALL", eans=["1"])
    big = _profile("BIG", eans=["2", "3", "4"])

    queue = executor.build_queue([small, big], {"PROFILE_C"}, 20)

    assert [item["profile"]["profile_id"] for item in queue] == ["BIG", "BIG", "BIG", "SMALL"]


def test_limit_truncates_the_queue():
    queue = executor.build_queue([_profile("P1", eans=list("12345"))], {"PROFILE_C"}, 3)

    assert len(queue) == 3


def test_levels_outside_the_wave_are_not_queued():
    profile = _profile("PD", level="PROFILE_D", eans=["1"])

    assert executor.build_queue([profile], {"PROFILE_C"}, 20) == []


def test_body_aligned_with_the_profile_has_no_divergence():
    assert executor.body_matches_profile(_body(), _profile("P1", eans=["1"])) == []


def test_body_with_another_tax_basis_diverges_from_the_profile():
    divergences = executor.body_matches_profile(
        _body(tributoIcms={"cstIcmsSaida": "000"}), _profile("P1", eans=["1"])
    )

    assert divergences == ["tributoIcms"]


def test_body_with_another_ncm_or_cfop_diverges_from_the_profile():
    divergences = executor.body_matches_profile(
        _body(codigoNcm="19059090", cdCfopSaida="5.102"), _profile("P1", eans=["1"])
    )

    assert set(divergences) == {"ncm", "cfopSaida"}


def test_zero_cost_still_requires_the_explicit_flag(monkeypatch):
    monkeypatch.delenv(executor.PENDING_COST_FLAG, raising=False)
    ok, reason = executor.validate_cost(0, {"cost_status": "PENDING"})

    assert not ok
    assert reason == "CUSTO_ZERO_SEM_AUTORIZACAO_EXPLICITA"


def test_zero_cost_passes_with_flag_and_pending_status(monkeypatch):
    monkeypatch.setenv(executor.PENDING_COST_FLAG, "true")
    ok, reason = executor.validate_cost(0, {"cost_status": "PENDING"})

    assert ok
    assert reason == "CUSTO_ZERO_AUTORIZADO"


def test_positive_cost_without_dfe_origin_is_refused(monkeypatch):
    monkeypatch.setenv(executor.PENDING_COST_FLAG, "true")
    ok, reason = executor.validate_cost(3.5, {"source": "PENDING_DFE"})

    assert not ok
    assert reason == "CUSTO_POSITIVO_SEM_ORIGEM_DFE"


def test_profiles_with_the_same_payload_share_one_canary():
    """NCM diferente com a mesma tributacao nao exige dois canarios."""
    first = _profile("P1", eans=["1", "2"], ncm="19053100", cest="1705300")
    second = _profile("P2", eans=["3"], ncm="21069090", cest="1704400")

    queue = executor.build_queue([first, second], {"PROFILE_C"}, 20, by_payload=True)

    assert len({item["profile"]["profile_id"] for item in queue}) == 1
    assert [item["is_canary"] for item in queue] == [True, False, False]


def test_different_payloads_keep_separate_canaries():
    substituted = _profile("ST", eans=["1"], cfop_saida="5.405")
    taxed = _profile("TRIB", eans=["2"], cfop_saida="5.102", icms={"cstIcmsSaida": "000"})

    queue = executor.build_queue([substituted, taxed], {"PROFILE_C"}, 20, by_payload=True)

    assert [item["is_canary"] for item in queue] == [True, True]


def test_payload_grouping_keeps_the_source_profile_on_each_product():
    queue = executor.build_queue([_profile("P1", eans=["1"])], {"PROFILE_C"}, 20, by_payload=True)

    assert queue[0]["product"]["perfilFiscal"] == "P1"
    assert queue[0]["profile"]["profile_id"].startswith("PAYLOAD-")


def test_a_verified_member_satisfies_the_whole_payload():
    verified = _profile("P1", eans=["1"], canary_status="VERIFIED", canary="1")
    pending = _profile("P2", eans=["2"], ncm="21069090", cest="1704400")

    queue = executor.build_queue([verified, pending], {"PROFILE_C"}, 20, by_payload=True)

    assert all(item["is_canary"] is False for item in queue)


def test_payload_check_ignores_ncm_but_not_the_tax_fields():
    profile = _profile("P1", eans=["1"])

    assert executor.body_matches_payload(_body(codigoNcm="21069090"), profile) == []
    assert executor.body_matches_payload(_body(cdCfopSaida="5.102"), profile) == ["cfopSaida"]


def test_payload_with_cest_does_not_authorize_a_product_without_cest():
    profile = _profile("P1", eans=["1"])

    assert executor.body_matches_payload(_body(codigoCest=None), profile) == ["presencaDeCest"]


def test_monophasic_flag_is_part_of_the_payload():
    profile = _profile("P1", eans=["1"])

    divergences = executor.body_matches_payload(_body(**{"Tributação Monofásica": 1}), profile)

    assert divergences == ["tributacaoMonofasica"]


def test_retry_after_is_respected_within_bounds():
    def response(header):
        return httpx.Response(429, headers={"Retry-After": header} if header else {})

    assert executor.retry_after_seconds(response("12")) == 12.0
    assert executor.retry_after_seconds(response("0")) == 1.0
    assert executor.retry_after_seconds(response("9999")) == 60.0
    assert executor.retry_after_seconds(response("nao-numerico")) == 5.0
    assert executor.retry_after_seconds(response(None)) == 5.0


class FakeClient:
    """Devolve, em ordem, respostas ou excecoes previamente combinadas."""

    def __init__(self, behaviours):
        self.behaviours = list(behaviours)
        self.calls = 0

    def post(self, *args, **kwargs):
        self.calls += 1
        behaviour = self.behaviours.pop(0)
        if isinstance(behaviour, Exception):
            raise behaviour
        return behaviour


class FakeReader:
    def __init__(self, rows):
        self.rows = rows
        self.reads = 0

    def get_catalog(self, key, cursor=0, page_size=200):
        self.reads += 1
        return [row for row in self.rows if int(row["produtoCodigo"]) > cursor][:page_size]


def _catalog_row(code, ean):
    return {"produtoCodigo": code, "produtoCodigoBarra": [{"codigoBarra": ean}]}


def test_timeout_with_the_product_already_created_never_resends(monkeypatch):
    monkeypatch.setattr(executor.time, "sleep", lambda _: None)
    client = FakeClient([httpx.ReadTimeout("estourou")])
    reader = FakeReader([_catalog_row(2481600, "7891000000017")])

    outcome, response, recovered, error = executor.send_product(
        client, reader, "k", _body(), ean="7891000000017", from_code=2481500
    )

    assert outcome == "TIMEOUT_BUT_CREATED"
    assert client.calls == 1
    assert recovered["produtoCodigo"] == 2481600
    assert response is None
    assert "estourou" in error


def test_timeout_only_resends_after_proving_the_product_is_absent(monkeypatch):
    monkeypatch.setattr(executor.time, "sleep", lambda _: None)
    client = FakeClient([httpx.ReadTimeout("1"), httpx.ReadTimeout("2"), httpx.ReadTimeout("3")])
    reader = FakeReader([_catalog_row(2481600, "outro-ean")])

    outcome, _, _, _ = executor.send_product(
        client, reader, "k", _body(), ean="7891000000017", from_code=2481500
    )

    assert outcome == "TIMEOUT_UNCONFIRMED"
    assert client.calls == 3
    assert reader.reads >= 3


def test_a_429_is_awaited_and_then_the_post_succeeds(monkeypatch):
    waited = []
    monkeypatch.setattr(executor.time, "sleep", waited.append)
    client = FakeClient(
        [httpx.Response(429, headers={"Retry-After": "3"}), httpx.Response(200, json={})]
    )

    outcome, response, _, _ = executor.send_product(
        client, FakeReader([]), "k", _body(), ean="7891000000017", from_code=1
    )

    assert outcome == "RESPONSE"
    assert response.status_code == 200
    assert waited == [3.0]


def _candidate(**overrides):
    product = {
        "ean": "7891000377130",
        "descricao": "BISCOITO RECHEADO CHOCOLATE 90G",
        "ncm": "19053100",
        "cest": "1705300",
        "familiaComercial": "BISCOITO",
        "precoVenda": 4.9,
    }
    product.update(overrides)
    return product


def test_a_common_product_passes_the_gate():
    assert executor.product_gate(_candidate()) is None


def test_truncated_brazilian_gtin_is_gated_out():
    reason = executor.product_gate(_candidate(ean="789607405141"))

    assert reason.startswith("GTIN_INCOERENTE_COM_O_PREFIXO")


def test_smoking_related_item_is_sent_to_wave_four():
    reason = executor.product_gate(
        _candidate(descricao="CARVAO PARA NARGUILE DISCO 10UN", ncm="44029000")
    )

    assert reason == "CATEGORIA_ESPECIAL_DA_ONDA_4:TABACARIA_CORRELATO"


def test_tobacco_counter_family_is_sent_to_wave_four():
    reason = executor.product_gate(
        _candidate(descricao="ISQUEIRO GRANDE", ncm="96131000", familiaComercial="TABACARIA")
    )

    assert reason == "CATEGORIA_ESPECIAL_DA_ONDA_4:TABACARIA"


def test_gated_products_do_not_consume_a_slot():
    profile = _profile("P1", eans=["789607405141", "7891000377130", "7891000377131"])
    for product, ean in zip(profile["produtos"], profile["produtos"]):
        product.update(_candidate(ean=ean["ean"]))
    rejected = []

    queue = executor.build_queue(
        [profile], {"PROFILE_C"}, 2, gate=executor.product_gate, rejected=rejected
    )

    assert [item["product"]["ean"] for item in queue] == ["7891000377130", "7891000377131"]
    assert [entry["ean"] for entry in rejected] == ["789607405141"]


def test_the_canary_is_the_first_product_actually_sent():
    """Se o primeiro da lista sai pelo gate, o canario passa a ser o proximo."""
    profile = _profile("P1", eans=["789607405141", "7891000377130"])
    for product in profile["produtos"]:
        product.update(_candidate(ean=product["ean"]))

    queue = executor.build_queue([profile], {"PROFILE_C"}, 5, gate=executor.product_gate)

    assert queue[0]["product"]["ean"] == "7891000377130"
    assert queue[0]["is_canary"] is True


def test_recent_search_stops_when_the_catalog_ends():
    reader = FakeReader([_catalog_row(10, "a"), _catalog_row(11, "b")])

    assert executor.find_recent_by_ean(reader, "k", "ausente", 5) is None
