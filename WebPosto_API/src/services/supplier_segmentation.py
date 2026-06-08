"""Segmentação corporativa de fornecedores — F01.4-D."""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from src.services.supplier_mdm import canonical_supplier_name, normalize_supplier_key

# Fornecedores homologados — parceria estratégica legítima (sem alerta falso de concentração)
STRATEGIC_HOMOLOGATED: frozenset[str] = frozenset({"VIBRA", "IPIRANGA", "BR DISTRIBUIDORA"})

V3_TO_SUPPLIER_CATEGORY: dict[str, tuple[str, str]] = {
    "ENERGIA": ("OPERACIONAL", "Energia"),
    "PESSOAL": ("RH", "Folha"),
    "FINANCEIRO": ("FINANCEIRO", "Tarifas"),
    "TRIBUTÁRIO": ("TRIBUTARIO", "Impostos"),
    "COMPRAS": ("ESTRATEGICOS", "Conveniencia Core"),
    "VEÍCULOS": ("OPERACIONAL", "Manutencao"),
    "MANUTENÇÃO": ("OPERACIONAL", "Manutencao"),
    "SERVIÇOS": ("OPERACIONAL", "Infraestrutura"),
    "TECNOLOGIA": ("OPERACIONAL", "Internet"),
    "FRETES": ("OPERACIONAL", "Infraestrutura"),
    "MARKETING": ("OPERACIONAL", "Infraestrutura"),
    "SEGUROS": ("FINANCEIRO", "Tarifas"),
    "ALUGUÉIS": ("OPERACIONAL", "Infraestrutura"),
}

PLANO_KEYWORDS: list[tuple[str, str, str]] = [
    (r"COMBUST|DIESEL|GASOLINA|REVENDA|POSTO", "ESTRATEGICOS", "Combustiveis"),
    (r"LUBRIF|OLEO", "ESTRATEGICOS", "Lubrificantes"),
    (r"CONVEN|LOJA|FOOD", "ESTRATEGICOS", "Conveniencia Core"),
    (r"SALAR|FOLHA|PESSOAL|VALE", "RH", "Folha"),
    (r"UNIFORM|FARDAM|EPI", "RH", "Uniforme"),
    (r"BANCO|TARIF|CARTAO|ADQUIRENTE", "FINANCEIRO", "Tarifas"),
    (r"IMPOST|TRIBUT|TAXA|CONTRIB", "TRIBUTARIO", "Impostos"),
    (r"ENERG|LUZ|AGUA|INTERNET|TELEFON", "OPERACIONAL", "Energia"),
    (r"MANUT|LIMPEZA|INFRA", "OPERACIONAL", "Manutencao"),
]

CENTRO_KEYWORDS: list[tuple[str, str, str]] = [
    (r"PISTA", "ESTRATEGICOS", "Combustiveis"),
    (r"LUBRIF", "ESTRATEGICOS", "Lubrificantes"),
    (r"LOJA|FOOD|CONVEN", "ESTRATEGICOS", "Conveniencia Core"),
]

SUPPLIER_KEYWORDS: list[tuple[str, str, str]] = [
    (r"VIBRA|IPIRANGA|PETROBRAS|BR DISTRIB|RAIZEN|SHELL", "ESTRATEGICOS", "Combustiveis"),
    (r"AMBEV|HEINEKEN|COCA|PEPSI|BEBID", "ESTRATEGICOS", "Conveniencia Core"),
    (r"ALELO|SODEXO|TICKET|VR BENEF", "RH", "Beneficios"),
    (r"BANCO|ITAU|BRADESCO|CAIXA|SANTANDER", "FINANCEIRO", "Bancos"),
    (r"O\.?E\.?C|CONTABIL", "FINANCEIRO", "Tarifas"),
]

DESC_KEYWORDS: list[tuple[str, str, str]] = [
    (r"COMBUST|DIESEL|GASOLINA", "ESTRATEGICOS", "Combustiveis"),
    (r"NF:|NOTA FISCAL", "ESTRATEGICOS", "Distribuicao"),
]


def _norm(text: str) -> str:
    return normalize_supplier_key(text)


def is_strategic_homologated(canonical: str) -> bool:
    return canonical in STRATEGIC_HOMOLOGATED


def classify_supplier_segment(
    *,
    plano_conta: str = "",
    plano_categoria_v3: str = "",
    centro_custo: str = "",
    supplier_name: str = "",
    descricao: str = "",
) -> dict[str, Any]:
    """Prioridade: Plano Conta → Centro Custo → Fornecedor → Descrição."""
    evidence: list[str] = []
    blob_plano = _norm(f"{plano_conta} {plano_categoria_v3}")

    if plano_categoria_v3 and plano_categoria_v3 in V3_TO_SUPPLIER_CATEGORY:
        cat, sub = V3_TO_SUPPLIER_CATEGORY[plano_categoria_v3]
        evidence.append(f"PLANO_CONTA_V3:{plano_categoria_v3}")
        return _segment_result(cat, sub, evidence, "PLANO_CONTA")

    for pat, cat, sub in PLANO_KEYWORDS:
        if re.search(pat, blob_plano, re.I):
            evidence.append(f"PLANO_CONTA:{pat}")
            return _segment_result(cat, sub, evidence, "PLANO_CONTA")

    blob_centro = _norm(centro_custo)
    for pat, cat, sub in CENTRO_KEYWORDS:
        if re.search(pat, blob_centro, re.I):
            evidence.append(f"CENTRO_CUSTO:{centro_custo}")
            return _segment_result(cat, sub, evidence, "CENTRO_CUSTO")

    canonical = canonical_supplier_name(supplier_name)
    if is_strategic_homologated(canonical):
        evidence.append(f"FORNECEDOR_HOMOLOGADO:{canonical}")
        return _segment_result("ESTRATEGICOS", "Combustiveis", evidence, "FORNECEDOR", strategic=True)

    blob_sup = _norm(supplier_name)
    for pat, cat, sub in SUPPLIER_KEYWORDS:
        if re.search(pat, blob_sup, re.I):
            evidence.append(f"FORNECEDOR:{supplier_name[:60]}")
            strategic = cat == "ESTRATEGICOS"
            return _segment_result(cat, sub, evidence, "FORNECEDOR", strategic=strategic)

    blob_desc = _norm(descricao)
    for pat, cat, sub in DESC_KEYWORDS:
        if re.search(pat, blob_desc, re.I):
            evidence.append(f"DESCRICAO:{descricao[:60]}")
            return _segment_result(cat, sub, evidence, "DESCRICAO")

    return _segment_result("OUTROS", "Sem evidencia", evidence or ["OUTROS"], "OUTROS")


def _segment_result(
    category: str,
    subcategory: str,
    evidence: list[str],
    source: str,
    strategic: bool = False,
) -> dict[str, Any]:
    return {
        "supplierCategory": category,
        "supplierSubcategory": subcategory,
        "supplierStrategic": strategic or category == "ESTRATEGICOS",
        "classificationSource": source,
        "classificationEvidence": evidence,
    }


def strategic_supplier_score(
    *,
    valor: Decimal,
    total: Decimal,
    filiais_count: int,
    n_filiais: int,
    transaction_count: int,
    supplier_strategic: bool,
) -> dict[str, Any]:
    vol = min(25, float(valor / total * 25)) if total else 0
    cap = min(25, filiais_count / max(n_filiais, 1) * 25)
    rec = min(25, transaction_count / 10 * 25)
    crit = 25 if supplier_strategic else min(25, vol)
    score = round(vol + cap + rec + crit)
    score = min(100, max(0, score))
    if score >= 75:
        band = "CRITICAL"
    elif score >= 50:
        band = "HIGH"
    elif score >= 25:
        band = "MEDIUM"
    else:
        band = "LOW"
    return {
        "strategicSupplierScore": score,
        "strategicBand": band,
        "components": {
            "volumeFinanceiro": round(vol, 1),
            "capilaridadeRede": round(cap, 1),
            "recorrenciaHistorica": round(rec, 1),
            "criticidadeOperacional": round(crit, 1),
        },
    }


def supplier_confidence_score(
    *,
    fornecedor_identificado: bool,
    plano_conta: bool,
    centro_custo: bool,
    movimento_financeiro: bool,
) -> dict[str, Any]:
    score = 0
    if fornecedor_identificado:
        score += 40
    if plano_conta:
        score += 30
    if centro_custo:
        score += 20
    if movimento_financeiro:
        score += 10
    if score >= 90:
        band = "ALTA"
    elif score >= 70:
        band = "MEDIA"
    else:
        band = "BAIXA"
    return {"supplierConfidenceScore": score, "confidenceBand": band}


def concentration_risk_level(share_pct: float, canonical: str) -> str | None:
    """Retorna None se homologado estratégico (sem falso positivo)."""
    if is_strategic_homologated(canonical):
        return None
    if share_pct > 35:
        return "CRITICAL"
    if share_pct > 20:
        return "HIGH"
    if share_pct > 10:
        return "MEDIUM"
    return "LOW" if share_pct > 5 else None


def detect_procurement_opportunities(
    by_canonical: dict[str, dict[str, Any]],
    total: Decimal,
) -> list[dict[str, Any]]:
    """Oportunidades com evidência — fornecedores equivalentes por subcategoria."""
    by_sub: dict[tuple[str, str], list[str]] = {}
    for name, agg in by_canonical.items():
        seg = agg.get("segment") or {}
        key = (seg.get("supplierCategory", "OUTROS"), seg.get("supplierSubcategory", "Sem evidencia"))
        by_sub.setdefault(key, []).append(name)

    opportunities: list[dict[str, Any]] = []
    for (cat, sub), suppliers in by_sub.items():
        if len(suppliers) < 2 or cat == "OUTROS" or sub in ("Combustiveis",):
            continue
        vals = [(s, by_canonical[s]["valor"]) for s in suppliers]
        vals.sort(key=lambda x: -x[1])
        top_val = vals[0][1]
        for name, val in vals[1:]:
            if top_val and val < top_val * Decimal("0.85"):
                diff = top_val - val
                opportunities.append(
                    {
                        "tipo": "NEGOCIACAO_GRUPO",
                        "categoria": cat,
                        "subcategoria": sub,
                        "fornecedorReferencia": vals[0][0],
                        "fornecedorOportunidade": name,
                        "economiaPotencialPeriodo": str(diff.quantize(Decimal("0.01"))),
                        "evidence": f"Subcategoria {sub}: {len(suppliers)} fornecedores",
                    }
                )

    dup_groups: dict[str, list[str]] = {}
    for name, agg in by_canonical.items():
        sub = (agg.get("segment") or {}).get("supplierSubcategory", "")
        if sub:
            dup_groups.setdefault(sub, []).append(name)

    for sub, names in dup_groups.items():
        if len(names) >= 2 and sub not in ("Combustiveis", "Conveniencia Core"):
            opportunities.append(
                {
                    "tipo": "CONTRATOS_DESCENTRALIZADOS",
                    "subcategoria": sub,
                    "fornecedores": names[:5],
                    "quantidade": len(names),
                    "evidence": f"{len(names)} fornecedores em {sub}",
                }
            )

    opportunities.sort(key=lambda x: float(x.get("economiaPotencialPeriodo", 0) or 0), reverse=True)
    return opportunities[:50]


def procurement_readiness_score(sources: set[str], has_catalog: bool) -> int:
    score = 0
    if "TITULO_PAGAR" in sources:
        score += 40
    if "DESPESAS_REDE_DESC" in sources or "DESPESAS_REDE" in sources:
        score += 25
    if "MOVIMENTO_CONTA" in sources:
        score += 15
    if has_catalog:
        score += 20
    return min(100, score)
