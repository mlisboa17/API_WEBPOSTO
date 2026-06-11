"""Testes F05.3 — Executive AI Copilot."""
from __future__ import annotations

import pytest

from src.services.executive_ai_copilot_service import (
    ExecutiveAiCopilotService,
    QUESTION_CATALOG,
)


def test_question_catalog_has_ten_homologated():
    assert len(QUESTION_CATALOG) == 10


def test_governance_blocks_meta_funcionario():
    svc = ExecutiveAiCopilotService()
    layers = svc._load_knowledge_layers("2026-06-01", "2026-06-07")
    block = svc._governance_block("metas por operador metaFuncionario", layers, None)
    assert block is not None


def test_governance_blocks_filial_9999():
    svc = ExecutiveAiCopilotService()
    layers = svc._load_knowledge_layers("2026-06-01", "2026-06-07")
    block = svc._governance_block("como está a filial 9999?", layers, None)
    assert block is not None


def test_reasoning_catalog_all_have_confidence_and_lineage():
    svc = ExecutiveAiCopilotService()
    layers = svc._load_knowledge_layers("2026-06-01", "2026-06-07")
    reasoning = svc._executive_reasoning_engine(layers)
    for item in reasoning["catalog"]:
        assert item.get("confidenceLevel")
        assert item.get("lineage") is not None


def test_recommendation_never_roi_realizado_without_evidence():
    svc = ExecutiveAiCopilotService()
    layers = svc._load_knowledge_layers("2026-06-01", "2026-06-07")
    recs = svc._recommendation_engine(layers)
    for rec in recs["recommendations"]:
        if rec.get("roiLabel") == "ROI_REALIZADO":
            assert rec.get("roiRealizado") is not None
        if "FRÁGIL" in (rec.get("labels") or []):
            assert rec.get("roiLabel") != "ROI_REALIZADO"


@pytest.mark.asyncio
async def test_ask_homologated_question():
    svc = ExecutiveAiCopilotService()
    resp = await svc.ask("Onde estamos perdendo dinheiro?", "2026-06-01", "2026-06-07")
    assert resp.success, resp.error
    answer = resp.data["resposta"]
    assert answer.get("confidenceLevel")
    assert answer.get("lineage")
    assert answer.get("evidenceSource") is not None


@pytest.mark.asyncio
async def test_build_full_payload():
    svc = ExecutiveAiCopilotService()
    resp = await svc.build("2026-06-01", "2026-06-07")
    assert resp.success, resp.error
    data = resp.data
    assert data["sprint"] == "F05.3"
    assert data["fonte"]["webPosto"] is False
    qa = data["qa"]
    assert qa["semCrossTenant"] is True
    assert qa["semRespostaSemConfidence"] is True
    assert qa["semRoiSemOrigem"] is True
    ex = data["executiveAnswers"]
    assert ex["5_perguntasHomologadas"] == 10
    assert ex["16_auditavel"] is True
    assert data["parecerFinal"].startswith("[PARECER FINAL:")
