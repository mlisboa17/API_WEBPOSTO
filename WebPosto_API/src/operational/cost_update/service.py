"""Fachada read-only do motor de proposta de custo por DF-e."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from src.operational.product_registration.dfe_cost_resolver import CostEvidence

from .audit_trail import CostUpdateAuditTrail
from .current_cost_reader import CurrentProductCostReader
from .decimal_utils import present_money, quantize_cost, ratio, to_decimal
from .evidence_resolver import CostEvidenceResolver
from .ports import UnimplementedCostUpdateGateway, UnimplementedCostUpdateVerifier
from .proposal_policy import CostUpdateProposalPolicy
from .proposal_store import CostProposalStore
from .schemas import CostUpdateCandidate, CostUpdateProposal, CurrentProductState, ScanSummary
from .versions import ENGINE_VERSION, POLICY_VERSION

COMPANY_CODE = 118508
DEFAULT_PENDING = Path("data/product_registration/pending_cost_update_118508.json")
DEFAULT_PRICE_REVIEW = Path("data/product_registration/pending_price_review_118508.json")
DEFAULT_CHECKPOINT = Path("data/product_registration/execution/checkpoint_118508.json")
DEFAULT_ACCOUNTANT = Path("data/product_registration/accountant_review_118508.json")


class CostUpdateService:
    """scan, propose, verify_current_state e status. Sem PUT."""

    def __init__(
        self,
        output_dir: Path,
        *,
        reader: CurrentProductCostReader | None = None,
        resolver: CostEvidenceResolver | None = None,
        policy: CostUpdateProposalPolicy | None = None,
        pending_path: Path = DEFAULT_PENDING,
        price_review_path: Path = DEFAULT_PRICE_REVIEW,
        checkpoint_path: Path = DEFAULT_CHECKPOINT,
        accountant_path: Path = DEFAULT_ACCOUNTANT,
        empresa: int = COMPANY_CODE,
    ) -> None:
        if empresa != COMPANY_CODE:
            raise ValueError("esta fase valida somente a empresa 118508")
        self.empresa = empresa
        self.output_dir = Path(output_dir)
        self.reader = reader
        self.resolver = resolver or CostEvidenceResolver(company_code=empresa)
        self.policy = policy or CostUpdateProposalPolicy()
        self.store = CostProposalStore(self.output_dir)
        self.audit = CostUpdateAuditTrail()
        self.pending_path = Path(pending_path)
        self.price_review_path = Path(price_review_path)
        self.checkpoint_path = Path(checkpoint_path)
        self.accountant_path = Path(accountant_path)
        self.gateway = UnimplementedCostUpdateGateway()
        self.verifier = UnimplementedCostUpdateVerifier()
        self.api_writes = 0

    def load_queue(self) -> list[CostUpdateCandidate]:
        pending = _load_json(self.pending_path)
        price_review = _load_json(self.price_review_path)
        checkpoint = _load_json(self.checkpoint_path)
        queue: dict[str, CostUpdateCandidate] = {}
        for ean, row in pending.items():
            if not isinstance(row, dict):
                continue
            queue[str(ean)] = _candidate_from_pending(row, self.empresa, "pending_cost_update")
        for ean, row in price_review.items():
            if str(ean) in queue or not isinstance(row, dict):
                continue
            queue[str(ean)] = _candidate_from_pending(row, self.empresa, "pending_price_review")
        self.audit.record(
            "queue_loaded",
            extra={
                "pending": len(pending),
                "price_review": len(price_review),
                "checkpoint": len([k for k in checkpoint if not str(k).startswith("_")]),
                "accountant": len(_load_json(self.accountant_path)),
                "queued": len(queue),
            },
        )
        return list(queue.values())

    def verify_current_state(self, key: str, produto_codigo: int, ean: str) -> CurrentProductState:
        if self.reader is None:
            raise RuntimeError("CurrentProductCostReader nao configurado")
        return self.reader.read(key, produto_codigo, ean)

    def _iter_evaluated(self, key: str, eans: set[str] | None = None):
        if self.reader is None:
            raise RuntimeError("CurrentProductCostReader nao configurado")
        self.resolver.build_index()
        for candidate in self.load_queue():
            if eans is not None and candidate.ean not in eans:
                continue
            current = self.verify_current_state(key, int(candidate.produto_codigo or 0), candidate.ean)
            evidence = self.resolver.resolve(candidate.ean)
            self.audit.record("scan_item", ean=candidate.ean, extra={"dfe": evidence.status})
            yield candidate, current, evidence

    def _summary_from_evaluated(self, evaluated: list) -> ScanSummary:
        items: list[dict[str, Any]] = []
        located = 0
        linked = 0
        with_dfe = 0
        still_zero = 0
        for candidate, current, evidence in evaluated:
            if current.produto_codigo:
                located += 1
            if current.ok and current.empresa_codigo == self.empresa:
                linked += 1
            if evidence.resolved:
                with_dfe += 1
            current_cost = to_decimal(current.custo_atual)
            if current_cost == 0:
                still_zero += 1
            items.append(
                {
                    "ean": candidate.ean,
                    "produtoCodigo": candidate.produto_codigo,
                    "descricao": current.descricao or candidate.descricao,
                    "located": bool(current.produto_codigo),
                    "linked": current.ok,
                    "custoAtual": present_money(current_cost),
                    "precoVenda": present_money(current.preco_venda),
                    "dfeStatus": evidence.status,
                    "custoDfe": present_money(evidence.preco_custo) if evidence.preco_custo is not None else None,
                    "origem": candidate.origem,
                }
            )
        return ScanSummary(
            empresa_codigo=self.empresa,
            analyzed=len(items),
            located_on_webposto=located,
            linked_to_company=linked,
            with_valid_dfe=with_dfe,
            still_zero_cost=still_zero,
            api_reads=self.reader.api_reads if self.reader else 0,
            api_writes=self.api_writes,
            sources={
                "pending_cost_update": len(_load_json(self.pending_path)),
                "pending_price_review": len(_load_json(self.price_review_path)),
                "checkpoint": len([k for k in _load_json(self.checkpoint_path) if not str(k).startswith("_")]),
                "accountant_review": len(_load_json(self.accountant_path)),
            },
            items=items,
        )

    def scan(self, key: str) -> ScanSummary:
        evaluated = list(self._iter_evaluated(key))
        summary = self._summary_from_evaluated(evaluated)
        self._write_json(self.output_dir / "scan_summary.json", json.loads(summary.model_dump_json()))
        return summary

    def propose(
        self,
        key: str,
        scan: ScanSummary | None = None,
        *,
        eans: set[str] | None = None,
        persist_aggregates: bool = True,
        event: str = "propose_item",
    ) -> dict[str, Any]:
        evaluated = list(self._iter_evaluated(key, eans))
        if scan is None:
            scan = self._summary_from_evaluated(evaluated)
            if persist_aggregates:
                self._write_json(self.output_dir / "scan_summary.json", json.loads(scan.model_dump_json()))
        buckets: dict[str, list[dict[str, Any]]] = {
            "PROPOSED": [],
            "NO_CHANGE": [],
            "REVIEW_REQUIRED": [],
            "BLOCKED": [],
            "DFE_NOT_FOUND": [],
        }
        above_sale = 0
        for candidate, current, evidence in evaluated:
            decision = self.policy.classify(
                current=current,
                evidence=evidence,
                expected_ean=candidate.ean,
                expected_ncm=current.ncm or candidate.ncm,
                expected_cest=current.cest or candidate.cest,
            )
            previous = self.store.latest_for_ean(candidate.ean)
            proposal = self._build_proposal(candidate, current, evidence, decision)
            persisted = self.store.persist(proposal)
            payload = persisted["proposal"]
            if (
                previous
                and previous.get("proposal_hash") != proposal.proposal_hash
                and persisted.get("created")
            ):
                self.store.mark_superseded(str(previous["proposal_hash"]))
            buckets[proposal.status].append(payload)
            if proposal.custo_acima_da_venda:
                above_sale += 1
            self.audit.record(
                event,
                ean=candidate.ean,
                extra={"status": proposal.status, "hash": proposal.proposal_hash},
            )
        totals = self._totals(buckets)
        result = {
            "engine_version": ENGINE_VERSION,
            "policy_version": POLICY_VERSION,
            "analyzed": scan.analyzed,
            "located_on_webposto": scan.located_on_webposto,
            "linked_to_company": scan.linked_to_company,
            "with_valid_dfe": scan.with_valid_dfe,
            "counts": {name: len(rows) for name, rows in buckets.items()},
            "still_zero_cost": scan.still_zero_cost,
            "above_sale": above_sale,
            "custo_total_atual": str(totals["atual"]),
            "custo_total_proposto": str(totals["proposto"]),
            "api_reads": self.reader.api_reads,
            "api_writes": 0,
        }
        if persist_aggregates:
            self._write_json(self.output_dir / "cost_update_proposals.json", {"items": buckets["PROPOSED"]})
            self._write_json(self.output_dir / "cost_update_no_change.json", {"items": buckets["NO_CHANGE"]})
            self._write_json(self.output_dir / "cost_update_review_required.json", {"items": buckets["REVIEW_REQUIRED"]})
            self._write_json(self.output_dir / "cost_update_blocked.json", {"items": buckets["BLOCKED"]})
            self._write_json(self.output_dir / "cost_update_dfe_not_found.json", {"items": buckets["DFE_NOT_FOUND"]})
            self._write_json(self.output_dir / "propose_summary.json", result)
            (self.output_dir / "COST_UPDATE_REPORT.md").write_text(
                self._report(scan, result, buckets),
                encoding="utf-8",
            )
        else:
            self._write_json(self.output_dir / "recalculate_delta.json", {"items": buckets, "summary": result})
        self.store.flush()
        return result

    def status(self) -> dict[str, Any]:
        index = self.store.load_index()
        return {
            "engine_version": ENGINE_VERSION,
            "proposals": len(index.get("by_hash") or {}),
            "eans": len(index.get("by_ean") or {}),
            "api_writes": 0,
        }

    def show_proposal(self, ean: str) -> dict[str, Any] | None:
        return self.store.latest_for_ean(ean)

    def _build_proposal(
        self,
        candidate: CostUpdateCandidate,
        current: CurrentProductState,
        evidence: CostEvidence,
        decision: dict[str, Any],
    ) -> CostUpdateProposal:
        current_cost = current.custo_atual
        proposed = evidence.preco_custo
        sale = current.preco_venda
        delta = None
        pct = None
        if current_cost is not None and proposed is not None:
            delta = quantize_cost(to_decimal(proposed) - to_decimal(current_cost))
            if to_decimal(current_cost) > 0:
                pct = ratio(delta, to_decimal(current_cost))
        markup_prev = ratio(to_decimal(sale), to_decimal(current_cost)) if sale and current_cost else None
        markup_new = ratio(to_decimal(sale), to_decimal(proposed)) if sale and proposed else None
        margin_prev = (
            ratio(to_decimal(sale) - to_decimal(current_cost), to_decimal(sale))
            if sale and current_cost is not None
            else None
        )
        margin_new = (
            ratio(to_decimal(sale) - to_decimal(proposed), to_decimal(sale))
            if sale and proposed is not None
            else None
        )
        profit = (to_decimal(sale) - to_decimal(proposed)) if sale is not None and proposed is not None else None
        above = bool(sale is not None and proposed is not None and to_decimal(proposed) > to_decimal(sale))
        nfe = self.resolver.sanitize(evidence)
        now = datetime.now(timezone.utc).isoformat()
        proposal_hash = _proposal_hash(
            self.empresa,
            candidate.produto_codigo,
            candidate.ean,
            current_cost,
            proposed,
            nfe,
        )
        previous = self.store.latest_for_ean(candidate.ean)
        version = 1
        previous_hash = None
        if previous and previous.get("proposal_hash") != proposal_hash:
            version = int(previous.get("version") or 1) + 1
            previous_hash = previous.get("proposal_hash")
        return CostUpdateProposal(
            proposal_id=f"cu_{candidate.ean}_{proposal_hash[:12]}",
            proposal_hash=proposal_hash,
            version=version,
            status=decision["status"],
            empresa_codigo=self.empresa,
            produto_codigo=candidate.produto_codigo,
            ean=candidate.ean,
            descricao=current.descricao or candidate.descricao,
            custo_anterior=current_cost,
            custo_proposto=proposed,
            diferenca_absoluta=delta,
            variacao_percentual=pct,
            preco_venda=sale,
            markup_anterior=markup_prev,
            markup_projetado=markup_new,
            margem_anterior=margin_prev,
            margem_projetada=margin_new,
            lucro_unitario_estimado=profit,
            custo_acima_da_venda=above,
            nfe={
                "numero": nfe.get("numero"),
                "serie": nfe.get("serie"),
                "emissao": nfe.get("emissao"),
                "accessKeyMasked": nfe.get("access_key_masked"),
                "documentId": nfe.get("document_id"),
                "calculo": nfe.get("calculo"),
                "status": nfe.get("status"),
            },
            formula=evidence.calculo,
            confianca=decision["confianca"],
            riscos=decision["riscos"],
            policy_version=POLICY_VERSION,
            created_at=now,
            updated_at=now,
            previous_proposal_hash=previous_hash,
        )

    def _totals(self, buckets: dict[str, list[dict[str, Any]]]) -> dict[str, Decimal]:
        atual = Decimal("0")
        proposto = Decimal("0")
        for rows in buckets.values():
            for row in rows:
                if row.get("custo_anterior") is not None:
                    atual += to_decimal(row["custo_anterior"])
                if row.get("custo_proposto") is not None:
                    proposto += to_decimal(row["custo_proposto"])
        return {"atual": atual, "proposto": proposto}

    def _report(self, scan: ScanSummary, result: dict[str, Any], buckets: dict[str, list]) -> str:
        examples = []
        for row in (buckets.get("PROPOSED") or buckets.get("REVIEW_REQUIRED") or [])[:5]:
            examples.append(
                f"- EAN {row.get('ean')} produto {row.get('produto_codigo')} "
                f"atual {row.get('custo_anterior')} -> proposto {row.get('custo_proposto')} "
                f"({row.get('status')})"
            )
        counts = result["counts"]
        return (
            "# Relatorio de propostas de custo — 118508\n\n"
            f"Motor {ENGINE_VERSION} / politica {POLICY_VERSION}. Somente GET. API writes = 0.\n\n"
            f"- Analisados: {result['analyzed']}\n"
            f"- Localizados no WebPosto: {result['located_on_webposto']}\n"
            f"- Vinculados a 118508: {result['linked_to_company']}\n"
            f"- DF-e valido: {result['with_valid_dfe']}\n"
            f"- PROPOSED: {counts['PROPOSED']}\n"
            f"- NO_CHANGE: {counts['NO_CHANGE']}\n"
            f"- REVIEW_REQUIRED: {counts['REVIEW_REQUIRED']}\n"
            f"- BLOCKED: {counts['BLOCKED']}\n"
            f"- DFE_NOT_FOUND: {counts['DFE_NOT_FOUND']}\n"
            f"- Ainda com custo zero: {result['still_zero_cost']}\n"
            f"- Custo acima da venda: {result['above_sale']}\n"
            f"- Custo total atual: {result['custo_total_atual']}\n"
            f"- Custo total proposto: {result['custo_total_proposto']}\n"
            f"- API reads: {result['api_reads']}\n"
            f"- API writes: 0\n\n"
            "## Exemplos sanitizados\n\n"
            + ("\n".join(examples) or "- nenhum")
            + "\n"
        )

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _candidate_from_pending(row: dict[str, Any], empresa: int, origem: str) -> CostUpdateCandidate:
    return CostUpdateCandidate(
        empresa_codigo=empresa,
        produto_codigo=int(row["produtoCodigo"]) if row.get("produtoCodigo") else None,
        ean=str(row.get("ean")),
        descricao=row.get("descricao"),
        custo_atual=row.get("precoCustoCadastrado"),
        preco_venda=row.get("precoVenda"),
        origem=origem,
    )


def _proposal_hash(
    empresa: int,
    produto_codigo: int | None,
    ean: str,
    custo_atual: Decimal | None,
    custo_proposto: Decimal | None,
    nfe: dict[str, Any],
) -> str:
    payload = {
        "empresa": empresa,
        "produtoCodigo": produto_codigo,
        "ean": ean,
        "custoAtual": str(custo_atual) if custo_atual is not None else None,
        "custoProposto": str(custo_proposto) if custo_proposto is not None else None,
        "dfe": {
            "documentId": nfe.get("document_id"),
            "accessKeyMasked": nfe.get("access_key_masked"),
            "precoCusto": nfe.get("preco_custo"),
        },
        "policyVersion": POLICY_VERSION,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
