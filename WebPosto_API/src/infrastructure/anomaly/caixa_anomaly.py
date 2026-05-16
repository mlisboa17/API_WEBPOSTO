"""
Detecção de anomalias em movimentos de caixa (retiradas atípicas).
"""

from __future__ import annotations

from decimal import Decimal
from statistics import mean, stdev
from typing import Any


def _valor(row: dict[str, Any]) -> Decimal:
    for k in (
        "valor",
        "valorMovimento",
        "valorTotal",
        "valorSaida",
        "valorRetirada",
    ):
        if row.get(k) is not None:
            try:
                return Decimal(str(row[k]))
            except Exception:
                pass
    return Decimal("0")


def detectar_anomalias_caixa(
    registros: list[dict[str, Any]],
    z_threshold: float = 2.5,
) -> list[dict[str, Any]]:
    """
    Varre turnos/caixa e aponta retiradas com valor > média + z*desvio.
    """
    saidas: list[tuple[dict[str, Any], Decimal]] = []
    for row in registros:
        tipo = str(
            row.get("tipoMovimento")
            or row.get("tipo")
            or row.get("operacao")
            or ""
        ).lower()
        v = _valor(row)
        if v <= 0:
            continue
        if any(x in tipo for x in ("saida", "saída", "retirada", "suprimento-", "debito")):
            saidas.append((row, v))
        elif not tipo and v > Decimal("500"):
            saidas.append((row, v))

    if len(saidas) < 3:
        return []

    valores = [float(v) for _, v in saidas]
    media = mean(valores)
    try:
        desvio = stdev(valores) or 1.0
    except Exception:
        desvio = 1.0
    limite = media + z_threshold * desvio

    flags: list[dict[str, Any]] = []
    for row, v in saidas:
        if float(v) > limite:
            flags.append(
                {
                    "severidade": "alta" if float(v) > limite * 1.5 else "media",
                    "valor": str(v),
                    "media_periodo": round(media, 2),
                    "limite": round(limite, 2),
                    "caixa_codigo": row.get("caixaCodigo") or row.get("codigo"),
                    "data": row.get("data") or row.get("dataMovimento"),
                    "motivo": "Retirada acima do padrão estatístico do período",
                }
            )
    return flags
