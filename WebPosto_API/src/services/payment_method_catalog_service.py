"""Catálogo executivo de administradoras e cartões — fonte oficial WebPosto."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from decimal import Decimal
from typing import Any

from src.services.analytics_multiselect import build_finance_center_filters
from src.services.cash_reconciliation.cash_reconciliation_service import CashReconciliationService


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").upper().strip())


def _money(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


class PaymentMethodCatalogService:
    def __init__(self) -> None:
        self._cash = CashReconciliationService()

    @staticmethod
    def _rows(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if isinstance(payload, dict):
            for key in ("resultados", "data", "items"):
                rows = payload.get(key)
                if isinstance(rows, list):
                    return [row for row in rows if isinstance(row, dict)]
        return []

    async def _fetch_cursor(self, client: Any, endpoint: str, params: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
        output: list[dict[str, Any]] = []
        seen: set[str] = set()
        cursor: Any = None
        for _ in range(20):
            query = dict(params)
            if cursor not in (None, ""):
                query["ultimoCodigo"] = cursor
            response = await client.call_endpoint(endpoint, params=query)
            if not response.success:
                error = response.error.message if response.error else "endpoint indisponível"
                return output, error
            rows = self._rows(response.data)
            if not rows:
                break
            signature = json.dumps(rows, sort_keys=True, ensure_ascii=False, default=str)
            if signature in seen:
                break
            seen.add(signature)
            output.extend(rows)
            next_cursor = response.data.get("ultimoCodigo") if isinstance(response.data, dict) else None
            if next_cursor in (None, "", cursor):
                break
            cursor = next_cursor
        unique = {json.dumps(row, sort_keys=True, ensure_ascii=False, default=str): row for row in output}
        return list(unique.values()), None

    @staticmethod
    def _method(admin: dict[str, Any]) -> str:
        description = _norm(admin.get("descricao"))
        kind = _norm(admin.get("tipo"))
        external = _norm(admin.get("administradoraCodigoExterno"))
        blob = f"{description} {kind} {external}"
        if "PREMMIA" in blob or "PREMIA" in blob:
            return "PREMMIA"
        if "PIX" in blob:
            return "PIX_TRANSFERENCIA"
        if "DEBIT" in blob or "DÉBIT" in blob or kind in {"D", "DEB"}:
            return "DEBITO"
        if "CREDIT" in blob or "CRÉDIT" in blob or kind in {"C", "CRED"}:
            return "CREDITO"
        return "NAO_IDENTIFICADO"

    async def build(self, start: str, end: str, company: str | int) -> dict[str, Any]:
        cash = await self._cash._resolve_cash_ops(company)
        filters = build_finance_center_filters(start, end, company)
        code = int(company)
        administrators, admin_error = await self._fetch_cursor(cash._overview.client, "administradora_rede", {})
        cards, card_error = await self._fetch_cursor(cash._overview.client, "cartao_rede", {"dataInicial": start, "dataFinal": end})
        transaction_source = "CARTAO_REDE"
        if not cards:
            cards = await self._cash._fetch_vfp(filters, cash)
            transaction_source = "VENDA_FORMA_PAGAMENTO"
        administrators = [row for row in administrators if int(row.get("empresaCodigo") or 0) == code]
        cards = [row for row in cards if int(row.get("empresaCodigo") or 0) == code]
        if transaction_source == "VENDA_FORMA_PAGAMENTO":
            # A VFP tambem contem dinheiro, prazo e outras naturezas que nao
            # pertencem ao catalogo de administradoras/cartoes.
            cards = [
                row for row in cards
                if row.get("administradoraCodigo") not in (None, "", 0, "0")
                or re.search(r"CART|PIX|PREMM?IA", _norm(row.get("nomeFormaPagamento")))
            ]
        admin_by_code = {str(row.get("administradoraCodigo")): row for row in administrators}
        buckets: dict[tuple[str, str, str], dict[str, Any]] = {}
        for row in cards:
            admin_code = str(row.get("administradoraCodigo") or "")
            admin = admin_by_code.get(admin_code) or {
                "descricao": row.get("adiministradoraDescricao") or row.get("administradoraDescricao"),
                "administradoraCodigo": admin_code,
            }
            method = self._method(admin)
            description = str(admin.get("descricao") or "Administradora não identificada").strip()
            movement_date = str(row.get("dataMovimento") or row.get("dataFiscal") or "")[:10]
            key = (admin_code, method, movement_date)
            bucket = buckets.setdefault(key, {
                "administradoraCodigo": admin_code,
                "administradora": description,
                "modalidade": method,
                "dataMovimento": movement_date,
                "valorBruto": Decimal("0"),
                "taxaEstimada": Decimal("0"),
                "valorLiquidoEsperado": Decimal("0"),
                "registros": 0,
                "pendentes": 0,
                "pagos": 0,
                "comNsu": 0,
                "comAutorizacao": 0,
                "bandeiras": set(),
            })
            gross = _money(row.get("valor") or row.get("valorPagamento"))
            rate = _money(row.get("taxaPercentual"))
            net = gross * (Decimal("1") - rate / Decimal("100"))
            bucket["valorBruto"] += gross
            bucket["taxaEstimada"] += gross - net
            bucket["valorLiquidoEsperado"] += net
            bucket["registros"] += 1
            bucket["pendentes"] += 1 if row.get("pendente") is True else 0
            bucket["pagos"] += 1 if row.get("dataPagamento") else 0
            bucket["comNsu"] += 1 if row.get("nsu") or row.get("nsuTef") else 0
            bucket["comAutorizacao"] += 1 if row.get("autorizacao") else 0
            if row.get("codigoBandeira"):
                bucket["bandeiras"].add(str(row["codigoBandeira"]))
        items = []
        for bucket in buckets.values():
            items.append({
                **{k: v for k, v in bucket.items() if k not in {"bandeiras", "valorBruto", "taxaEstimada", "valorLiquidoEsperado"}},
                "bandeiras": sorted(bucket["bandeiras"]),
                "valorBruto": str(bucket["valorBruto"].quantize(Decimal("0.01"))),
                "taxaEstimada": str(bucket["taxaEstimada"].quantize(Decimal("0.01"))),
                "valorLiquidoEsperado": str(bucket["valorLiquidoEsperado"].quantize(Decimal("0.01"))),
            })
        items.sort(key=lambda item: Decimal(item["valorBruto"]), reverse=True)
        modality_totals: dict[str, Decimal] = defaultdict(Decimal)
        for item in items:
            modality_totals[item["modalidade"]] += Decimal(item["valorBruto"])
        return {
            "empresaCodigo": code,
            "administradoras": administrators,
            "cartoes": items,
            "resumoModalidades": {key: str(value.quantize(Decimal("0.01"))) for key, value in modality_totals.items()},
            "premmia": [item for item in items if item["modalidade"] == "PREMMIA"],
            "qualidade": {
                "administradorasEncontradas": len(administrators),
                "cartoesEncontrados": len(cards),
                "cartoesNaoIdentificados": sum(item["registros"] for item in items if item["modalidade"] == "NAO_IDENTIFICADO"),
                "fonteMovimentos": transaction_source,
                "adminError": admin_error,
                "cardError": card_error,
            },
        }
