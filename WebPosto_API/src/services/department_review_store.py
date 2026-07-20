"""Decisões manuais de departamento com trilha mínima de auditoria."""

from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Lock

from pydantic import BaseModel, ConfigDict, Field


ALLOWED_DEPARTMENTS = {"combustiveis", "conveniencia", "lubrificantes"}
DEFAULT_PATH = Path("snapshots/department_reviews/store.json")


class DepartmentReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    fact_id: str
    department: str
    reviewer: str = Field(min_length=2)
    rationale: str = Field(min_length=3)
    category: str | None = None
    subcategory: str | None = None
    recipient_name: str | None = None
    reviewed_at: str


class DepartmentMappingRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    management_account_code: str
    department: str
    reviewer: str = Field(min_length=2)
    rationale: str = Field(min_length=3)
    category: str | None = None
    subcategory: str | None = None
    created_at: str
    active: bool = True


class SharedAllocationRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    management_account_code: str
    percentages: dict[str, int]
    reviewer: str = Field(min_length=2)
    rationale: str = Field(min_length=3)
    created_at: str
    active: bool = True


class DepartmentReviewStore:
    def __init__(self, path: str | Path = DEFAULT_PATH) -> None:
        self._path = Path(path)
        self._rules_path = self._path.with_name("rules.json")
        self._allocations_path = self._path.with_name("allocations.json")
        self._lock = Lock()

    def _load(self) -> dict[str, DepartmentReview]:
        if not self._path.exists():
            return {}
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return {key: DepartmentReview.model_validate(value) for key, value in raw.items()}

    def get(self, fact_id: str) -> DepartmentReview | None:
        return self._load().get(fact_id)

    def list_all(self) -> list[DepartmentReview]:
        return sorted(self._load().values(), key=lambda item: item.reviewed_at, reverse=True)

    def assign(self, fact_id: str, department: str, reviewer: str, rationale: str,
               category: str | None = None, subcategory: str | None = None,
               recipient_name: str | None = None) -> DepartmentReview:
        if department not in ALLOWED_DEPARTMENTS:
            raise ValueError("departamento invalido")
        record = DepartmentReview(
            fact_id=fact_id,
            department=department,
            reviewer=reviewer,
            rationale=rationale,
            category=category,
            subcategory=subcategory,
            recipient_name=recipient_name.strip() if recipient_name else None,
            reviewed_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            data = self._load()
            data[fact_id] = record
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(
                {key: value.model_dump(mode="json") for key, value in data.items()},
                ensure_ascii=False, indent=2,
            ), encoding="utf-8")
        return record

    def delete(self, fact_id: str) -> bool:
        with self._lock:
            data = self._load()
            removed = data.pop(fact_id, None) is not None
            if removed:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                self._path.write_text(json.dumps(
                    {key: value.model_dump(mode="json") for key, value in data.items()},
                    ensure_ascii=False, indent=2,
                ), encoding="utf-8")
            return removed

    def _load_rules(self) -> dict[str, DepartmentMappingRule]:
        if not self._rules_path.exists():
            return {}
        try:
            raw = json.loads(self._rules_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return {key: DepartmentMappingRule.model_validate(value) for key, value in raw.items()}

    def get_rule(self, management_account_code: str | None) -> DepartmentMappingRule | None:
        if not management_account_code:
            return None
        rule = self._load_rules().get(str(management_account_code))
        return rule if rule and rule.active else None

    def list_rules(self) -> list[DepartmentMappingRule]:
        return sorted(self._load_rules().values(), key=lambda item: item.created_at, reverse=True)

    def assign_rule(self, management_account_code: str, department: str,
                    reviewer: str, rationale: str, category: str | None = None,
                    subcategory: str | None = None) -> DepartmentMappingRule:
        if department not in ALLOWED_DEPARTMENTS:
            raise ValueError("departamento invalido")
        if not str(management_account_code).strip():
            raise ValueError("plano de contas obrigatorio")
        record = DepartmentMappingRule(
            management_account_code=str(management_account_code),
            department=department,
            reviewer=reviewer,
            rationale=rationale,
            category=category,
            subcategory=subcategory,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            rules = self._load_rules()
            rules[record.management_account_code] = record
            self._rules_path.parent.mkdir(parents=True, exist_ok=True)
            self._rules_path.write_text(json.dumps(
                {key: value.model_dump(mode="json") for key, value in rules.items()},
                ensure_ascii=False, indent=2,
            ), encoding="utf-8")
        return record

    def delete_rule(self, management_account_code: str) -> bool:
        with self._lock:
            rules = self._load_rules()
            removed = rules.pop(str(management_account_code), None) is not None
            if removed:
                self._rules_path.parent.mkdir(parents=True, exist_ok=True)
                self._rules_path.write_text(json.dumps(
                    {key: value.model_dump(mode="json") for key, value in rules.items()},
                    ensure_ascii=False, indent=2,
                ), encoding="utf-8")
            return removed

    def _load_allocations(self) -> dict[str, SharedAllocationRule]:
        if not self._allocations_path.exists():
            return {}
        try:
            raw = json.loads(self._allocations_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return {key: SharedAllocationRule.model_validate(value) for key, value in raw.items()}

    def get_allocation(self, management_account_code: str | None) -> SharedAllocationRule | None:
        if not management_account_code:
            return None
        rule = self._load_allocations().get(str(management_account_code))
        return rule if rule and rule.active else None

    def list_allocations(self) -> list[SharedAllocationRule]:
        return sorted(self._load_allocations().values(), key=lambda item: item.created_at, reverse=True)

    def assign_allocation(self, management_account_code: str, percentages: dict[str, int],
                          reviewer: str, rationale: str) -> SharedAllocationRule:
        cleaned = {key: int(value) for key, value in percentages.items() if int(value) > 0}
        if not cleaned or set(cleaned) - ALLOWED_DEPARTMENTS or sum(cleaned.values()) != 100:
            raise ValueError("rateio deve usar departamentos oficiais e somar 100")
        record = SharedAllocationRule(
            management_account_code=str(management_account_code),
            percentages=cleaned,
            reviewer=reviewer,
            rationale=rationale,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            rules = self._load_allocations()
            rules[record.management_account_code] = record
            self._allocations_path.parent.mkdir(parents=True, exist_ok=True)
            self._allocations_path.write_text(json.dumps(
                {key: value.model_dump(mode="json") for key, value in rules.items()},
                ensure_ascii=False, indent=2,
            ), encoding="utf-8")
        return record
