"""Testes de categorização de despesas — Sprint 47."""

import tempfile
from pathlib import Path

from src.services.expense_categorization_service import (
    ExpenseCategorizationService,
    ExpenseMappingRule,
    MatchConfidence,
    CategorizationResult,
    _normalize_text,
)
from src.domain.enums.expense_classification import ExpenseClassification


def test_normalize_text_removes_accents():
    assert _normalize_text("Manutenção Elétrica") == "MANUTENCAO ELETRICA"
    assert _normalize_text("ÁGUA E LUZ") == "AGUA E LUZ"
    assert _normalize_text("café") == "CAFE"


def test_normalize_text_removes_special_chars():
    assert _normalize_text("Taxa R$ 100,00") == "TAXA R 100 00"
    assert _normalize_text("Serviço #123") == "SERVICO 123"


def test_categorize_exact_match():
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ExpenseCategorizationService(rules_path=Path(tmpdir) / "rules.json")

        service.add_rule(
            webposto_pattern="ENERGIA ELETRICA ESPECIAL",
            target_classification=ExpenseClassification.ENERGIA,
            confidence_level=MatchConfidence.EXACT,
            priority=200,
        )

        result = service.categorize("exp-001", "Energia Elétrica Especial")
        assert result.classification == ExpenseClassification.ENERGIA
        assert result.confidence == MatchConfidence.EXACT
        assert result.is_pending is False


def test_categorize_pattern_match():
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ExpenseCategorizationService(rules_path=Path(tmpdir) / "rules.json")

        service.add_rule(
            webposto_pattern="MANUTENCAO%",
            target_classification=ExpenseClassification.MANUTENCAO,
        )

        result = service.categorize("exp-002", "Manutenção Preventiva Gerador")
        assert result.classification == ExpenseClassification.MANUTENCAO
        assert result.is_pending is False


def test_categorize_pattern_with_wildcards():
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ExpenseCategorizationService(rules_path=Path(tmpdir) / "rules.json")

        service.add_rule(
            webposto_pattern="COMB%GERADOR",
            target_classification=ExpenseClassification.OPERACIONAL,
            priority=200,
        )

        result = service.categorize("exp-003", "Combustível do Gerador")
        assert result.classification == ExpenseClassification.OPERACIONAL


def test_categorize_pending_when_no_match():
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ExpenseCategorizationService(rules_path=Path(tmpdir) / "rules.json")

        result = service.categorize("exp-004", "Despesa Aleatória XYZ")
        assert result.classification == ExpenseClassification.PENDENTE
        assert result.is_pending is True
        assert result.matched_rule_id is None


def test_categorize_batch():
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ExpenseCategorizationService(rules_path=Path(tmpdir) / "rules.json")

        service.add_rule("ENERGIA%", ExpenseClassification.ENERGIA)
        service.add_rule("ALUGUEL%", ExpenseClassification.ALUGUEL)

        expenses = [
            {"id": "1", "descricao": "Energia Elétrica Filial"},
            {"id": "2", "descricao": "Aluguel Escritório"},
            {"id": "3", "descricao": "Despesa Desconhecida"},
        ]

        summary = service.categorize_batch(expenses)

        assert summary.total_expenses == 3
        assert summary.categorized == 2
        assert summary.pending == 1
        assert summary.by_classification["ENERGIA"] == 1
        assert summary.by_classification["ALUGUEL"] == 1


def test_learn_from_reclassification():
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ExpenseCategorizationService(rules_path=Path(tmpdir) / "rules.json")

        rule = service.learn_from_reclassification(
            original_description="Taxa Cartório Município",
            new_classification=ExpenseClassification.ADMINISTRATIVA,
            created_by="diretor@posto.com",
        )

        assert rule.target_classification == ExpenseClassification.ADMINISTRATIVA
        assert rule.confidence_level == MatchConfidence.MANUAL
        assert "TAXA" in rule.webposto_pattern

        result = service.categorize("exp-new", "Taxa Cartório Prefeitura")
        assert result.classification == ExpenseClassification.ADMINISTRATIVA


def test_rule_priority_order():
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ExpenseCategorizationService(rules_path=Path(tmpdir) / "rules.json")

        service.add_rule("TRANSPORTE%", ExpenseClassification.PESSOAL, priority=10)
        service.add_rule("VALE TRANSPORTE%", ExpenseClassification.OPERACIONAL, priority=200)

        result = service.categorize("exp-005", "Vale Transporte Funcionários")
        assert result.classification == ExpenseClassification.OPERACIONAL


def test_update_rule():
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ExpenseCategorizationService(rules_path=Path(tmpdir) / "rules.json")

        rule = service.add_rule("TEST%", ExpenseClassification.OPERACIONAL)
        original_id = rule.rule_id

        updated = service.update_rule(
            original_id,
            is_active=False,
            target_classification=ExpenseClassification.ADMINISTRATIVA,
        )

        assert updated is not None
        assert updated.is_active is False
        assert updated.target_classification == ExpenseClassification.ADMINISTRATIVA


def test_delete_rule():
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ExpenseCategorizationService(rules_path=Path(tmpdir) / "rules.json")

        rule = service.add_rule("DELETE%", ExpenseClassification.OPERACIONAL)
        rule_id = rule.rule_id

        assert service.delete_rule(rule_id) is True
        assert service.get_rule(rule_id) is None
        assert service.delete_rule(rule_id) is False


def test_default_rules_initialized():
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ExpenseCategorizationService(rules_path=Path(tmpdir) / "rules.json")

        rules = service.list_rules()
        assert len(rules) > 20

        result = service.categorize("exp-006", "Energia Elétrica Posto")
        assert result.classification == ExpenseClassification.ENERGIA

        result2 = service.categorize("exp-007", "Salário Funcionários")
        assert result2.classification == ExpenseClassification.PESSOAL
