"""Ciclos de auditoria abertos a partir dos fatos WebPosto, sem baixa financeira."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.services.prestacao_contas_intelligence_service import PrestacaoContasIntelligenceService
from src.services.json_file_lock import InterProcessFileLock


DEFAULT_PATH = Path(".runtime/periodic_audits/runs.json")


class AuditChecklistItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    titulo: str
    descricao: str
    severidade: str
    impacto: float = 0
    status: str = "PENDENTE"
    fonte: str
    evidencia: str | None = None
    responsavel: str | None = None
    resolvido_em: datetime | None = None


class AuditRunEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    action: str
    actor: str
    at: datetime
    item_id: str | None = None
    evidence: str | None = None


class AuditDocumentReconciliation(BaseModel):
    model_config = ConfigDict(frozen=True)
    evidence_id: str
    sha256: str
    status: str
    comparisons: list[dict[str, Any]] = Field(default_factory=list)
    reconciled_by: str
    reconciled_at: datetime
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_justification: str | None = None


class PeriodicAuditRun(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    cycle_id: str
    empresa_codigo: str
    centro_custo: str
    data_inicial: str
    data_final: str
    status: str = "AGUARDANDO_CONFERENCIA"
    criado_em: datetime
    aprovado_por: str | None = None
    aprovado_em: datetime | None = None
    itens: list[AuditChecklistItem] = Field(default_factory=list)
    eventos: list[AuditRunEvent] = Field(default_factory=list)
    reconciliacoes: list[AuditDocumentReconciliation] = Field(default_factory=list)


class PeriodicAuditRunService:
    def __init__(self, path: str | Path = DEFAULT_PATH, intelligence: PrestacaoContasIntelligenceService | None = None) -> None:
        self._path = Path(path)
        self._intelligence = intelligence or PrestacaoContasIntelligenceService()

    def _load(self) -> dict[str, PeriodicAuditRun]:
        if not self._path.exists(): return {}
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            return {key: PeriodicAuditRun.model_validate(value) for key, value in raw.items()}
        except (OSError, json.JSONDecodeError, ValueError): return {}

    def _save(self, records: dict[str, PeriodicAuditRun]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps({key: item.model_dump(mode="json") for key, item in records.items()}, ensure_ascii=False, indent=2)
        temp: Path | None = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self._path.parent, delete=False) as handle:
                handle.write(content); handle.flush(); os.fsync(handle.fileno()); temp = Path(handle.name)
            os.replace(temp, self._path)
        finally:
            if temp and temp.exists(): temp.unlink(missing_ok=True)

    @staticmethod
    def _item(title: str, description: str, source: str, severity: str = "ALTA", impact: float = 0) -> AuditChecklistItem:
        return AuditChecklistItem(id=str(uuid4()), titulo=title, descricao=description, fonte=source, severidade=severity, impacto=round(float(impact or 0), 2))

    async def open_run(self, cycle_id: str, empresa_codigo: str, centro_custo: str, data_inicial: str, data_final: str) -> PeriodicAuditRun:
        try:
            start, end = date.fromisoformat(data_inicial), date.fromisoformat(data_final)
        except ValueError as exc:
            raise ValueError("INVALID_PERIOD") from exc
        if end < start:
            raise ValueError("INVALID_PERIOD")
        existing = next(
            (
                run for run in self._load().values()
                if run.cycle_id == cycle_id and run.data_inicial == data_inicial and run.data_final == data_final
            ),
            None,
        )
        if existing:
            return existing
        response = await self._intelligence.build(data_inicial, data_final, empresa_codigo, centro_custo)
        if not response.success or not response.data: raise ValueError(response.error or "Falha ao coletar fatos WebPosto")
        facts: dict[str, Any] = response.data
        coverage = ((facts.get("scope") or {}).get("centerCoverage") or {})
        items: list[AuditChecklistItem] = []
        for label, key in (("despesas", "Despesas"), ("caixas", "Caixas"), ("banco", "Movimento bancário")):
            evidence = coverage.get(label) or {}
            if evidence.get("status") != "COMPROVADA":
                items.append(self._item(f"{key}: centro de custo pendente", f"{evidence.get('withoutCenter', 0)} registro(s) sem centro comprovado; não foram distribuídos.", "WEBPOSTO", "CRITICA"))
        accountability = facts.get("employeeAccountability") or {}
        if accountability.get("status") == "BLOQUEADO_EVIDENCIA_CENTRO":
            items.append(self._item("Responsabilização de funcionário bloqueada", accountability.get("motivo") or "Evidência insuficiente.", "LEDGER", "ALTA"))
        sangria = facts.get("sangriaIntelligence") or {}
        answers = sangria.get("answers") or {}
        flow = sangria.get("fluxo") or {}
        if answers.get("quebraRastreabilidade"):
            items.append(self._item("Sangria sem depósito correspondente", "Conferir destino físico e extrato bancário antes de aprovar.", "CAIXA × MOVIMENTO_CONTA", "CRITICA", (flow.get("SANGRIA") or {}).get("valor", 0)))
        vale = facts.get("valeForensics") or {}
        if float(vale.get("valorTotal") or 0) > 0:
            items.append(self._item("Vales/adiantamentos a conferir", f"Existem {vale.get('total', 0)} lançamento(s) de vale ou adiantamento.", "DESPESAS", "ALTA", vale.get("valorTotal", 0)))
        if not items:
            items.append(self._item("Conferência documental", "Fatos automáticos sem divergência crítica; confirme documentos e destinação do dinheiro.", "CHECKLIST_DIRETOR", "NORMAL"))
        now = datetime.now(timezone.utc)
        run = PeriodicAuditRun(
            id=str(uuid4()), cycle_id=cycle_id, empresa_codigo=str(empresa_codigo),
            centro_custo=centro_custo, data_inicial=data_inicial, data_final=data_final,
            criado_em=now, itens=items,
            eventos=[AuditRunEvent(action="OPENED", actor="SYSTEM", at=now)],
        )
        with InterProcessFileLock(self._path):
            records = self._load()
            existing = next(
                (
                    current for current in records.values()
                    if current.cycle_id == cycle_id
                    and current.data_inicial == data_inicial
                    and current.data_final == data_final
                ),
                None,
            )
            if existing:
                return existing
            records[run.id] = run
            self._save(records)
            return run

    def get(self, run_id: str) -> PeriodicAuditRun | None: return self._load().get(run_id)

    def list_all(self) -> list[PeriodicAuditRun]:
        return sorted(self._load().values(), key=lambda item: item.criado_em, reverse=True)

    def resolve(self, run_id: str, item_id: str, responsavel: str, evidencia: str) -> PeriodicAuditRun | None:
        with InterProcessFileLock(self._path):
            records = self._load(); run = records.get(run_id)
            if not run: return None
            items = [item.model_copy(update={"status": "RESOLVIDO", "responsavel": responsavel, "evidencia": evidencia, "resolvido_em": datetime.now(timezone.utc)}) if item.id == item_id else item for item in run.itens]
            if not any(item.id == item_id for item in run.itens): return None
            event = AuditRunEvent(action="ITEM_RESOLVED", actor=responsavel, at=datetime.now(timezone.utc), item_id=item_id, evidence=evidencia)
            updated = run.model_copy(update={"itens": items, "eventos": [*run.eventos, event], "status": "PRONTO_PARA_APROVACAO" if all(item.status == "RESOLVIDO" for item in items) else "AGUARDANDO_CONFERENCIA"})
            records[run_id] = updated; self._save(records); return updated

    def record_reconciliation(
        self,
        run_id: str,
        evidence_id: str,
        sha256: str,
        result: dict[str, Any],
        actor: str,
    ) -> PeriodicAuditRun | None:
        with InterProcessFileLock(self._path):
            records = self._load(); run = records.get(run_id)
            if not run: return None
            now = datetime.now(timezone.utc)
            record = AuditDocumentReconciliation(
                evidence_id=evidence_id,
                sha256=sha256,
                status=str(result.get("status") or "UNKNOWN"),
                comparisons=list(result.get("comparisons") or []),
                reconciled_by=actor,
                reconciled_at=now,
            )
            reconciliations = [
                item for item in run.reconciliacoes if item.evidence_id != evidence_id
            ]
            reconciliations.append(record)
            event = AuditRunEvent(
                action="PDF_RECONCILED",
                actor=actor,
                at=now,
                evidence=f"sha256:{sha256};status:{record.status}",
            )
            updated = run.model_copy(update={
                "reconciliacoes": reconciliations,
                "eventos": [*run.eventos, event],
            })
            records[run_id] = updated; self._save(records); return updated

    def review_reconciliation(
        self,
        run_id: str,
        evidence_id: str,
        actor: str,
        justification: str,
    ) -> PeriodicAuditRun | None:
        if len(justification.strip()) < 3:
            raise ValueError("REVIEW_JUSTIFICATION_REQUIRED")
        with InterProcessFileLock(self._path):
            records = self._load(); run = records.get(run_id)
            if not run: return None
            if not any(item.evidence_id == evidence_id for item in run.reconciliacoes):
                return None
            now = datetime.now(timezone.utc)
            reconciliations = [
                item.model_copy(update={
                    "reviewed_by": actor,
                    "reviewed_at": now,
                    "review_justification": justification.strip(),
                }) if item.evidence_id == evidence_id else item
                for item in run.reconciliacoes
            ]
            event = AuditRunEvent(
                action="PDF_RECONCILIATION_REVIEWED",
                actor=actor,
                at=now,
                evidence=f"{evidence_id}:{justification.strip()}",
            )
            updated = run.model_copy(update={
                "reconciliacoes": reconciliations,
                "eventos": [*run.eventos, event],
            })
            records[run_id] = updated; self._save(records); return updated

    def approve(self, run_id: str, diretor: str) -> PeriodicAuditRun | None:
        with InterProcessFileLock(self._path):
            records = self._load(); run = records.get(run_id)
            if not run: return None
            if any(item.status != "RESOLVIDO" for item in run.itens): raise ValueError("Existem itens pendentes no checklist")
            if any(item.reviewed_at is None for item in run.reconciliacoes):
                raise ValueError("Existem conciliações de PDF sem revisão humana")
            now = datetime.now(timezone.utc)
            event = AuditRunEvent(action="APPROVED", actor=diretor, at=now)
            updated = run.model_copy(update={"status": "APROVADO", "aprovado_por": diretor, "aprovado_em": now, "eventos": [*run.eventos, event]})
            records[run_id] = updated; self._save(records); return updated
