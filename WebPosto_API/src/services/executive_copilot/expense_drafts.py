"""CREATE_EXPENSE_DRAFT persistente no Action Hub local. WEBPOSTO_WRITES=0."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from src.services.ai_ops.models import connect_action_hub_db
from src.services.executive_copilot.access import restrict_requested_units
from src.services.executive_copilot.action_proposals import ACTION_EXECUTION_NOT_ENABLED
from src.services.executive_copilot.contracts import WEBPOSTO_WRITES
from src.services.executive_copilot.unit_capabilities import (
    ACTION_NETWORK_SCOPE_FORBIDDEN,
    UNIT_REQUIRED_FOR_ACTION,
    public_name,
    user_role,
)
from src.services.sds_sanitize import sanitize_text, sanitize_value

Clock = Callable[[], datetime]

CONTRACT_VERSION = "expense-draft-v1"
ACTION_TYPE = "CREATE_EXPENSE_DRAFT"
IDEMPOTENCY_WINDOW_HOURS = 24

STATUS_DRAFT = "DRAFT"
STATUS_CONFIRMED = "CONFIRMED"
STATUS_PENDING_APPROVAL = "PENDING_APPROVAL"
STATUS_APPROVED_LOCAL = "APPROVED_LOCAL"
STATUS_REJECTED = "REJECTED"
STATUS_CANCELLED = "CANCELLED"
STATUS_EXECUTION_BLOCKED = "EXECUTION_BLOCKED"

ACTIVE_STATUSES = frozenset(
    {STATUS_DRAFT, STATUS_CONFIRMED, STATUS_PENDING_APPROVAL, STATUS_APPROVED_LOCAL}
)
APPROVER_ROLES = frozenset({"director", "admin", "owner"})
NETWORK_ROLES = frozenset({"director", "admin", "owner"})

EVENT_CREATED = "DRAFT_CREATED"
EVENT_UPDATED = "DRAFT_UPDATED"
EVENT_CONFIRMED = "DRAFT_CONFIRMED"
EVENT_APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
EVENT_APPROVED = "DRAFT_APPROVED_LOCAL"
EVENT_REJECTED = "DRAFT_REJECTED"
EVENT_CANCELLED = "DRAFT_CANCELLED"
EVENT_EXECUTION_BLOCKED = "EXECUTION_BLOCKED"

FORBIDDEN_PUBLIC_KEYS = frozenset(
    {
        "empresaCodigo",
        "empresa_codigo",
        "token",
        "header",
        "url",
        "credencial",
        "sqlite",
        "ownerToken",
        "stack",
    }
)

_INVENTED = (
    "comprovante",
    "operador",
    "fornecedor",
    "contaContabil",
    "centroCusto",
    "documentoFiscal",
    "dataCompetencia",
    "formaPagamento",
    "observacoes",
    "aprovacao",
    "categoriaHomologada",
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def _actor(user: dict[str, Any] | None) -> str:
    if not isinstance(user, dict):
        return ""
    return str(user.get("sub") or user.get("email") or "").strip()


def _fold(value: str) -> str:
    norm = unicodedata.normalize("NFD", str(value or ""))
    ascii_only = "".join(ch for ch in norm if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", ascii_only.casefold()).strip()


def _money(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None
    if amount <= 0:
        return None
    return float(amount)


def classify_expense_description(descricao: str) -> dict[str, Any] | None:
    blob = _fold(descricao)
    if "gelo" in blob:
        return {
            "campo": "categoria",
            "status": "AUTO_CLASSIFIED",
            "valor": "Gelo",
            "evidencia": "regra: palavra-chave gelo",
        }
    return None


def public_filled(filled: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in filled.items():
        if key in FORBIDDEN_PUBLIC_KEYS or key in {"empresaCodigo", "empresa_codigo"}:
            continue
        if key in _INVENTED:
            continue
        out[key] = value
    return out


def permitted_actions(status: str, role: str) -> list[str]:
    actions: list[str] = ["read"]
    if status == STATUS_DRAFT:
        actions.extend(["edit", "confirm", "cancel"])
    elif status in {STATUS_CONFIRMED, STATUS_PENDING_APPROVAL}:
        actions.extend(["cancel", "reject"])
        if role in APPROVER_ROLES:
            actions.append("approve")
    actions.append("execute_blocked")
    return actions


def _requester_key(user: dict[str, Any] | None) -> str:
    return _fold(_actor(user))


def idempotency_key(
    *,
    unit: int,
    user: dict[str, Any] | None,
    valor: float | None,
    descricao: str,
    moment: datetime,
) -> str:
    bucket = moment.astimezone(timezone.utc).strftime("%Y-%m-%d")
    payload = {
        "version": CONTRACT_VERSION,
        "action": ACTION_TYPE,
        "unit": int(unit),
        "user": _requester_key(user),
        "valor": None if valor is None else f"{valor:.2f}",
        "descricao": _fold(descricao),
        "period": bucket,
        "windowHours": IDEMPOTENCY_WINDOW_HOURS,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def plan_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ExpenseDraftService:
    def __init__(self, *, db_path: str | None = None, clock: Clock | None = None) -> None:
        self._db_path = db_path
        self._clock = clock or _now
        with connect_action_hub_db(self._db_path):
            pass

    def save(
        self,
        *,
        user: dict[str, Any] | None,
        unit: int | None,
        valor: float | None,
        descricao: str,
        all_units: bool = False,
    ) -> dict[str, Any]:
        if all_units:
            return self._blocked(
                ACTION_NETWORK_SCOPE_FORBIDDEN,
                "Ação DRAFT não opera em Todas as Unidades. Selecione uma unidade.",
            )
        if unit is None:
            return self._blocked(
                UNIT_REQUIRED_FOR_ACTION,
                "Informe a unidade da despesa. Ex.: Conveniência 24 Horas.",
            )
        auth = restrict_requested_units([unit], user)
        if auth.blocked:
            return self._blocked(auth.blocked["code"], auth.blocked["message"])
        unit = auth.units[0]
        now = self._clock()
        filled = {"valor": valor, "descricao": sanitize_text(descricao), "unitPublicName": public_name(unit)}
        filled = {key: value for key, value in filled.items() if value not in (None, "")}
        missing = [key for key in ("valor", "descricao") if filled.get(key) in (None, "")]
        auto = []
        suggested = classify_expense_description(str(filled.get("descricao") or ""))
        if suggested:
            auto.append(suggested)
        key = idempotency_key(unit=unit, user=user, valor=valor, descricao=str(filled.get("descricao") or ""), moment=now)
        digest = plan_hash(
            {
                "action": ACTION_TYPE,
                "unit": unit,
                "valor": filled.get("valor"),
                "descricao": filled.get("descricao"),
                "version": CONTRACT_VERSION,
            }
        )
        existing = self._by_key(key)
        if existing and existing["status"] in ACTIVE_STATUSES:
            payload = self._public(existing, duplicate=True)
            return payload
        draft_id = uuid.uuid4().hex
        actor = _actor(user)
        role = user_role(user)
        row = {
            "id": draft_id,
            "action_type": ACTION_TYPE,
            "status": STATUS_DRAFT,
            "empresa_codigo": unit,
            "requester": actor,
            "role": role,
            "valor": valor,
            "descricao": filled.get("descricao") or "",
            "filled_json": json.dumps(public_filled(filled), ensure_ascii=False),
            "missing_json": json.dumps(missing, ensure_ascii=False),
            "auto_classified_json": json.dumps(auto, ensure_ascii=False),
            "idempotency_key": key,
            "plan_hash": digest,
            "contract_version": CONTRACT_VERSION,
            "created_at": _iso(now),
            "updated_at": _iso(now),
        }
        with connect_action_hub_db(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO webposto_action_hub_copilot_drafts (
                    id, action_type, status, empresa_codigo, requester, role, valor, descricao,
                    filled_json, missing_json, auto_classified_json, idempotency_key, plan_hash,
                    contract_version, created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    row["id"],
                    row["action_type"],
                    row["status"],
                    row["empresa_codigo"],
                    row["requester"],
                    row["role"],
                    row["valor"],
                    row["descricao"],
                    row["filled_json"],
                    row["missing_json"],
                    row["auto_classified_json"],
                    row["idempotency_key"],
                    row["plan_hash"],
                    row["contract_version"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            conn.commit()
        self._event(draft_id, EVENT_CREATED, user, {"status": STATUS_DRAFT})
        return self._public(self._get_row(draft_id), duplicate=False)

    def get(self, draft_id: str, user: dict[str, Any] | None) -> dict[str, Any]:
        row = self._get_row(draft_id)
        if row is None:
            return self._blocked("DRAFT_NOT_FOUND", "Proposta não encontrada.")
        denied = self._reauthorize(row, user)
        if denied:
            return denied
        return self._public(row)

    def confirm(self, draft_id: str, user: dict[str, Any] | None) -> dict[str, Any]:
        return self._transition(
            draft_id,
            user,
            allowed_from={STATUS_DRAFT},
            next_status=STATUS_CONFIRMED,
            event=EVENT_CONFIRMED,
            extra_event=EVENT_APPROVAL_REQUESTED,
        )

    def approve(self, draft_id: str, user: dict[str, Any] | None) -> dict[str, Any]:
        row = self._get_row(draft_id)
        if row is None:
            return self._blocked("DRAFT_NOT_FOUND", "Proposta não encontrada.")
        denied = self._reauthorize(row, user)
        if denied:
            return denied
        role = user_role(user)
        if role not in APPROVER_ROLES:
            return self._blocked("APPROVAL_FORBIDDEN", "Papel sem permissão para aprovar localmente.")
        return self._transition(
            draft_id,
            user,
            allowed_from={STATUS_CONFIRMED, STATUS_PENDING_APPROVAL},
            next_status=STATUS_APPROVED_LOCAL,
            event=EVENT_APPROVED,
        )

    def reject(self, draft_id: str, user: dict[str, Any] | None) -> dict[str, Any]:
        row = self._get_row(draft_id)
        if row is None:
            return self._blocked("DRAFT_NOT_FOUND", "Proposta não encontrada.")
        denied = self._reauthorize(row, user)
        if denied:
            return denied
        role = user_role(user)
        if role not in APPROVER_ROLES:
            return self._blocked("APPROVAL_FORBIDDEN", "Papel sem permissão para rejeitar.")
        return self._transition(
            draft_id,
            user,
            allowed_from={STATUS_CONFIRMED, STATUS_PENDING_APPROVAL},
            next_status=STATUS_REJECTED,
            event=EVENT_REJECTED,
        )

    def cancel(self, draft_id: str, user: dict[str, Any] | None) -> dict[str, Any]:
        return self._transition(
            draft_id,
            user,
            allowed_from={STATUS_DRAFT, STATUS_CONFIRMED, STATUS_PENDING_APPROVAL},
            next_status=STATUS_CANCELLED,
            event=EVENT_CANCELLED,
        )

    def execute(self, draft_id: str, user: dict[str, Any] | None) -> dict[str, Any]:
        row = self._get_row(draft_id)
        if row is None:
            return self._blocked("DRAFT_NOT_FOUND", "Proposta não encontrada.")
        denied = self._reauthorize(row, user)
        if denied:
            return denied
        now = _iso(self._clock())
        with connect_action_hub_db(self._db_path) as conn:
            conn.execute(
                "UPDATE webposto_action_hub_copilot_drafts SET status=?, updated_at=? WHERE id=?",
                (STATUS_EXECUTION_BLOCKED, now, draft_id),
            )
            conn.commit()
        self._event(draft_id, EVENT_EXECUTION_BLOCKED, user, {"code": ACTION_EXECUTION_NOT_ENABLED})
        payload = self._public(self._get_row(draft_id))
        payload["status"] = STATUS_EXECUTION_BLOCKED
        payload["canExecute"] = False
        payload["executionCode"] = ACTION_EXECUTION_NOT_ENABLED
        payload["blocked"] = {
            "code": ACTION_EXECUTION_NOT_ENABLED,
            "message": "Execução no ERP WebPosto não está habilitada.",
        }
        payload["webpostoWrites"] = WEBPOSTO_WRITES
        return payload

    def _transition(
        self,
        draft_id: str,
        user: dict[str, Any] | None,
        *,
        allowed_from: set[str],
        next_status: str,
        event: str,
        extra_event: str | None = None,
    ) -> dict[str, Any]:
        row = self._get_row(draft_id)
        if row is None:
            return self._blocked("DRAFT_NOT_FOUND", "Proposta não encontrada.")
        denied = self._reauthorize(row, user)
        if denied:
            return denied
        if row["status"] not in allowed_from:
            return self._blocked("INVALID_TRANSITION", f"Transição inválida a partir de {row['status']}.")
        now = _iso(self._clock())
        with connect_action_hub_db(self._db_path) as conn:
            cursor = conn.execute(
                "UPDATE webposto_action_hub_copilot_drafts SET status=?, updated_at=? WHERE id=? AND status=?",
                (next_status, now, draft_id, row["status"]),
            )
            if cursor.rowcount != 1:
                return self._blocked("CONCURRENT_UPDATE", "Atualização concorrente: recarregue a proposta.")
            conn.commit()
        self._event(draft_id, event, user, {"from": row["status"], "to": next_status})
        if extra_event:
            self._event(draft_id, extra_event, user, {"status": next_status})
        return self._public(self._get_row(draft_id))

    def _reauthorize(self, row: dict[str, Any], user: dict[str, Any] | None) -> dict[str, Any] | None:
        auth = restrict_requested_units([int(row["empresa_codigo"])], user)
        if auth.blocked:
            return self._blocked(auth.blocked["code"], auth.blocked["message"])
        return None

    def _by_key(self, key: str) -> dict[str, Any] | None:
        with connect_action_hub_db(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM webposto_action_hub_copilot_drafts WHERE idempotency_key=?",
                (key,),
            ).fetchone()
        return dict(row) if row else None

    def _get_row(self, draft_id: str) -> dict[str, Any] | None:
        with connect_action_hub_db(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM webposto_action_hub_copilot_drafts WHERE id=?",
                (draft_id,),
            ).fetchone()
        return dict(row) if row else None

    def _event(self, draft_id: str, event: str, user: dict[str, Any] | None, detail: dict[str, Any]) -> None:
        with connect_action_hub_db(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO webposto_action_hub_copilot_events (
                    id, draft_id, event, actor, role, detail_json, created_at
                ) VALUES (?,?,?,?,?,?,?)
                """,
                (
                    uuid.uuid4().hex,
                    draft_id,
                    event,
                    sanitize_text(_actor(user)),
                    user_role(user),
                    json.dumps(sanitize_value(detail), ensure_ascii=False),
                    _iso(self._clock()),
                ),
            )
            conn.commit()

    def _audit_summary(self, draft_id: str) -> list[dict[str, Any]]:
        with connect_action_hub_db(self._db_path) as conn:
            rows = conn.execute(
                """
                SELECT event, actor, role, created_at
                FROM webposto_action_hub_copilot_events
                WHERE draft_id=? ORDER BY created_at
                """,
                (draft_id,),
            ).fetchall()
        return [
            {
                "event": row["event"],
                "actor": sanitize_text(row["actor"] or ""),
                "role": row["role"],
                "createdAt": row["created_at"],
            }
            for row in rows
        ]

    def _blocked(self, code: str, message: str) -> dict[str, Any]:
        return sanitize_value(
            {
                "ok": False,
                "blocked": {"code": code, "message": message},
                "canExecute": False,
                "executionCode": ACTION_EXECUTION_NOT_ENABLED,
                "webpostoWrites": WEBPOSTO_WRITES,
            }
        )

    def _public(self, row: dict[str, Any] | None, *, duplicate: bool = False) -> dict[str, Any]:
        if row is None:
            return self._blocked("DRAFT_NOT_FOUND", "Proposta não encontrada.")
        filled = json.loads(row["filled_json"] or "{}")
        missing = json.loads(row["missing_json"] or "[]")
        auto = json.loads(row["auto_classified_json"] or "[]")
        status = row["status"]
        unit = int(row["empresa_codigo"])
        payload = {
            "ok": True,
            "draftId": row["id"],
            "actionType": ACTION_TYPE,
            "status": status,
            "unitPublicName": public_name(unit),
            "filledFields": public_filled(filled),
            "missingFields": missing,
            "autoClassifiedFields": auto,
            "requiresConfirmation": status == STATUS_DRAFT,
            "requiresApproval": status in {STATUS_DRAFT, STATUS_CONFIRMED, STATUS_PENDING_APPROVAL},
            "canExecute": False,
            "executionCode": ACTION_EXECUTION_NOT_ENABLED,
            "webpostoWrites": WEBPOSTO_WRITES,
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "permittedActions": permitted_actions(status, row["role"]),
            "auditSummary": self._audit_summary(row["id"]),
            "duplicate": duplicate,
        }
        return sanitize_value(payload)
