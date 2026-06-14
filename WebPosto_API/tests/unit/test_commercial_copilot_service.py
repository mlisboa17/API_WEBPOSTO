"""Testes F07.9 — Commercial Copilot & Executive Advisor."""
from __future__ import annotations

import pytest

from src.services.commercial_copilot_service import (
    CommercialCopilotService,
    QUESTION_CATALOG,
)


def test_question_catalog_has_ten_homologated():
    assert len(QUESTION_CATALOG) == 10


def test_governance_blocks_promotion_question():
    svc = CommercialCopilotService()
    layers = svc._load_knowledge_layers("2026-06-01", "2026-06-07", None)
    block = svc._governance_block("Quem merece promoção?", layers, None)
    assert block is not None


def test_reasoning_catalog_all_have_confidence_and_lineage():
    svc = CommercialCopilotService()
    layers = svc._load_knowledge_layers("2026-06-01", "2026-06-07", None)
    if not layers.get("hasSnapshots"):
        pytest.skip("snapshots homologados ausentes")
    reasoning = svc._commercial_reasoning_engine(layers)
    for item in reasoning["catalog"]:
        assert item.get("confidenceLevel")
        assert item.get("lineage") is not None


def test_recommendation_never_invented_without_lineage():
    svc = CommercialCopilotService()
    layers = svc._load_knowledge_layers("2026-06-01", "2026-06-07", None)
    if not layers.get("hasSnapshots"):
        pytest.skip("snapshots homologados ausentes")
    recs = svc._recommendation_engine(layers)
    for rec in recs["recommendations"]:
        assert rec.get("lineage")
        assert rec.get("confidenceLevel")
        assert rec.get("evidenceSource") is not None


@pytest.mark.asyncio
async def test_ask_homologated_question():
    svc = CommercialCopilotService()
    resp = await svc.ask("Qual produto gera mais receita?", "2026-06-01", "2026-06-07")
    if not resp.success:
        pytest.skip(resp.error)
    answer = resp.data["answer"]
    assert answer.get("confidenceLevel")
    assert answer.get("lineage")
    assert answer.get("evidenceSource") is not None


@pytest.mark.asyncio
async def test_build_full_payload():
    svc = CommercialCopilotService()
    resp = await svc.build("2026-06-01", "2026-06-07")
    if not resp.success:
        pytest.skip(resp.error)
    data = resp.data
    assert data["sprint"] == "F07.9"
    assert data["fonte"]["webPostoLive"] is False
    qa = data["qa"]
    assert qa["semCrossTenant"] is True
    assert qa["zeroRespostaSemLineage"] is True
    ex = data["executiveAnswers"]
    assert ex["5_perguntasHomologadas"] == 10
    assert data["parecerFinal"].startswith("[PARECER FINAL:")
