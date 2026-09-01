"""Engine de De-Para e categorização de despesas WebPosto — Sprint 47."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.enums.expense_classification import ExpenseClassification


class MatchConfidence(str, Enum):
    """Nível de confiança do matching."""

    EXACT = "EXACT"
    PATTERN = "PATTERN"
    FUZZY = "FUZZY"
    MANUAL = "MANUAL"


class ExpenseMappingRule(BaseModel):
    """Regra de mapeamento de despesa WebPosto para classificação DRE."""

    model_config = ConfigDict(frozen=True)

    rule_id: str
    webposto_pattern: str = Field(min_length=1)
    target_classification: ExpenseClassification
    confidence_level: MatchConfidence = MatchConfidence.PATTERN
    department: str | None = None
    is_active: bool = True
    priority: int = 0
    created_by: str = "system"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str | None = None

    @field_validator("webposto_pattern", mode="before")
    @classmethod
    def normalize_pattern(cls, value: str) -> str:
        return value.strip().upper()

    def matches(self, description: str) -> bool:
        normalized_desc = _normalize_text(description)
        raw_pattern = self.webposto_pattern.upper().strip()

        if self.confidence_level == MatchConfidence.EXACT:
            normalized_pattern = _normalize_text(raw_pattern)
            return normalized_desc == normalized_pattern

        if "%" in raw_pattern:
            pattern_parts = raw_pattern.split("%")
            normalized_parts = [_normalize_text(p) for p in pattern_parts if p]
            regex_pattern = ".*".join(re.escape(p) for p in normalized_parts)
            try:
                return bool(re.search(regex_pattern, normalized_desc))
            except re.error:
                return False

        normalized_pattern = _normalize_text(raw_pattern)
        return normalized_pattern in normalized_desc


class CategorizationResult(BaseModel):
    """Resultado da categorização de uma despesa."""

    model_config = ConfigDict(frozen=True)

    expense_id: str
    original_description: str
    normalized_description: str
    classification: ExpenseClassification
    department: str | None = None
    matched_rule_id: str | None = None
    confidence: MatchConfidence
    is_pending: bool = False
    categorized_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CategorizationSummary(BaseModel):
    """Resumo de categorização de um lote de despesas."""

    model_config = ConfigDict(frozen=True)

    total_expenses: int = 0
    categorized: int = 0
    pending: int = 0
    by_classification: dict[str, int] = Field(default_factory=dict)
    by_confidence: dict[str, int] = Field(default_factory=dict)
    results: list[CategorizationResult] = Field(default_factory=list)
    processed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.upper().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


DEFAULT_RULES_PATH = Path("snapshots/expense_mappings/rules.json")


class ExpenseCategorizationService:
    """Engine de categorização automática de despesas WebPosto."""

    def __init__(self, rules_path: str | Path = DEFAULT_RULES_PATH) -> None:
        self._rules_path = Path(rules_path)
        self._lock = Lock()
        self._rules_cache: dict[str, ExpenseMappingRule] = {}
        self._load_rules()

    def _load_rules(self) -> None:
        if not self._rules_path.exists():
            self._init_default_rules()
            return
        try:
            raw = json.loads(self._rules_path.read_text(encoding="utf-8"))
            self._rules_cache = {
                k: ExpenseMappingRule.model_validate(v) for k, v in raw.items()
            }
        except (OSError, json.JSONDecodeError):
            self._init_default_rules()

    def _init_default_rules(self) -> None:
        default_rules = [
            ("LIMP%", ExpenseClassification.OPERACIONAL, "Limpeza"),
            ("COMB%GERADOR", ExpenseClassification.OPERACIONAL, "Combustível gerador"),
            ("ENERGIA%", ExpenseClassification.ENERGIA, "Energia elétrica"),
            ("LUZ%", ExpenseClassification.ENERGIA, "Energia elétrica"),
            ("AGUA%", ExpenseClassification.ENERGIA, "Água"),
            ("ALUGUEL%", ExpenseClassification.ALUGUEL, "Aluguel"),
            ("LOCACAO%", ExpenseClassification.ALUGUEL, "Locação"),
            ("SALARIO%", ExpenseClassification.PESSOAL, "Salários"),
            ("FOLHA%", ExpenseClassification.PESSOAL, "Folha de pagamento"),
            ("VALE%", ExpenseClassification.PESSOAL, "Vales"),
            ("FGTS%", ExpenseClassification.PESSOAL, "FGTS"),
            ("INSS%", ExpenseClassification.TRIBUTARIA, "INSS"),
            ("ICMS%", ExpenseClassification.TRIBUTARIA, "ICMS"),
            ("PIS%", ExpenseClassification.TRIBUTARIA, "PIS/COFINS"),
            ("COFINS%", ExpenseClassification.TRIBUTARIA, "PIS/COFINS"),
            ("IMPOSTO%", ExpenseClassification.TRIBUTARIA, "Impostos"),
            ("MANUTENCAO%", ExpenseClassification.MANUTENCAO, "Manutenção"),
            ("REPARO%", ExpenseClassification.MANUTENCAO, "Reparos"),
            ("CONSERTO%", ExpenseClassification.MANUTENCAO, "Consertos"),
            ("MARKETING%", ExpenseClassification.MARKETING, "Marketing"),
            ("PUBLICIDADE%", ExpenseClassification.MARKETING, "Publicidade"),
            ("PROPAGANDA%", ExpenseClassification.MARKETING, "Propaganda"),
            ("CARTORIO%", ExpenseClassification.ADMINISTRATIVA, "Cartório"),
            ("TAXA%", ExpenseClassification.ADMINISTRATIVA, "Taxas"),
            ("CONTADOR%", ExpenseClassification.ADMINISTRATIVA, "Contabilidade"),
            ("SEGURO%", ExpenseClassification.ADMINISTRATIVA, "Seguros"),
            ("ADVOGADO%", ExpenseClassification.ADMINISTRATIVA, "Advocacia"),
            ("JURIDICO%", ExpenseClassification.ADMINISTRATIVA, "Jurídico"),
            ("JUROS%", ExpenseClassification.FINANCEIRA, "Juros"),
            ("TARIFA%BANC%", ExpenseClassification.FINANCEIRA, "Tarifas bancárias"),
            ("IOF%", ExpenseClassification.FINANCEIRA, "IOF"),
            ("MULTA%", ExpenseClassification.FINANCEIRA, "Multas"),
        ]

        for i, (pattern, classification, _desc) in enumerate(default_rules):
            rule_id = f"default-{i+1:03d}"
            self._rules_cache[rule_id] = ExpenseMappingRule(
                rule_id=rule_id,
                webposto_pattern=pattern,
                target_classification=classification,
                confidence_level=MatchConfidence.PATTERN,
                priority=100 - i,
            )

        self._save_rules()

    def _save_rules(self) -> None:
        with self._lock:
            self._rules_path.parent.mkdir(parents=True, exist_ok=True)
            data = {k: v.model_dump(mode="json") for k, v in self._rules_cache.items()}
            self._rules_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_rules(self, active_only: bool = True) -> list[ExpenseMappingRule]:
        rules = list(self._rules_cache.values())
        if active_only:
            rules = [r for r in rules if r.is_active]
        return sorted(rules, key=lambda r: -r.priority)

    def get_rule(self, rule_id: str) -> ExpenseMappingRule | None:
        return self._rules_cache.get(rule_id)

    def add_rule(
        self,
        webposto_pattern: str,
        target_classification: ExpenseClassification,
        confidence_level: MatchConfidence = MatchConfidence.PATTERN,
        department: str | None = None,
        created_by: str = "user",
        priority: int = 50,
    ) -> ExpenseMappingRule:
        rule_id = f"user-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        rule = ExpenseMappingRule(
            rule_id=rule_id,
            webposto_pattern=webposto_pattern,
            target_classification=target_classification,
            confidence_level=confidence_level,
            department=department,
            created_by=created_by,
            priority=priority,
        )
        self._rules_cache[rule_id] = rule
        self._save_rules()
        return rule

    def update_rule(
        self,
        rule_id: str,
        is_active: bool | None = None,
        priority: int | None = None,
        target_classification: ExpenseClassification | None = None,
    ) -> ExpenseMappingRule | None:
        existing = self._rules_cache.get(rule_id)
        if not existing:
            return None

        updates = {}
        if is_active is not None:
            updates["is_active"] = is_active
        if priority is not None:
            updates["priority"] = priority
        if target_classification is not None:
            updates["target_classification"] = target_classification
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        updated = ExpenseMappingRule(**{**existing.model_dump(), **updates})
        self._rules_cache[rule_id] = updated
        self._save_rules()
        return updated

    def delete_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules_cache:
            del self._rules_cache[rule_id]
            self._save_rules()
            return True
        return False

    def categorize(self, expense_id: str, description: str) -> CategorizationResult:
        normalized = _normalize_text(description)
        sorted_rules = sorted(
            [r for r in self._rules_cache.values() if r.is_active],
            key=lambda r: -r.priority,
        )

        for rule in sorted_rules:
            if rule.matches(description):
                return CategorizationResult(
                    expense_id=expense_id,
                    original_description=description,
                    normalized_description=normalized,
                    classification=rule.target_classification,
                    department=rule.department or rule.target_classification.department,
                    matched_rule_id=rule.rule_id,
                    confidence=rule.confidence_level,
                    is_pending=False,
                )

        return CategorizationResult(
            expense_id=expense_id,
            original_description=description,
            normalized_description=normalized,
            classification=ExpenseClassification.PENDENTE,
            department=None,
            matched_rule_id=None,
            confidence=MatchConfidence.FUZZY,
            is_pending=True,
        )

    def categorize_batch(self, expenses: list[dict[str, Any]]) -> CategorizationSummary:
        results: list[CategorizationResult] = []
        by_classification: dict[str, int] = {}
        by_confidence: dict[str, int] = {}

        for expense in expenses:
            expense_id = str(expense.get("id") or expense.get("despesaId") or expense.get("codigo") or "")
            description = str(expense.get("descricao") or expense.get("historico") or expense.get("nome") or "")

            result = self.categorize(expense_id, description)
            results.append(result)

            cls_name = result.classification.value
            by_classification[cls_name] = by_classification.get(cls_name, 0) + 1
            conf_name = result.confidence.value
            by_confidence[conf_name] = by_confidence.get(conf_name, 0) + 1

        categorized = sum(1 for r in results if not r.is_pending)
        pending = sum(1 for r in results if r.is_pending)

        return CategorizationSummary(
            total_expenses=len(results),
            categorized=categorized,
            pending=pending,
            by_classification=by_classification,
            by_confidence=by_confidence,
            results=results,
        )

    def learn_from_reclassification(
        self,
        original_description: str,
        new_classification: ExpenseClassification,
        created_by: str = "user",
    ) -> ExpenseMappingRule:
        normalized = _normalize_text(original_description)
        words = normalized.split()
        if len(words) >= 2:
            pattern = f"{words[0]}%{words[-1]}"
        elif words:
            pattern = f"{words[0]}%"
        else:
            pattern = normalized

        return self.add_rule(
            webposto_pattern=pattern,
            target_classification=new_classification,
            confidence_level=MatchConfidence.MANUAL,
            created_by=created_by,
            priority=75,
        )

    def reclassify_pending(self, expenses: list[dict[str, Any]]) -> CategorizationSummary:
        return self.categorize_batch(expenses)
