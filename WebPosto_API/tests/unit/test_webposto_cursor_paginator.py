from src.models.error_model import WebPostoError
from src.models.response_model import WebPostoResponse
from src.services.webposto_cursor_paginator import WebPostoCursorPaginator


def row(code: int) -> dict:
    return {"codigo": code, "empresaCodigo": 11495, "vendaItemCodigo": code}


class FakeClient:
    def __init__(self, batches):
        self.batches = list(batches)
        self.calls = []

    async def call_endpoint(self, key, params):
        self.calls.append((key, dict(params)))
        if key == "venda_item_rede":
            return WebPostoResponse.fail(WebPostoError(status=401, type="UNAUTHORIZED"))
        return WebPostoResponse.ok(self.batches.pop(0))


async def test_collects_list_payload_using_last_codigo_as_cursor() -> None:
    client = FakeClient([[row(1), row(2)], [row(3)]])
    paginator = WebPostoCursorPaginator(client, batch_size=2)

    response = await paginator.collect("venda_item_rede", "venda_item", {"empresaCodigo": 11495})

    assert response.success is True
    assert [item["codigo"] for item in response.data["resultados"]] == [1, 2, 3]
    assert response.data["pagination"]["complete"] is True
    assert response.data["pagination"]["termination"] == "SHORT_BATCH"
    fallback_calls = [params for key, params in client.calls if key == "venda_item"]
    assert fallback_calls[1]["ultimoCodigo"] == 2


async def test_rejects_stalled_cursor_instead_of_returning_partial_total() -> None:
    client = FakeClient([[row(1), row(2)], [row(2), row(2)]])
    paginator = WebPostoCursorPaginator(client, batch_size=2)

    response = await paginator.collect("venda_item_rede", "venda_item", {})

    assert response.success is False
    assert response.error is not None
    assert response.error.type == "CURSOR_STALLED"


async def test_rejects_safety_limit_without_completion_proof() -> None:
    client = FakeClient([[row(1), row(2)]])
    paginator = WebPostoCursorPaginator(client, max_pages=1, batch_size=2)

    response = await paginator.collect("venda_item_rede", "venda_item", {})

    assert response.success is False
    assert response.error is not None
    assert response.error.type == "PAGINATION_SAFETY_LIMIT"


async def test_supports_endpoint_specific_cursor_field() -> None:
    class MovementClient:
        def __init__(self):
            self.calls = []
            self.batches = [
                [{"movimentoContaCodigo": 10}, {"movimentoContaCodigo": 20}],
                [{"movimentoContaCodigo": 21}],
            ]

        async def call_endpoint(self, key, params):
            self.calls.append(dict(params))
            return WebPostoResponse.ok(self.batches.pop(0))

    client = MovementClient()
    response = await WebPostoCursorPaginator(client, batch_size=2).collect(
        "movimento_conta", "movimento_conta", {}, cursor_field="movimentoContaCodigo"
    )

    assert response.success is True
    assert client.calls[1]["ultimoCodigo"] == 20
