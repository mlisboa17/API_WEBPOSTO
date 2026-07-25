from src.gateway.webposto_client import WebPostoClient


ROWS = [
    {"empresaCodigo": 11495, "valor": 1},
    {"empresaCodigo": 5555, "valor": 2},
    {"empresaCodigo": 74014, "valor": 3},
    {"empresaCodigo": 5256, "valor": 4},
    {"empresaCodigo": None, "valor": 5},
]


def test_network_payload_excludes_unlicensed_companies():
    result = WebPostoClient._scope_network_payload(ROWS)

    assert {row["empresaCodigo"] for row in result} == {11495, 5555, 74014}


def test_network_payload_honors_requested_licensed_company():
    result = WebPostoClient._scope_network_payload({"resultados": ROWS}, 74014)

    assert result["resultados"] == [{"empresaCodigo": 74014, "valor": 3}]


def test_invalid_requested_company_cannot_expand_scope():
    result = WebPostoClient._scope_network_payload({"data": ROWS}, 5256)

    assert {row["empresaCodigo"] for row in result["data"]} == {11495, 5555, 74014}
