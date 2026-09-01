"""Classificação fiscal baseada em evidência da NF-e de entrada.

Regra central: a base de ICMS nunca é inferida a partir do NCM. CST 00 (operação
tributada integralmente) e CST 60 (ICMS já recolhido por substituição tributária) são
situações distintas e não podem ser tratadas como equivalentes. Um produto que entrou
tributado não herda a base de um produto que entrou substituído, ainda que ambos sejam
alimentos com NCM do capítulo 19.

Sem evidência de entrada, o resolver não atribui base: devolve revisão.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .schemas import ProductAnalysis

# Classificação da situação de ICMS observada na entrada.
ST_PROVEN = "ST_COMPROVADA"
ST_ABSENT = "SEM_ST_COMPROVADA"
ST_ANTICIPATION_POSSIBLE = "ANTECIPACAO_POSSIVEL"
ST_NO_EVIDENCE = "SEM_EVIDENCIA_DE_ENTRADA"

CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_LOW = "LOW"
CONFIDENCE_NONE = "NONE"

RISK_ASSUMED_BY_OWNER = "ASSUMED_BY_OWNER"
RISK_NONE = "NONE"

# CST de ICMS que caracterizam mercadoria já substituída na entrada.
CST_SUBSTITUTED = frozenset({"60", "060", "10", "010", "30", "070", "70"})
# CST de ICMS que caracterizam operação tributada integralmente.
CST_FULLY_TAXED = frozenset({"00", "000", "20", "020"})

MIN_EQUIVALENTS_FOR_INFERENCE = 5
MIN_SHARE_FOR_INFERENCE = 0.80


class FiscalEvidenceError(Exception):
    """Evidência fiscal ausente ou incoerente."""


def value_or_missing(value: Any) -> Any:
    """Devolve o valor ou None. Nunca converte vazio em zero.

    Transformar campo vazio em zero foi a origem do RET=3 e mascara ausência de
    informação como se fosse alíquota zero declarada.
    """
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def require_declared(value: Any, field_name: str) -> Any:
    """Falha explicitamente quando um campo obrigatório não foi declarado."""
    resolved = value_or_missing(value)
    if resolved is None:
        raise FiscalEvidenceError(f"Campo fiscal não declarado: {field_name}")
    return resolved


@dataclass(frozen=True)
class EntryEvidence:
    """Tributação observada na NF-e de entrada do produto."""

    cst_icms: str | None
    icms_st_retido: float | None
    cest: str | None
    ncm: str | None
    cfop_fornecedor: str | None = None
    cst_pis: str | None = None
    cst_cofins: str | None = None
    invoice_reference: str | None = None

    @property
    def has_st_withheld(self) -> bool:
        return bool(self.icms_st_retido) and float(self.icms_st_retido) > 0


@dataclass
class FiscalDecision:
    """Resultado da classificação fiscal de um produto."""

    st_classification: str
    icms_basis: dict[str, Any] | None = None
    pis_cofins_basis: dict[str, Any] | None = None
    icms_table_reference: str | None = None
    pis_cofins_table_reference: str | None = None
    confidence: str = CONFIDENCE_NONE
    fiscal_risk: str = RISK_NONE
    requires_accountant_review: bool = True
    justification: str = ""
    equivalents_considered: int = 0
    equivalents_distribution: dict[str, int] = field(default_factory=dict)
    inferred_fields: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    @property
    def can_register(self) -> bool:
        return self.icms_basis is not None and self.pis_cofins_basis is not None and not self.blockers


def classify_entry(evidence: EntryEvidence) -> str:
    """Classifica a situação de ST a partir da NF-e, sem olhar o NCM."""
    cst = value_or_missing(evidence.cst_icms)
    if cst is None:
        return ST_NO_EVIDENCE

    cst = str(cst).strip()
    if cst in CST_SUBSTITUTED or evidence.has_st_withheld:
        return ST_PROVEN
    if cst in CST_FULLY_TAXED:
        # CEST indica mercadoria sujeita a ST no estado, mas a compra veio tributada:
        # pode haver antecipação a cargo do adquirente. Isso não se declara sozinho.
        if value_or_missing(evidence.cest):
            return ST_ANTICIPATION_POSSIBLE
        return ST_ABSENT
    return ST_NO_EVIDENCE


def evaluate_equivalents(distribution: dict[str, int]) -> tuple[str | None, str, int, float]:
    """Avalia a distribuição de bases entre produtos equivalentes.

    Devolve a base predominante, o nível de confiança, o total e a participação.
    A distribuição precisa vir medida; um dicionário vazio significa que não há
    evidência mensurável, não que exista consenso.
    """
    total = sum(distribution.values())
    if total == 0:
        return None, CONFIDENCE_NONE, 0, 0.0

    reference, count = max(distribution.items(), key=lambda item: item[1])
    share = count / total
    if total >= MIN_EQUIVALENTS_FOR_INFERENCE and share >= MIN_SHARE_FOR_INFERENCE:
        return reference, CONFIDENCE_HIGH, total, share
    return reference, CONFIDENCE_LOW, total, share


class FiscalResolver:
    """Resolve a base fiscal a partir de evidência, nunca a partir do NCM."""

    BLOCKED_KEYWORDS = [
        "combustível",
        "gasolina",
        "álcool",
        "gás",
        "medicamento",
        "cigarro",
        "cigarrilha",
    ]

    def check_blocked(self, description: str) -> str | None:
        desc_lower = (description or "").lower()
        for keyword in self.BLOCKED_KEYWORDS:
            if keyword in desc_lower:
                return f"BLOCKED_KEYWORD_{keyword.upper()}"
        return None

    def decide(
        self,
        evidence: EntryEvidence,
        *,
        substituted_basis: dict[str, Any] | None = None,
        substituted_table_reference: str | None = None,
        taxed_basis: dict[str, Any] | None = None,
        taxed_table_reference: str | None = None,
        pis_cofins_basis: dict[str, Any] | None = None,
        pis_cofins_table_reference: str | None = None,
        equivalents_distribution: dict[str, int] | None = None,
        basis_catalog: dict[str, dict[str, Any]] | None = None,
        no_evidence_candidates: list[tuple[str, dict[str, Any]]] | None = None,
    ) -> FiscalDecision:
        """Decide a base fiscal do produto.

        `substituted_basis` só é aplicada quando a NF-e comprova substituição.
        `taxed_basis` só é aplicada quando a entrada veio tributada, e nunca pode conter
        CST de saída de mercadoria substituída.
        `equivalents_distribution` precisa ser medida em produtos da própria empresa;
        sem medição, cai para a alíquota da NF-e com confiança baixa.
        """
        classification = classify_entry(evidence)
        distribution = equivalents_distribution or {}

        if classification == ST_NO_EVIDENCE:
            return self._decide_without_entry_evidence(
                evidence,
                candidates=no_evidence_candidates or [],
                pis_cofins_basis=pis_cofins_basis,
                pis_cofins_table_reference=pis_cofins_table_reference,
            )

        if classification == ST_PROVEN:
            if substituted_basis is None or substituted_table_reference is None:
                return FiscalDecision(
                    st_classification=classification,
                    confidence=CONFIDENCE_NONE,
                    requires_accountant_review=True,
                    justification=(
                        "Substituição comprovada na entrada, mas nenhuma tabela local "
                        "corresponde integralmente à base exigida"
                    ),
                    blockers=["NO_MATCHING_ST_TABLE"],
                )
            return FiscalDecision(
                st_classification=classification,
                icms_basis=dict(substituted_basis),
                icms_table_reference=substituted_table_reference,
                pis_cofins_basis=dict(pis_cofins_basis) if pis_cofins_basis else None,
                pis_cofins_table_reference=pis_cofins_table_reference,
                confidence=CONFIDENCE_HIGH,
                fiscal_risk=RISK_NONE,
                requires_accountant_review=False,
                justification=(
                    f"NF-e {evidence.invoice_reference} comprova ICMS por substituição "
                    f"(CST {evidence.cst_icms}); base de ST aplicada com correspondência "
                    f"integral na tabela {substituted_table_reference}"
                ),
                blockers=[] if pis_cofins_basis else ["NO_MATCHING_PIS_COFINS_TABLE"],
            )

        # A partir daqui a entrada veio tributada: a base do produto substituído
        # (padrão BONO/NEGRESCO) é proibida, independentemente do NCM.
        reference, confidence, total, share = evaluate_equivalents(distribution)
        catalog = basis_catalog or {}

        if reference is None and taxed_basis is not None:
            # Correspondência mais específica disponível: a alíquota destacada na própria
            # NF-e de entrada. Não é consenso entre equivalentes, então a confiança é
            # baixa e a revisão contábil é obrigatória.
            guard = str(taxed_basis.get("cstSaida") or "")
            if guard in CST_SUBSTITUTED:
                return FiscalDecision(
                    st_classification=classification,
                    confidence=CONFIDENCE_NONE,
                    fiscal_risk=RISK_ASSUMED_BY_OWNER,
                    requires_accountant_review=True,
                    justification=(
                        f"Base oferecida para produto tributado usa CST de saída {guard}, "
                        f"própria de mercadoria substituída: recusada"
                    ),
                    blockers=["SUBSTITUTED_BASIS_OFFERED_TO_TAXED_PRODUCT"],
                )
            return FiscalDecision(
                st_classification=classification,
                icms_basis=dict(taxed_basis),
                icms_table_reference=taxed_table_reference,
                pis_cofins_basis=dict(pis_cofins_basis) if pis_cofins_basis else None,
                pis_cofins_table_reference=pis_cofins_table_reference,
                confidence=CONFIDENCE_LOW,
                fiscal_risk=RISK_ASSUMED_BY_OWNER,
                requires_accountant_review=True,
                justification=(
                    f"NF-e {evidence.invoice_reference} destaca ICMS com CST "
                    f"{evidence.cst_icms} e alíquota "
                    f"{taxed_basis.get('percentualIcmsEntrada')}%; tabela "
                    f"{taxed_table_reference} corresponde a essa alíquota de entrada. "
                    f"Base de saída é inferência provisória, não medida em equivalentes"
                ),
                equivalents_considered=total,
                equivalents_distribution=dict(distribution),
                blockers=[] if pis_cofins_basis else ["NO_MATCHING_PIS_COFINS_TABLE"],
            )

        if reference is None:
            return FiscalDecision(
                st_classification=classification,
                confidence=CONFIDENCE_NONE,
                fiscal_risk=RISK_ASSUMED_BY_OWNER,
                requires_accountant_review=True,
                justification=(
                    "Entrada tributada integralmente e sem distribuição mensurável de bases "
                    "entre produtos equivalentes da empresa: a base de saída não pode ser "
                    "inferida a partir de evidência"
                ),
                equivalents_considered=total,
                equivalents_distribution=dict(distribution),
                blockers=["NO_MEASURABLE_EQUIVALENT_BASIS"],
            )

        basis = catalog.get(reference)
        if basis is None:
            return FiscalDecision(
                st_classification=classification,
                confidence=confidence,
                fiscal_risk=RISK_ASSUMED_BY_OWNER,
                requires_accountant_review=True,
                justification=(
                    f"Base predominante entre equivalentes ({reference}) não existe nas "
                    f"tabelas locais: referência não pode ser inventada"
                ),
                equivalents_considered=total,
                equivalents_distribution=dict(distribution),
                blockers=["BASIS_REFERENCE_NOT_IN_LOCAL_TABLES"],
            )

        return FiscalDecision(
            st_classification=classification,
            icms_basis=dict(basis),
            icms_table_reference=reference,
            pis_cofins_basis=dict(pis_cofins_basis) if pis_cofins_basis else None,
            pis_cofins_table_reference=pis_cofins_table_reference,
            confidence=confidence,
            fiscal_risk=RISK_ASSUMED_BY_OWNER,
            requires_accountant_review=True,
            justification=(
                f"Entrada tributada (CST {evidence.cst_icms}); base inferida da referência "
                f"{reference}, predominante em {share:.0%} de {total} produtos equivalentes "
                f"da empresa. Inferência provisória, sujeita a revisão contábil"
            ),
            equivalents_considered=total,
            equivalents_distribution=dict(distribution),
            blockers=[] if pis_cofins_basis else ["NO_MATCHING_PIS_COFINS_TABLE"],
        )

    def _decide_without_entry_evidence(
        self,
        evidence: EntryEvidence,
        *,
        candidates: list[tuple[str, dict[str, Any]]],
        pis_cofins_basis: dict[str, Any] | None,
        pis_cofins_table_reference: str | None,
    ) -> FiscalDecision:
        """Decide quando não há NF-e de entrada para o produto.

        Sem compra registrada não há como provar substituição, então nenhuma base é
        aplicada por padrão — em particular, CST 060 não é presumido. A base só é aceita
        quando o conjunto de candidatos sustentados por NCM e CEST converge para uma
        única referência de tabela local. Duas hipóteses plausíveis bloqueiam o produto.
        """
        if not candidates:
            return FiscalDecision(
                st_classification=ST_NO_EVIDENCE,
                confidence=CONFIDENCE_NONE,
                fiscal_risk=RISK_ASSUMED_BY_OWNER,
                requires_accountant_review=True,
                justification=(
                    "Sem NF-e de entrada e sem base sustentada por NCM e CEST em produtos "
                    "de tributação já comprovada: nenhuma base é atribuída"
                ),
                blockers=["NO_ENTRY_TAX_EVIDENCE"],
            )

        distinct = {reference for reference, _ in candidates}
        if len(distinct) > 1:
            return FiscalDecision(
                st_classification=ST_NO_EVIDENCE,
                confidence=CONFIDENCE_NONE,
                fiscal_risk=RISK_ASSUMED_BY_OWNER,
                requires_accountant_review=True,
                justification=(
                    f"Sem NF-e de entrada e com mais de uma base plausível "
                    f"({sorted(distinct)}): escolher uma seria arbitrar tributação"
                ),
                blockers=["AMBIGUOUS_BASIS_WITHOUT_ENTRY_EVIDENCE"],
            )

        reference, basis = candidates[0]
        return FiscalDecision(
            st_classification=ST_NO_EVIDENCE,
            icms_basis=dict(basis),
            icms_table_reference=reference,
            pis_cofins_basis=dict(pis_cofins_basis) if pis_cofins_basis else None,
            pis_cofins_table_reference=pis_cofins_table_reference,
            # Sem evidência de entrada a confiança nunca é alta, mesmo com base única.
            confidence=CONFIDENCE_LOW,
            fiscal_risk=RISK_ASSUMED_BY_OWNER,
            requires_accountant_review=True,
            justification=(
                f"Sem NF-e de entrada para o EAN. Base {reference} é a única sustentada por "
                f"NCM {evidence.ncm} e CEST {evidence.cest} entre produtos cuja tributação "
                f"foi comprovada por documento fiscal. Inferência assumida pelo titular"
            ),
            equivalents_considered=len(candidates),
            inferred_fields=["tributoIcms", "cstSaida", "percentualIcmsSaida", "cdCfopSaida"],
            blockers=[] if pis_cofins_basis else ["NO_MATCHING_PIS_COFINS_TABLE"],
        )

    def resolve(
        self,
        analysis: ProductAnalysis,
        ncm: str | None = None,
        description: str = "",
        evidence: EntryEvidence | None = None,
        **decide_kwargs: Any,
    ) -> ProductAnalysis:
        """Aplica a decisão fiscal ao objeto de análise.

        Sem `evidence`, nenhuma base é atribuída e o produto vai para revisão: não há
        atalho por NCM.
        """
        blocked = self.check_blocked(description)
        if blocked:
            analysis.status = "BLOCKED"
            analysis.gate = blocked
            analysis.validation_issues.append(f"Produto bloqueado: {blocked}")
            analysis.risk_level = "ALTO_RISCO"
            return analysis

        if not ncm:
            analysis.status = "REVIEW_REQUIRED"
            analysis.validation_issues.append("NCM não informado")
            analysis.risk_level = "ALTO_RISCO"
            return analysis

        analysis.ncm = "".join(c for c in str(ncm) if c.isdigit()).zfill(8)[-8:]

        if evidence is None:
            analysis.status = "REVIEW_REQUIRED"
            analysis.validation_issues.append(
                "Sem evidência de tributação na NF-e de entrada: base fiscal não atribuída"
            )
            analysis.risk_level = "ALTO_RISCO"
            analysis.field_provenance["icms_model"] = {
                "source": "NONE",
                "confidence": CONFIDENCE_NONE,
                "reason": "NO_ENTRY_EVIDENCE",
            }
            return analysis

        decision = self.decide(evidence, **decide_kwargs)

        analysis.field_provenance["icms_model"] = {
            "source": f"ENTRY_EVIDENCE_{decision.st_classification}",
            "confidence": decision.confidence,
            "tableReference": decision.icms_table_reference,
            "fiscalRisk": decision.fiscal_risk,
            "requiresAccountantReview": decision.requires_accountant_review,
            "justification": decision.justification,
        }

        if not decision.can_register:
            analysis.status = "REVIEW_REQUIRED"
            analysis.risk_level = "ALTO_RISCO"
            analysis.validation_issues.extend(decision.blockers)
            return analysis

        analysis.tributo_icms = decision.icms_basis
        analysis.tributo_pis_cofins = decision.pis_cofins_basis
        analysis.field_provenance["pis_cofins_model"] = {
            "source": "LOCAL_TABLE",
            "confidence": decision.confidence,
            "tableReference": decision.pis_cofins_table_reference,
        }
        if decision.requires_accountant_review:
            analysis.risk_level = "MÉDIO_RISCO"
        return analysis
