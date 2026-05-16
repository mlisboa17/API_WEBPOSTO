"""
Perfis fiscais Adelaide — monofásico, CST e risco de bitributação.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Códigos operacionais do cockpit + códigos WebPosto reais (Posto VIP)
FISCAL_BY_CODE: Dict[str, Dict[str, Any]] = {
    "001": {
        "nome": "Gasolina Comum",
        "monofasico": True,
        "cst": "060",
        "webposto_codigos": ["1257884"],
    },
    "002": {
        "nome": "Gasolina Aditivada",
        "monofasico": True,
        "cst": "060",
        "webposto_codigos": ["1260803"],
    },
    "003": {
        "nome": "Etanol Hidratado",
        "monofasico": False,
        "cst": "000",
        "webposto_codigos": ["1975728"],
    },
    "004": {
        "nome": "Diesel S10",
        "monofasico": True,
        "cst": "060",
        "webposto_codigos": ["1257999"],
        "risco": "Verificar CST na NF — divergência comum gera bitributação",
    },
    "1257884": {"nome": "Gasolina comum", "monofasico": True, "cst": "060"},
    "1260803": {"nome": "Gasolina aditivada", "monofasico": True, "cst": "060"},
    "1975728": {"nome": "Etanol", "monofasico": False, "cst": "000"},
    "1257999": {"nome": "Diesel S10", "monofasico": True, "cst": "060"},
    "1258001": {"nome": "Diesel comum", "monofasico": True, "cst": "060"},
}


def list_fiscal_audit_rows() -> List[Dict[str, Any]]:
    """Linhas para tabela de auditoria no dashboard executivo."""
    seen = set()
    rows: List[Dict[str, Any]] = []
    for codigo, perfil in FISCAL_BY_CODE.items():
        if len(codigo) > 4:
            continue
        if codigo in seen:
            continue
        seen.add(codigo)
        mono = perfil.get("monofasico", False)
        cst = perfil.get("cst", "000")
        regime = "Monofásico" if mono else "Tributado integral"
        status = "✓ Correto"
        if perfil.get("risco"):
            regime = "Tributado integral (divergente)"
            status = "⚠ Risco de bitributação"
        rows.append(
            {
                "codigo": codigo,
                "produto": perfil["nome"],
                "regime_efetivo": regime,
                "cst_sefaz": cst,
                "status_fiscal": status,
            }
        )
    return rows
