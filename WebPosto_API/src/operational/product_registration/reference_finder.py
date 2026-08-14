"""Localização de produtos modelo para tributação — somente leitura."""

from __future__ import annotations

import re
import unicodedata
from typing import Any


def _norm(text: Any) -> str:
    raw = str(text or "").strip().upper()
    nfkd = unicodedata.normalize("NFKD", raw)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _tokens(text: Any) -> set[str]:
    n = _norm(text)
    return {t for t in re.split(r"[^A-Z0-9]+", n) if len(t) >= 3}


def _as_int(v: Any) -> int | None:
    try:
        i = int(v)
        return i if i > 0 else None
    except (TypeError, ValueError):
        return None


def score_reference_product(
    candidate: dict[str, Any],
    *,
    empresa_codigo: int,
    ncm: str | None,
    cest: str | None,
    grupo_codigo: int | None,
    descricao: str | None,
    unidade_venda: str | None,
) -> tuple[int, list[str], bool]:
    """Retorna (score, reasons, disqualified)."""
    reasons: list[str] = []
    score = 0
    if bool(candidate.get("combustivel")):
        return -999, ["DISQUALIFY_COMBUSTIVEL"], True
    tipo = str(candidate.get("tipoProduto") or candidate.get("tipo") or "P").upper()
    if tipo and tipo != "P":
        return -999, [f"DISQUALIFY_TIPO_{tipo}"], True

    cand_emp = _as_int(candidate.get("empresaCodigo")) or empresa_codigo
    if cand_emp != int(empresa_codigo):
        score -= 40
        reasons.append("empresa_diferente:-40")
    else:
        score += 5
        reasons.append("mesma_empresa:+5")

    cand_ncm = str(candidate.get("ncm") or candidate.get("codigoNcm") or "").zfill(8)[-8:]
    if ncm and cand_ncm == str(ncm).zfill(8)[-8:]:
        score += 40
        reasons.append("mesmo_ncm:+40")

    cand_cest = str(candidate.get("cest") or candidate.get("codigoCest") or "").zfill(7)[-7:]
    if cest and cand_cest and cand_cest == str(cest).zfill(7)[-7:]:
        score += 25
        reasons.append("mesmo_cest:+25")

    cand_grupo = _as_int(candidate.get("grupoCodigo") or candidate.get("grupo"))
    if grupo_codigo and cand_grupo == int(grupo_codigo):
        score += 15
        reasons.append("mesmo_grupo:+15")

    a, b = _tokens(descricao), _tokens(candidate.get("nome") or candidate.get("descricao"))
    if a and b and (a & b):
        score += 10
        reasons.append("categoria_descritiva:+10")

    uv = _norm(unidade_venda)
    cuv = _norm(candidate.get("unidadeVenda") or candidate.get("unidade_venda"))
    if uv and cuv and uv == cuv:
        score += 5
        reasons.append("mesma_unidade:+5")

    if _tax_complete(candidate):
        score += 5
        reasons.append("tributacao_completa:+5")

    ativo = candidate.get("ativo")
    if ativo is False:
        score -= 15
        reasons.append("inativo:-15")

    return score, reasons, False


def _tax_complete(p: dict[str, Any]) -> bool:
    ncm = str(p.get("ncm") or p.get("codigoNcm") or "")
    if len(re.sub(r"\D", "", ncm)) != 8:
        return False
    icms = p.get("tributoIcms") or p.get("icms") or {}
    pis = p.get("tributoPisCofins") or p.get("pisCofins") or {}
    if not isinstance(icms, dict) or not isinstance(pis, dict):
        return False
    if not (icms.get("cstSaida") or icms.get("cst_saida")):
        return False
    if not (pis.get("cstPisSaida") or pis.get("cst_pis_saida")):
        return False
    return True


def find_tax_reference_products(
    catalog: list[dict[str, Any]],
    *,
    empresa_codigo: int,
    ncm: str | None,
    cest: str | None = None,
    grupo_codigo: int | None = None,
    descricao: str | None = None,
    unidade_venda: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Retorna 3–10 candidatos (quando existirem), ordenados por score.
    Não escolhe automaticamente só por descrição.
    """
    scored: list[dict[str, Any]] = []
    ncm_norm = re.sub(r"\D", "", str(ncm or "")).zfill(8)[-8:] if ncm else None
    cest_norm = re.sub(r"\D", "", str(cest or "")).zfill(7)[-7:] if cest else None

    for raw in catalog or []:
        p = dict(raw)
        p.setdefault("empresaCodigo", empresa_codigo)
        score, reasons, bad = score_reference_product(
            p,
            empresa_codigo=empresa_codigo,
            ncm=ncm_norm,
            cest=cest_norm,
            grupo_codigo=grupo_codigo,
            descricao=descricao,
            unidade_venda=unidade_venda,
        )
        if bad or score < 40:
            # exige pelo menos mesmo NCM (40) na mesma empresa (+5) — mínimo útil
            if bad:
                continue
            if not (ncm_norm and str(p.get("ncm") or p.get("codigoNcm") or "").zfill(8)[-8:] == ncm_norm):
                continue
        scored.append(
            {
                **_public_candidate(p),
                "score": score,
                "scoreBreakdown": reasons,
            }
        )

    scored.sort(key=lambda x: (-int(x["score"]), str(x.get("descricao") or "")))
    # preferir ativos e mesma empresa
    out = scored[: max(3, min(limit, 10))] if scored else []
    if len(scored) >= 3:
        out = scored[: min(limit, 10)]
    elif scored:
        out = scored[: min(limit, 10)]
    return out


def _public_candidate(p: dict[str, Any]) -> dict[str, Any]:
    eans = list(p.get("eans") or [])
    for b in p.get("produtoCodigoBarra") or []:
        if isinstance(b, dict):
            code = b.get("codigoBarra") or b.get("codigo")
            if code:
                eans.append(str(code))
    return {
        "produtoCodigo": p.get("produtoCodigo") or p.get("codigo"),
        "referencia": p.get("referenciaCodigo") or p.get("referencia"),
        "descricao": p.get("nome") or p.get("descricao"),
        "eans": sorted({str(e) for e in eans if e}),
        "grupoCodigo": p.get("grupoCodigo") or p.get("grupo"),
        "ncm": p.get("ncm") or p.get("codigoNcm"),
        "cest": p.get("cest") or p.get("codigoCest"),
        "unidadeCompra": p.get("unidadeCompra"),
        "unidadeVenda": p.get("unidadeVenda"),
        "iat": p.get("iat"),
        "ippt": p.get("ippt"),
        "naturezaReceitaCodigo": p.get("naturezaReceitaCodigo"),
        "tributoIcms": p.get("tributoIcms") or p.get("icms"),
        "tributoPisCofins": p.get("tributoPisCofins") or p.get("pisCofins"),
        "cdCfopEntrada": p.get("cdCfopEntrada") or p.get("cfopEntrada"),
        "cdCfopSaida": p.get("cdCfopSaida") or p.get("cfopSaida"),
        "tributacaoMonofasica": p.get("tributacaoMonofasica"),
        "tributoCbsIbs": p.get("tributoCbsIbs") or p.get("cbsIbs"),
        "centroCustoCodigo": p.get("centroCustoCodigo"),
        "ativo": p.get("ativo"),
        "ultimaAlteracao": p.get("ultimaAlteracao") or p.get("dataAlteracao"),
        "empresaCodigo": p.get("empresaCodigo"),
        "combustivel": bool(p.get("combustivel")),
        "tipoProduto": p.get("tipoProduto") or "P",
    }
