"""
Mapeamento JSON WebPosto → entidades de domínio (ACL).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from src.domain.entities.sales import Filial, Product, SalesInvoice, TankVolume
from src.domain.value_objects.money import Money
from src.domain.value_objects.payment_method import PaymentMethod
from src.domain.value_objects.quantity import Quantity


def _money(val: Any) -> Money:
    return Money(amount=val or 0)


def _rows(payload: Any) -> List[dict]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        rows = payload.get("resultados") or payload.get("data") or []
        return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []
    return []


def map_product(row: dict, empresa_row: Optional[dict] = None) -> Product:
    emp = empresa_row or {}
    pid = int(row.get("produtoCodigo") or row.get("codigo") or 0)
    pv = emp.get("precoVenda") if emp.get("precoVenda") is not None else row.get("precoVenda", 0)
    pc = emp.get("precoCusto") if emp.get("precoCusto") is not None else row.get("precoCusto", 0)
    return Product(
        codigo=pid,
        descricao=str(row.get("nome") or row.get("descricao") or f"Produto {pid}"),
        grupo_codigo=row.get("grupoCodigo") or row.get("codigoGrupo"),
        preco_venda=_money(pv),
        preco_custo=_money(pc),
        ativo=bool(emp.get("ativo", row.get("ativo", True))),
    )


def map_filial(row: dict) -> Filial:
    return Filial(
        codigo=int(row.get("empresaCodigo") or row.get("codigo") or row.get("filialCodigo") or 0),
        razao_social=str(row.get("razaoSocial") or row.get("nome") or ""),
        nome_fantasia=str(row.get("nomeFantasia") or row.get("fantasia") or ""),
        cnpj=row.get("cnpj"),
    )


def map_sales_invoice(row: dict) -> SalesInvoice:
    vid = int(row.get("vendaCodigo") or row.get("codigo") or 0)
    dt_raw = row.get("data") or row.get("dataMovimento") or row.get("dataEmissao")
    try:
        dt = datetime.fromisoformat(str(dt_raw).replace("Z", "+00:00")) if dt_raw else datetime.utcnow()
    except Exception:
        dt = datetime.utcnow()
    return SalesInvoice(
        id=vid,
        data_emissao=dt,
        filial_codigo=row.get("filialCodigo") or row.get("empresaCodigo"),
        forma_pagamento=PaymentMethod.from_raw(row.get("formaPagamento") or row.get("tipoPagamento")),
        valor_total=_money(row.get("valorTotal") or row.get("valor") or 0),
        itens=[],
    )


def map_tank_volume(row: dict) -> TankVolume:
    nome = str(row.get("nomeProduto") or row.get("nome") or "")
    litros = row.get("volume") or row.get("litros") or row.get("quantidade") or 0
    return TankVolume(
        tanque_codigo=int(row.get("tanqueCodigo") or row.get("codigo") or 0),
        produto_codigo=row.get("produtoCodigo"),
        produto_nome=nome,
        volume_litros=Quantity(value=litros, unit="L"),
    )
