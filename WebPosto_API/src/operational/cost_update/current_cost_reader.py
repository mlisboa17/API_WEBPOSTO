"""Le o custo atual no WebPosto. Somente GET."""

from __future__ import annotations

from typing import Any

from .decimal_utils import optional_decimal
from .schemas import CurrentProductState

COMPANY_CODE = 118508


def _barcodes(product: dict[str, Any]) -> set[str]:
    found: set[str] = set()
    for entry in product.get("produtoCodigoBarra") or []:
        if isinstance(entry, dict) and entry.get("codigoBarra") is not None:
            found.add(str(entry["codigoBarra"]).strip())
        elif entry is not None:
            found.add(str(entry).strip())
    if product.get("produtoCodigoExterno"):
        found.add(str(product["produtoCodigoExterno"]).strip())
    return {value for value in found if value}


class CurrentProductCostReader:
    """GET PRODUTO + PRODUTO_EMPRESA. Checkpoint nunca substitui o estado atual."""

    def __init__(self, reader: Any, *, empresa: int = COMPANY_CODE) -> None:
        self.reader = reader
        self.empresa = empresa
        self.api_reads = 0

    def read(self, key: str, produto_codigo: int, expected_ean: str) -> CurrentProductState:
        if not produto_codigo:
            return CurrentProductState(
                ok=False,
                classification="BLOCKED_MISSING_PRODUCT_CODE",
                reasons=["produtoCodigo ausente"],
            )
        catalog = self.reader.get_catalog(key, produto_codigo - 1, 50)
        links = self.reader.get_company_links(key, produto_codigo - 1, 50)
        self.api_reads += 2
        matches = [row for row in catalog if int(row.get("produtoCodigo") or 0) == produto_codigo]
        if len(matches) != 1:
            return CurrentProductState(
                ok=False,
                ambiguous=True,
                produto_codigo=produto_codigo,
                classification="BLOCKED_AMBIGUOUS_GET",
                reasons=["resposta GET de catalogo ambigua ou vazia"],
                api_reads=2,
            )
        product = matches[0]
        company_links = [row for row in links if int(row.get("produtoCodigo") or 0) == produto_codigo]
        ours = [row for row in company_links if int(row.get("empresaCodigo") or 0) == self.empresa]
        if len(ours) != 1:
            return CurrentProductState(
                ok=False,
                ambiguous=len(ours) > 1 or len(company_links) > 1,
                produto_codigo=produto_codigo,
                empresa_codigo=int(company_links[0]["empresaCodigo"]) if company_links else None,
                classification=(
                    "BLOCKED_AMBIGUOUS_GET"
                    if len(ours) > 1
                    else "BLOCKED_WRONG_COMPANY"
                ),
                reasons=["vinculo PRODUTO_EMPRESA ausente, ambiguo ou de outra empresa"],
                api_reads=2,
            )
        link = ours[0]
        ean_ok = expected_ean in _barcodes(product)
        reasons: list[str] = []
        if not ean_ok:
            reasons.append("EAN diverge do cadastro")
        if link.get("ativo") is False:
            reasons.append("produto inativo")
        return CurrentProductState(
            ok=ean_ok and bool(link.get("ativo", True)),
            empresa_codigo=self.empresa,
            produto_codigo=produto_codigo,
            ean_confirmado=ean_ok,
            ativo=bool(link.get("ativo", True)),
            custo_atual=optional_decimal(link.get("precoCusto")),
            preco_venda=optional_decimal(link.get("precoVenda")),
            ncm=str(product.get("ncm") or "") or None,
            cest=str(product.get("cest") or "") or None,
            descricao=str(product.get("nome") or "") or None,
            classification="OK" if ean_ok else "BLOCKED_EAN_MISMATCH",
            reasons=reasons,
            api_reads=2,
        )
