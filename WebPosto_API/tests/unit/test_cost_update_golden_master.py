"""Golden master das classificacoes de proposta de custo."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from src.operational.product_registration.dfe_cost_resolver import CostEvidence, STATUS_RESOLVED
from src.operational.cost_update.proposal_policy import CostUpdateProposalPolicy
from src.operational.cost_update.schemas import CurrentProductState

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "cost_update" / "golden" / "cases.json"


def test_golden_status_is_stable():
    policy = CostUpdateProposalPolicy()
    for case in json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]:
        current = CurrentProductState(
            ok=True,
            empresa_codigo=118508,
            produto_codigo=1,
            ean_confirmado=True,
            ativo=True,
            custo_atual=Decimal(case["current_cost"]),
            preco_venda=Decimal(case["sale"]),
            classification="OK",
        )
        evidence = CostEvidence(
            status=STATUS_RESOLVED,
            ean=case["ean"],
            match_type="EXACT_EAN",
            preco_custo=Decimal(case["proposed"]),
            unidade_atomica=True,
            quantidade_origem="uCom",
        )
        decision = policy.classify(current=current, evidence=evidence, expected_ean=case["ean"])
        assert decision["status"] == case["expected_status"]
