from __future__ import annotations

from typing import Any


def _to_number(value: Any) -> float:
    try:
        return float(str(value or 0).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def aggregate_fuel_executive_payload(payload: dict[str, Any], company_codes: list[int]) -> dict[str, Any]:
    """Agrega payload fuel executive para multiselect (espelha rebuildFuelExecutivePayload do frontend)."""
    if not payload or not company_codes:
        return payload

    allowed = set(company_codes)
    filiais = [item for item in (payload.get("filiais") or []) if _to_number(item.get("empresaCodigo")) in allowed]
    detalhes = [item for item in (payload.get("detalhes") or []) if _to_number(item.get("empresaCodigo")) in allowed]
    litros_total = sum(_to_number(item.get("litros")) for item in filiais)

    combustivel_map: dict[str, dict[str, Any]] = {}
    for item in detalhes:
        key = str(item.get("produtoCodigo") or item.get("combustivel") or "")
        current = combustivel_map.get(key) or {
            "produtoCodigo": item.get("produtoCodigo"),
            "combustivel": item.get("combustivel"),
            "litros": 0.0,
        }
        current["litros"] = _to_number(current.get("litros")) + _to_number(item.get("litros"))
        combustivel_map[key] = current

    combustiveis = sorted(
        [
            {
                **item,
                "participacao": round((item["litros"] / litros_total) * 100, 2) if litros_total > 0 else 0.0,
            }
            for item in combustivel_map.values()
        ],
        key=lambda row: _to_number(row.get("litros")),
        reverse=True,
    )

    ranking = sorted(filiais, key=lambda row: _to_number(row.get("litros")), reverse=True)[:10]
    ranking = [{**item, "posicao": index + 1} for index, item in enumerate(ranking)]

    diesel = sum(
        _to_number(item.get("litros"))
        for item in combustiveis
        if "diesel" in str(item.get("combustivel") or "").lower()
    )
    gasolina = sum(
        _to_number(item.get("litros"))
        for item in combustiveis
        if "gasolina" in str(item.get("combustivel") or "").lower()
    )
    etanol = sum(
        _to_number(item.get("litros"))
        for item in combustiveis
        if any(token in str(item.get("combustivel") or "").lower() for token in ("etanol", "alcool"))
    )

    combustivel_lider = combustiveis[0] if combustiveis else {"combustivel": "Sem dados", "litros": 0}
    filial_lider = ranking[0] if ranking else {"nomeFilial": "Sem dados", "litros": 0}

    return {
        **payload,
        "litrosTotal": litros_total,
        "filiais": filiais,
        "combustiveis": combustiveis,
        "ranking": ranking,
        "detalhes": detalhes,
        "consistencia": {
            "somaCombustiveis": round(sum(_to_number(item.get("litros")) for item in combustiveis), 3),
            "somaFiliais": round(sum(_to_number(item.get("litros")) for item in filiais), 3),
        },
        "kpis": {
            "litrosVendidos": litros_total,
            "combustivelLider": {
                "produtoCodigo": combustivel_lider.get("produtoCodigo"),
                "nome": combustivel_lider.get("combustivel"),
                "litros": combustivel_lider.get("litros"),
            },
            "filialLider": {
                "empresaCodigo": filial_lider.get("empresaCodigo"),
                "nomeFilial": filial_lider.get("nomeFilial"),
                "litros": filial_lider.get("litros"),
            },
            "participacaoDiesel": round((diesel / litros_total) * 100, 2) if litros_total > 0 else 0.0,
            "participacaoGasolina": round((gasolina / litros_total) * 100, 2) if litros_total > 0 else 0.0,
            "participacaoEtanol": round((etanol / litros_total) * 100, 2) if litros_total > 0 else 0.0,
        },
        "lineage": {"aggregate": "multiselect_backend"},
    }
