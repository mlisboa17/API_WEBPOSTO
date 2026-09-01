"""Identidade de abastecimento para consolidação do SDS.

`codigo` no payload de ABASTECIMENTO é o mesmo identificador operacional
que `abastecimentoCodigo`. Nunca usar vendaItemCodigo nem fallback sintético.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

LICENSED_SDS_CODES = (5555, 11495, 74014)

STATUS_SUCESSO = "SUCESSO"
STATUS_SEM_MOVIMENTO = "SEM_MOVIMENTO_CONFIRMADO"
STATUS_PARCIAL = "PARCIAL"
STATUS_FALHA = "FALHA"
STATUS_PENDENTE = "PENDENTE"
COMPLETE_STATUSES = frozenset({STATUS_SUCESSO, STATUS_SEM_MOVIMENTO})

IDENTITY_KEYS = ("abastecimentoCodigo", "codigo")
FORBIDDEN_IDENTITY_KEYS = ("vendaItemCodigo", "stringFull")


def abastecimento_identity(row: dict[str, Any]) -> str | None:
    """Retorna o ID operacional ou None. Ignora vendaItemCodigo."""
    for key in IDENTITY_KEYS:
        val = row.get(key)
        if val is None:
            continue
        text = str(val).strip()
        if not text or text.startswith("sds-"):
            continue
        return text
    return None


def _as_float(val: Any) -> float:
    try:
        if val is None or val == "":
            return 0.0
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def product_code(row: dict[str, Any]) -> str:
    for key in ("codigoProduto", "produtoCodigo", "produtoLmcCodigo", "produto_codigo"):
        val = row.get(key)
        if val is None:
            continue
        code = str(val).strip()
        if code and code not in ("0",) and code.isdigit() and len(code) <= 8:
            return code
        if code and not code.isdigit() and 1 <= len(code) <= 16:
            return code
    return ""


def product_name(row: dict[str, Any], codigo: str = "") -> str:
    for key in (
        "produtoDescricao",
        "produtoNome",
        "nomeProduto",
        "produto",
        "descricao",
        "produto_nome",
    ):
        val = row.get(key)
        if val is not None and str(val).strip():
            name = str(val).strip()
            if codigo and name == f"Produto {codigo}":
                continue
            return name
    return ""


def ratio_or_none(num: float | None, den: float | None) -> float | None:
    if num is None or den is None or den <= 0:
        return None
    return round(float(num) / float(den), 4)


def summarize_abastecimentos(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Agrega combustível válido. Contagem só com identidade oficial."""
    by_product: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"nome": "", "litros": 0.0, "faturamento": 0.0, "ids": set(), "ultima": None}
    )
    sem_identidade = 0
    lidos = 0
    vistos: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        codigo = product_code(row)
        if not codigo:
            continue
        identity = abastecimento_identity(row)
        if identity and identity in vistos:
            continue
        lidos += 1
        litros = _as_float(row.get("quantidade") or row.get("quantidadeLitros") or row.get("litros"))
        valor = _as_float(row.get("valorTotal") or row.get("valorVenda") or row.get("valor"))
        nome = product_name(row, codigo)
        bucket = by_product[codigo]
        if nome and (not bucket["nome"] or bucket["nome"].startswith("Produto ")):
            bucket["nome"] = nome
        elif not bucket["nome"]:
            bucket["nome"] = f"Produto {codigo}"
        bucket["litros"] += litros
        bucket["faturamento"] += valor
        if identity:
            vistos.add(identity)
            bucket["ids"].add(identity)
        else:
            sem_identidade += 1
        ts = row.get("dataHoraAbastecimento") or row.get("dataFiscal")
        if ts:
            bucket["ultima"] = str(ts)

    qtd = sum(len(item["ids"]) for item in by_product.values())
    litros = sum(float(item["litros"]) for item in by_product.values())
    fat = sum(float(item["faturamento"]) for item in by_product.values())
    confiavel = sem_identidade == 0 and qtd > 0
    if not by_product:
        status = STATUS_SEM_MOVIMENTO
    elif sem_identidade:
        status = STATUS_PARCIAL
    else:
        status = STATUS_SUCESSO
    return {
        "by_product": dict(by_product),
        "linhasCombustivel": lidos,
        "registrosSemIdentidade": sem_identidade,
        "quantidadeAbastecimentos": qtd if qtd else None,
        "litrosVendidos": round(litros, 3) if by_product else None,
        "faturamentoCombustivel": round(fat, 2) if by_product else None,
        "contagemConfiavel": confiavel,
        "ticketMedioLitros": ratio_or_none(litros, qtd) if confiavel else None,
        "ticketMedioReais": ratio_or_none(fat, qtd) if confiavel else None,
        "status": status,
        "avisos": _avisos(sem_identidade, confiavel, bool(by_product)),
    }


def _avisos(sem_identidade: int, confiavel: bool, tem_combustivel: bool) -> list[str]:
    avisos: list[str] = []
    if sem_identidade:
        avisos.append(
            f"{sem_identidade} registro(s) de combustível sem abastecimentoCodigo/"
            "codigo. Excluídos da contagem. Ticket médio indisponível."
        )
    if tem_combustivel and not confiavel:
        avisos.append("Contagem de abastecimentos não confiável para ticket médio.")
    return avisos
