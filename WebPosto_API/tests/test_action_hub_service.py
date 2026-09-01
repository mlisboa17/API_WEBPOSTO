"""Action Hub: ciclo de vida local, economia realizada e writes = 0."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1.endpoints import conveniencia_ia_ops as ia_ops_ep
from src.services.ai_ops.action_hub_service import ActionHubService, referencia_acao
from src.services.ai_ops.models import connect_action_hub_db
from src.services.ai_ops.schemas import UpdateActionStatus
from src.services.webposto.schemas import WEBPOSTO_WRITES

CPF = "12345678901"


def _item(
    *,
    empresa: int = 118508,
    agente: str = "FinanceiroIA",
    codigo: str = "QUEBRA_CAIXA",
    produto: int | None = None,
    descricao: str = "Caixa P1 · dinheiro 80.00",
    impacto: float = 100.0,
    ganho: float = 80.0,
) -> SimpleNamespace:
    return SimpleNamespace(
        empresa_codigo=empresa,
        agente=agente,
        codigo_diagnostico=codigo,
        produto_codigo=produto,
        descricao=descricao,
        impacto_financeiro_reais=impacto,
        ganho_estimado_reais=ganho,
        ean=None,
    )


def test_sync_upsert_is_deterministic(tmp_path: Path) -> None:
    db = str(tmp_path / "logos_local.db")
    hub = ActionHubService(db_path=db)
    first = hub.sync_from_items([_item(), _item()])
    second = hub.sync_from_items([_item(impacto=120, ganho=90)])
    listed = hub.list(empresa_codigo=118508)
    assert listed.total == 1
    assert listed.webposto_writes == WEBPOSTO_WRITES == 0
    assert listed.items[0].impacto_financeiro_reais == 120
    assert listed.items[0].status == "PENDENTE"
    assert first >= 1
    assert second >= 0
    assert referencia_acao(_item()) == "CAIXA:P1"


def test_sync_isolates_official_empresas(tmp_path: Path) -> None:
    db = str(tmp_path / "logos_local.db")
    hub = ActionHubService(db_path=db)
    hub.sync_from_items(
        [
            _item(empresa=118508, produto=10, descricao="SKU loja"),
            _item(empresa=5555, produto=10, descricao="SKU pista"),
            _item(empresa=11495, produto=11, descricao="SKU vip", agente="CompradorIA", codigo="RUPTURA"),
            _item(empresa=74014, produto=12, descricao="SKU doze", agente="ProdutoIA", codigo="EAN_INVALIDO"),
            _item(empresa=999, produto=99, descricao="fora"),
        ]
    )
    rede = hub.list(rede=True)
    assert sorted({item.empresa_codigo for item in rede.items}) == [5555, 11495, 74014, 118508]
    pista = hub.list(empresa_codigo=5555)
    assert pista.total == 1
    assert pista.items[0].identificador_referencia == "SKU:10"
    assert pista.items[0].empresa_codigo == 5555


def test_transition_and_economia_realizada(tmp_path: Path) -> None:
    db = str(tmp_path / "logos_local.db")
    hub = ActionHubService(db_path=db)
    hub.sync_from_items(
        [
            _item(ganho=80, impacto=100),
            _item(empresa=11495, produto=7, descricao="VIP", ganho=40, impacto=50, agente="TaxAdvisorIA", codigo="FCP_PE"),
        ]
    )
    pending = hub.list(status="PENDENTE")
    first = pending.items[0]
    mid = hub.update(first.id, UpdateActionStatus(status="EM_ANDAMENTO"), ator="auditor")
    assert mid.status == "EM_ANDAMENTO"
    done = hub.update(first.id, UpdateActionStatus(status="RESOLVIDO", justificativa="conferido no caixa"), ator="auditor")
    assert done.status == "RESOLVIDO"
    assert done.resolvido_em
    assert done.webposto_writes == 0
    metrics = hub.metrics(rede=True, periodo_inicio=date.today().replace(day=1), periodo_fim=date.today())
    assert metrics.economia_realizada_reais == 80
    assert metrics.impacto_recuperado_reais == 100
    assert metrics.tarefas_resolvidas == 1
    assert metrics.tarefas_pendentes == 1
    assert metrics.webposto_writes == 0
    with connect_action_hub_db(db) as conn:
        leftover = conn.execute(
            "SELECT COUNT(*) AS n FROM webposto_action_hub_tasks WHERE status='PENDENTE'"
        ).fetchone()["n"]
    assert leftover == 1


def test_justificado_requires_text_and_blocks_invalid_transition(tmp_path: Path) -> None:
    db = str(tmp_path / "logos_local.db")
    hub = ActionHubService(db_path=db)
    hub.sync_from_items([_item(descricao=f"cliente {CPF}")])
    task = hub.list().items[0]
    assert CPF not in task.descricao
    try:
        hub.update(task.id, UpdateActionStatus(status="JUSTIFICADO"))
        raise AssertionError("deveria exigir justificativa")
    except ValueError:
        pass
    closed = hub.update(task.id, UpdateActionStatus(status="JUSTIFICADO", justificativa="falso positivo do turno"))
    assert closed.status == "JUSTIFICADO"
    try:
        hub.update(task.id, UpdateActionStatus(status="EM_ANDAMENTO"))
        raise AssertionError("não reabre tarefa justificada")
    except PermissionError:
        pass
    metrics = hub.metrics(empresa_codigo=118508)
    assert metrics.economia_realizada_reais == 0
    assert metrics.tarefas_justificadas == 1


def test_action_hub_endpoints(tmp_path: Path) -> None:
    db = str(tmp_path / "logos_local.db")
    hub = ActionHubService(db_path=db)
    hub.sync_from_items([_item(produto=88, descricao="SKU 88", ganho=25, impacto=30)])
    ia_ops_ep.configure_services(action_hub=hub)
    app = FastAPI()
    app.include_router(ia_ops_ep.router)
    client = TestClient(app)
    listed = client.get("/api/v1/conveniencia/ia-ops/actions", params={"empresa_codigo": 118508})
    assert listed.status_code == 200
    body = listed.json()
    assert body["webposto_writes"] == 0
    assert body["total"] == 1
    task_id = body["items"][0]["id"]
    assumed = client.patch(
        f"/api/v1/conveniencia/ia-ops/actions/{task_id}",
        json={"status": "EM_ANDAMENTO"},
    )
    assert assumed.status_code == 200
    assert assumed.json()["status"] == "EM_ANDAMENTO"
    resolved = client.patch(
        f"/api/v1/conveniencia/ia-ops/actions/{task_id}",
        json={"status": "RESOLVIDO", "justificativa": "glosa aplicada"},
    )
    assert resolved.status_code == 200
    metrics = client.get("/api/v1/conveniencia/ia-ops/actions/metrics", params={"empresa_codigo": 118508})
    assert metrics.status_code == 200
    payload = metrics.json()
    assert payload["webposto_writes"] == 0
    assert payload["economiaRealizadaReais"] == 25
    assert payload["tarefasResolvidas"] == 1
    assert payload["tarefasPendentes"] == 0
    denied = client.patch(
        f"/api/v1/conveniencia/ia-ops/actions/{task_id}",
        json={"status": "PENDENTE"},
    )
    assert denied.status_code == 409
    missing = client.patch("/api/v1/conveniencia/ia-ops/actions/nao-existe", json={"status": "EM_ANDAMENTO"})
    assert missing.status_code == 404
