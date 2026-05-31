"""Mapeamento JSON WebPosto → entidades de auditoria (somente campos reais da API)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, List, Optional

from src.domain.entities.audit import (
    AuditDespesa,
    AuditRawData,
    AuditTurno,
    AuditVendaLinha,
    SubCentroCusto,
    calcular_faturamento_periodo,
)
from src.domain.adelaide.abastecimento_filters import (
    aplicar_filtros_abastecimento,
    normalizar_registro_valor,
    valor_financeiro_abastecimento,
    codigo_produto,
)

_FOOD_KEYS = ("food", "lanch", "restaur", "refeic", "refeiç", "padaria", "snack", "lanche")
_LOJA_KEYS = ("loja", "conven", "pdv", "varejo", "mercear", "bebida", "revenda", "conveniencia")
_PISTA_KEYS = ("pista", "combust", "bico", "abastec", "posto", "bomba")

_CENTRO_FIELDS = (
    "centroCusto",
    "centroCustoDescricao",
    "centroCustoNome",
    "descricaoCentroCusto",
    "codigoCentroCusto",
    "subCentro",
    "subCentroCusto",
    "subCentroDescricao",
)


def _rows(payload: Any) -> List[dict]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        inner = payload.get("resultados") or payload.get("data") or []
        return [r for r in inner if isinstance(r, dict)] if isinstance(inner, list) else []
    return []


def _dec(val: Any) -> Decimal:
    try:
        return Decimal(str(val or 0)).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0")


def _parse_date(raw: Any) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except Exception:
        return None


def _row_blob(row: dict) -> str:
    parts: list[str] = []
    for k in _CENTRO_FIELDS:
        v = row.get(k)
        if v is not None and str(v).strip():
            parts.append(str(v))
    for k in (
        "historico",
        "descricao",
        "planoConta",
        "conta",
        "nomeGrupo",
        "grupo",
        "categoria",
        "nomeProduto",
        "observacao",
    ):
        v = row.get(k)
        if v is not None and str(v).strip():
            parts.append(str(v))
    return " ".join(parts).lower()


def resolve_sub_centro_from_text(blob: str) -> Optional[SubCentroCusto]:
    """Classifica por texto do ERP; None = não classificado (não inventar LOJA/FOOD)."""
    b = (blob or "").lower()
    if not b.strip():
        return None
    if any(k in b for k in _FOOD_KEYS):
        return SubCentroCusto.FOOD
    if any(k in b for k in _LOJA_KEYS):
        return SubCentroCusto.LOJA
    if any(k in b for k in _PISTA_KEYS):
        return SubCentroCusto.PISTA
    return None


def row_belongs_sub_centro(row: dict, sub_centro: SubCentroCusto) -> bool:
    resolved = resolve_sub_centro_from_text(_row_blob(row))
    if resolved is not None:
        return resolved == sub_centro
    return False


def _grupo_rotulo_item(item: dict) -> str:
    keys = (
        "nomeGrupoProduto",
        "grupoProdutoNome",
        "grupoProdutoDescricao",
        "descricaoGrupoProduto",
        "grupoNome",
        "nomeGrupo",
        "descricaoGrupo",
        "grupoDescricao",
        "categoriaProduto",
        "categoriaNome",
        "departamento",
        "secao",
        "grupo",
    )
    for k in keys:
        if item.get(k) is not None and str(item[k]).strip():
            return str(item[k]).strip()
    cod = item.get("grupoProdutoCodigo") or item.get("codigoGrupo") or item.get("grupoCodigo")
    if cod is not None and str(cod).strip():
        return f"Grupo cód. {cod}"
    return ""


def _valor_linha_item(item: dict) -> Decimal:
    for k in ("valorTotal", "valorTotalItem", "totalItem", "valorLiquido", "valor"):
        v = item.get(k)
        if v is not None:
            d = _dec(v)
            if d > 0:
                return d
    try:
        q = Decimal(str(item.get("quantidade") or 0))
        vu = Decimal(str(item.get("valorUnitario") or item.get("precoUnitario") or 0))
        if q > 0 and vu > 0:
            return (q * vu).quantize(Decimal("0.01"))
    except Exception:
        pass
    return Decimal("0")


def _item_blob(item: dict, venda: dict) -> str:
    parts = [_grupo_rotulo_item(item)]
    for k in _CENTRO_FIELDS:
        v = item.get(k) or venda.get(k)
        if v is not None and str(v).strip():
            parts.append(str(v))
    return " ".join(parts).lower()


def map_caixa_turnos(rows: List[dict], sub_centro: SubCentroCusto) -> List[AuditTurno]:
    out: List[AuditTurno] = []
    for i, row in enumerate(rows):
        if not row_belongs_sub_centro(row, sub_centro):
            continue
        apurado = _dec(
            row.get("valorApurado")
            or row.get("valor_apurado")
            or row.get("valorTotal")
            or row.get("valor")
        )
        apresentado = _dec(
            row.get("valorApresentado")
            or row.get("valor_apresentado")
            or row.get("valorSistema")
        )
        out.append(
            AuditTurno(
                turno_id=str(row.get("caixaCodigo") or row.get("codigo") or i),
                data=_parse_date(row.get("data") or row.get("dataMovimento")),
                valor_caixa=apurado,
                valor_sistema=apresentado,
                sub_centro=sub_centro,
            )
        )
    return out


def map_caixa_apresentado(rows: List[dict], sub_centro: SubCentroCusto) -> tuple[Decimal, Decimal]:
    apurado = Decimal("0")
    apresentado = Decimal("0")
    for row in rows:
        if not row_belongs_sub_centro(row, sub_centro):
            continue
        apurado += _dec(row.get("valorApurado") or row.get("apurado") or row.get("valorApuradoTotal"))
        apresentado += _dec(
            row.get("valorApresentado") or row.get("apresentado") or row.get("valorApresentadoTotal")
        )
        for forma in row.get("formasPagamento") or row.get("formas") or []:
            if isinstance(forma, dict):
                if not row_belongs_sub_centro(forma, sub_centro) and _row_blob(forma):
                    continue
                apurado += _dec(forma.get("valorApurado") or forma.get("apurado"))
                apresentado += _dec(forma.get("valorApresentado") or forma.get("apresentado"))
    return apurado.quantize(Decimal("0.01")), apresentado.quantize(Decimal("0.01"))


def map_abastecimento_vendas(
    rows: List[dict],
    sub_centro: SubCentroCusto,
) -> List[AuditVendaLinha]:
    if sub_centro != SubCentroCusto.PISTA:
        return []
    filtrados = aplicar_filtros_abastecimento(
        [normalizar_registro_valor(r) for r in rows],
        excluir_afericao=True,
        apenas_combustivel=True,
    )
    out: List[AuditVendaLinha] = []
    for row in filtrados:
        litros = Decimal(str(row.get("quantidade") or 0)).quantize(Decimal("0.0001"))
        fat = valor_financeiro_abastecimento(row)
        if fat <= 0 and litros <= 0:
            continue
        out.append(
            AuditVendaLinha(
                produto_codigo=codigo_produto(row),
                categoria=str(row.get("nomeProduto") or row.get("descricaoProduto") or ""),
                litros=litros,
                faturamento=fat,
            )
        )
    return out


def map_vendas_pdv(rows: List[dict], sub_centro: SubCentroCusto) -> List[AuditVendaLinha]:
    """LOJA e FOOD: soma itens classificados; ignora cupom inteiro sem classificação por item."""
    if sub_centro == SubCentroCusto.PISTA:
        return []
    out: List[AuditVendaLinha] = []
    for venda in rows:
        itens = venda.get("itens") or venda.get("itensVenda") or []
        if not isinstance(itens, list) or not itens:
            continue
        for item in itens:
            if not isinstance(item, dict):
                continue
            blob = _item_blob(item, venda)
            resolved = resolve_sub_centro_from_text(blob)
            if resolved != sub_centro:
                continue
            fat = _valor_linha_item(item)
            if fat <= 0:
                continue
            out.append(
                AuditVendaLinha(
                    produto_codigo=str(item.get("produtoCodigo") or item.get("codigo") or ""),
                    categoria=_grupo_rotulo_item(item) or str(item.get("categoria") or ""),
                    litros=Decimal("0"),
                    faturamento=fat,
                )
            )
    return out


def map_despesas(rows: List[dict], sub_centro: SubCentroCusto) -> List[AuditDespesa]:
    out: List[AuditDespesa] = []
    for row in rows:
        if not row_belongs_sub_centro(row, sub_centro):
            continue
        plano = str(row.get("planoConta") or row.get("conta") or row.get("historico") or "")
        desc = str(row.get("descricao") or row.get("nomeFornecedor") or "")
        val = _dec(row.get("valor") or row.get("valorTotal") or row.get("valorTitulo"))
        if val <= 0:
            continue
        out.append(
            AuditDespesa(
                descricao=desc or plano,
                plano_conta=plano,
                valor=val,
                sub_centro=sub_centro,
            )
        )
    return out


def build_audit_raw(
    *,
    posto_id: str,
    sub_centro: SubCentroCusto,
    data_inicio: date,
    data_fim: date,
    caixa_rows: Any,
    apresentado_rows: Any,
    abastecimento_rows: Any,
    venda_rows: Any,
    titulo_pagar_rows: Any,
    erros_api: list[str] | None = None,
) -> AuditRawData:
    caixa = _rows(caixa_rows)
    apres = _rows(apresentado_rows)
    turnos = map_caixa_turnos(caixa, sub_centro)
    ap_total, apres_total = map_caixa_apresentado(apres, sub_centro)
    if not ap_total and turnos:
        ap_total = sum(t.valor_caixa for t in turnos)
    if not apres_total and turnos:
        apres_total = sum(t.valor_sistema for t in turnos)

    vendas: List[AuditVendaLinha] = []
    if sub_centro == SubCentroCusto.PISTA:
        vendas = map_abastecimento_vendas(_rows(abastecimento_rows), sub_centro)
    else:
        vendas = map_vendas_pdv(_rows(venda_rows), sub_centro)

    despesas = map_despesas(_rows(titulo_pagar_rows), sub_centro)
    faturamento = calcular_faturamento_periodo(sub_centro, vendas)

    if sub_centro != SubCentroCusto.PISTA and _rows(venda_rows) and not vendas:
        from src.domain.exceptions.audit_fetch import AuditFetchError

        raise AuditFetchError(
            f"Nenhum item de venda PDV foi classificado como {sub_centro.value} "
            "(grupo/centro de custo na WebPosto). Não usamos estimativa nem cupom inteiro sem classificação.",
            erros=erros_api or [],
        )

    return AuditRawData(
        posto_id=posto_id,
        sub_centro=sub_centro,
        data_inicio=data_inicio,
        data_fim=data_fim,
        turnos=turnos,
        vendas=vendas,
        despesas=despesas,
        caixa_apurado_total=ap_total,
        caixa_apresentado_total=apres_total,
        faturamento_periodo=faturamento,
    )
