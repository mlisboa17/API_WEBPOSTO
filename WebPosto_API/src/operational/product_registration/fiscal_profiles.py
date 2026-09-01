"""Perfis fiscais reutilizaveis para cadastro em lote.

Um perfil e um conjunto de produtos que compartilham familia comercial, NCM, CEST,
tratamento observado na entrada, base de ICMS, base de PIS/COFINS e CFOP de saida. A
aprovacao passa a ser por perfil: validado o canario, os demais produtos do mesmo perfil
seguem sem decisao individual.

O nivel do perfil expressa a forca da evidencia, nao a preferencia comercial:

    PROFILE_A  nota do proprio produto, sem conflito
    PROFILE_B  mesmo NCM e CEST, mesma familia, evidencia em varias notas e fornecedores
    PROFILE_C  mesmo NCM e CEST, mesma familia, evidencia restrita e sem concorrencia
    PROFILE_D  sem evidencia de entrada; correspondencia mais especifica das tabelas
    PROFILE_SPECIAL  categorias de regime proprio, sempre isoladas

Familia diferente nunca entra no mesmo perfil, ainda que o NCM comece igual: prefixo de
NCM nao e evidencia de tratamento.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .fiscal_resolver import ST_ABSENT, ST_ANTICIPATION_POSSIBLE, ST_PROVEN

LEVEL_A = "PROFILE_A"
LEVEL_B = "PROFILE_B"
LEVEL_C = "PROFILE_C"
LEVEL_D = "PROFILE_D"
LEVEL_SPECIAL = "PROFILE_SPECIAL"

WAVE_BY_LEVEL = {LEVEL_A: 1, LEVEL_B: 1, LEVEL_C: 1, LEVEL_D: 2, LEVEL_SPECIAL: 4}

TREATMENT_SUBSTITUTED = "ST"
TREATMENT_TAXED = "TRIBUTADO"

CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_LOW = "LOW"
CONFIDENCE_VERY_LOW = "VERY_LOW"

RISK_ASSUMED = "ASSUMED_BY_OWNER"

# Evidencia ampla o suficiente para dispensar a leitura caso a caso.
STRONG_INVOICES = 3
STRONG_SUPPLIERS = 2
# Fracao minima dos itens de evidencia que precisa ser da familia do candidato.
MIN_FAMILY_SHARE = 0.7

CATEGORIES_WITH_OWN_REGIME = {
    "22": "BEBIDA_ALCOOLICA",
    "24": "TABACO",
    "30": "MEDICAMENTO",
    "27": "COMBUSTIVEL",
    "36": "PIROTECNICO",
}


@dataclass
class EvidenceReading:
    """Leitura da evidencia de um par NCM e CEST, ja resumida."""

    treatment: str | None
    entry_rate: float | None
    items: int
    invoices: int
    suppliers: int
    families: dict[str, int]
    cst_distribution: dict[str, int]
    conflict: str | None = None
    family_evidence: str | None = None


@dataclass
class Placement:
    """Onde o produto foi colocado, e por que."""

    level: str | None
    treatment: str | None = None
    blocked_reason: str | None = None
    detail: str | None = None
    evidence: EvidenceReading | None = None
    confidence: str = CONFIDENCE_LOW
    entry_rate: float | None = None


@dataclass
class Profile:
    """Perfil fiscal agregado, pronto para serializacao."""

    profile_id: str
    level: str
    descricao: str
    familias_permitidas: list[str]
    ncms: list[str]
    cests: list[str]
    tratamento_observado: str
    referencia_icms: str | None
    referencia_pis_cofins: str | None
    cfop_entrada: str
    cfop_saida: str
    tributacao_monofasica: int
    tributo_icms: dict[str, Any]
    tributo_pis_cofins: dict[str, Any]
    evidencias: dict[str, Any]
    confidence: str
    fiscal_risk: str
    requires_accountant_review: bool
    onda: int
    produtos: list[dict[str, Any]] = field(default_factory=list)
    canario_ean: str | None = None
    canario_produto_codigo: int | None = None
    profile_canary_status: str = "PENDING"
    canario_origem: str | None = None

    @property
    def candidatos(self) -> int:
        return len(self.produtos)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "level": self.level,
            "descricao": self.descricao,
            "familias_permitidas": self.familias_permitidas,
            "ncms": self.ncms,
            "cests": self.cests,
            "tratamento_observado": self.tratamento_observado,
            "referencia_icms": self.referencia_icms,
            "referencia_pis_cofins": self.referencia_pis_cofins,
            "cfop_entrada": self.cfop_entrada,
            "cfop_saida": self.cfop_saida,
            "tributacao_monofasica": self.tributacao_monofasica,
            "tributo_icms": self.tributo_icms,
            "tributo_pis_cofins": self.tributo_pis_cofins,
            "evidencias": self.evidencias,
            "confidence": self.confidence,
            "fiscal_risk": self.fiscal_risk,
            "requires_accountant_review": self.requires_accountant_review,
            "onda": self.onda,
            "quantidade_candidatos": self.candidatos,
            "produto_canario": self.canario_ean,
            "produto_canario_codigo": self.canario_produto_codigo,
            "profile_canary_status": self.profile_canary_status,
            "canario_origem": self.canario_origem,
            "produtos": self.produtos,
        }


# Itens de consumo fumigeno que nao ficam no capitulo 24: o NCM os trata como carvao,
# papel ou acessorio, mas comercialmente pertencem a tabacaria e seguem com ela.
SMOKING_RELATED_TERMS = (
    "NARGUILE",
    "NARGUILLE",
    "CIGARRO",
    "CIGARRILHA",
    "CHARUTO",
    "TABACO",
    "FUMO",
    "PITEIRA",
    "SEDA P",
    "SEDA PARA",
)


def special_category(ncm: str | None, description: str | None = None) -> str | None:
    """Categoria de regime proprio do produto, quando houver.

    O NCM decide primeiro; a descricao entra para os fumigenos que o NCM nao revela.
    """
    if ncm and len(ncm) >= 2:
        found = CATEGORIES_WITH_OWN_REGIME.get(ncm[:2])
        if found:
            return found
    text = (description or "").upper()
    if any(term in text for term in SMOKING_RELATED_TERMS):
        return "TABACARIA_CORRELATO"
    return None


def read_evidence(
    entries: list[dict[str, Any]], summary: dict[str, Any], candidate_family: str | None
) -> EvidenceReading:
    """Interpreta a evidencia do par NCM e CEST e aponta o conflito, se existir.

    A convergencia e exigida no tratamento e na aliquota: itens que entraram tributados a
    aliquotas diferentes descrevem tratamentos diferentes para a mesma mercadoria, e nesse
    caso nenhuma base pode ser eleita.
    """
    reading = EvidenceReading(
        treatment=None,
        entry_rate=None,
        items=summary["itens"],
        invoices=summary["notasDistintas"],
        suppliers=summary["fornecedoresDistintos"],
        families=summary["familiasObservadas"],
        cst_distribution=summary["distribuicaoCst"],
    )
    classifications = set(summary["classificacoes"])
    if not entries:
        reading.conflict = "SEM_EVIDENCIA"
        return reading

    # O CEST identifica a mercadoria no regime de substituição, então itens de mesmo NCM e
    # CEST já falam do mesmo tratamento. A família serve para detectar contradição
    # evidente, e só pode contradizer quando é reconhecida nos dois lados: descrição de
    # fornecedor que não se classifica é silêncio, não divergência.
    recognized = [e["familiaComercial"] for e in entries if e.get("familiaComercial")]
    if candidate_family and recognized:
        same_family = sum(1 for f in recognized if f == candidate_family)
        if same_family / len(recognized) < MIN_FAMILY_SHARE:
            reading.conflict = "FAMILIA_COMERCIAL_DIVERGENTE"
            return reading
        reading.family_evidence = "CONFIRMADA"
    else:
        reading.family_evidence = "NEUTRA"

    if classifications == {ST_PROVEN}:
        reading.treatment = TREATMENT_SUBSTITUTED
        return reading
    if classifications and classifications <= {ST_ABSENT, ST_ANTICIPATION_POSSIBLE}:
        rates = {
            round(float(e["aliquotaEntrada"]), 4)
            for e in entries
            if e.get("aliquotaEntrada") is not None
        }
        if len(rates) != 1:
            reading.conflict = "ALIQUOTAS_DE_ENTRADA_DIVERGENTES"
            return reading
        reading.treatment = TREATMENT_TAXED
        reading.entry_rate = rates.pop()
        return reading

    reading.conflict = "TRATAMENTOS_CONCORRENTES_NA_EVIDENCIA"
    return reading


def place_from_evidence(reading: EvidenceReading) -> Placement:
    """Escolhe entre analogia forte e reduzida, ou bloqueia por conflito."""
    if reading.conflict:
        return Placement(level=None, blocked_reason=reading.conflict, evidence=reading)
    # Analogia forte exige também que a família tenha sido confirmada: sem isso a
    # semelhança se apoia apenas no par NCM e CEST, e o nível cai.
    strong = (
        reading.invoices >= STRONG_INVOICES
        and reading.suppliers >= STRONG_SUPPLIERS
        and reading.family_evidence == "CONFIRMADA"
    )
    return Placement(
        level=LEVEL_B if strong else LEVEL_C,
        treatment=reading.treatment,
        evidence=reading,
        confidence=CONFIDENCE_LOW,
        entry_rate=reading.entry_rate,
    )


def build_profile_id(
    level: str, family: str | None, ncm: str, cest: str | None, icms_reference: str | None
) -> str:
    """Identificador estavel e legivel do perfil."""
    return "-".join(
        [
            level.replace("PROFILE_", "P"),
            (family or "SEM_FAMILIA"),
            ncm,
            (cest or "SEM_CEST"),
            (icms_reference or "SEM_REF"),
        ]
    )


# Do mais forte para o mais fraco: o perfil unificado assume o nivel mais fraco entre os
# produtos, porque a aprovacao vale para todos eles.
LEVEL_STRENGTH = {LEVEL_A: 0, LEVEL_B: 1, LEVEL_C: 2, LEVEL_D: 3, LEVEL_SPECIAL: 4}


def weakest_level(levels: list[str]) -> str:
    return max(levels, key=lambda level: LEVEL_STRENGTH[level])


ORIGIN_OWN_INVOICE = "NF_E_DO_PRODUTO"
ORIGIN_ANALOGY = "ANALOGIA_NCM_CEST"
ORIGIN_LOCAL_TABLE = "TABELA_LOCAL_POR_CEST"


def audit_trail(origin: str, confidence: str) -> dict[str, str]:
    """De onde veio a base e quem responde por ela.

    Sem lancamento fiscal do proprio produto nao existe tratamento comprovado, e a
    trilha precisa dizer isso com clareza para quem revisar depois.
    """
    if origin == ORIGIN_OWN_INVOICE:
        return {
            "tax_basis_source": "OWN_INVOICE",
            "entry_tax_evidence": "AVAILABLE",
            "decision_authority": (
                "PIPELINE_EVIDENCE" if confidence == CONFIDENCE_HIGH else RISK_ASSUMED
            ),
        }
    if origin == ORIGIN_ANALOGY:
        return {
            "tax_basis_source": "NCM_CEST_ANALOGY",
            "entry_tax_evidence": "UNAVAILABLE_FOR_THIS_PRODUCT",
            "decision_authority": "OWNER_RISK_ACCEPTANCE",
        }
    return {
        "tax_basis_source": "LOCAL_TABLE_INFERENCE",
        "entry_tax_evidence": "UNAVAILABLE",
        "decision_authority": "OWNER_RISK_ACCEPTANCE",
    }


def payload_key(profile: dict[str, Any]) -> tuple:
    """Identidade do payload fiscal que a API vai receber.

    Dois produtos de NCM diferente podem gerar exatamente o mesmo payload tributario. Se
    geram, um unico canario prova a aceitacao do payload para os dois: o que o canario
    demonstra e que a combinacao de referencias, CFOP e tributos e aceita e volta intacta.
    NCM e CEST continuam sendo conferidos produto a produto na verificacao individual.
    """
    return (
        profile["referencia_icms"],
        profile["referencia_pis_cofins"],
        profile["cfop_entrada"],
        profile["cfop_saida"],
        profile["tributacao_monofasica"],
        bool(profile["cests"]),
        json.dumps(profile["tributo_icms"], sort_keys=True),
        json.dumps(profile["tributo_pis_cofins"], sort_keys=True),
    )


def payload_id(profile: dict[str, Any]) -> str:
    """Identificador legivel do payload fiscal."""
    return "-".join(
        [
            "PAYLOAD",
            str(profile["referencia_icms"] or "SEM_REF"),
            str(profile["referencia_pis_cofins"] or "SEM_REF"),
            f"E{profile['cfop_entrada']}",
            f"S{profile['cfop_saida']}",
            f"MONO{profile['tributacao_monofasica']}",
            "COM_CEST" if profile["cests"] else "SEM_CEST",
        ]
    )


def resolve_profile_family(families: list[str | None]) -> str | None | bool:
    """Familia de um grupo de produtos que compartilham base fiscal.

    Produto cuja descricao nao se classifica e compativel com qualquer familia, porque
    nada afirma. Duas familias reconhecidas diferentes nao se unificam: mesmo com NCM e
    CEST iguais, manter separado preserva a leitura de quem revisa.
    """
    recognized = {family for family in families if family}
    if len(recognized) > 1:
        return False
    return next(iter(recognized), None)
