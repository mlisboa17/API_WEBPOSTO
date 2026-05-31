"""
Caso de uso: monta AdelaideDashboardMetrics a partir da API Quality (isolado do HTTP).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Optional

from src.application.usecases.fetch_executive_kpis import (
    FetchExecutiveKpisRequest,
    fetch_executive_kpis,
    periodo_preset,
)
from src.application.usecases.fetch_produto_grupos import (
    codigos_produto_dos_grupos,
    fetch_codigos_produtos_grupos,
    fetch_produto_grupos,
    mesclar_filtro_codigos,
)
from src.application.usecases.fetch_unidade_webposto import fetch_unidade_webposto
from src.domain.adelaide.fiscal_catalog import list_fiscal_audit_rows
from src.domain.adelaide.metrics_schema import (
    AdelaideDashboardMetrics,
    mask_metrics_for_role,
    quantize_money,
)


def _por_produto_payload(kpis: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for p in getattr(kpis, "produtos", None) or []:
        rows.append(
            {
                "codigo": p.codigo_produto,
                "nome": p.nome_produto,
                "litros": format(quantize_money(p.litros), "f"),
                "faturamento": format(quantize_money(p.faturamento_bruto), "f"),
                "pis_cofins": format(quantize_money(p.pis_cofins), "f"),
            }
        )
    return rows


async def build_adelaide_metrics(
    periodo: str,
    webposto_client: Any,
    role: str = "director",
    *,
    data_inicial: Optional[date] = None,
    data_final: Optional[date] = None,
    filial: Optional[list[int]] = None,
    codigos_produto: Optional[list[str]] = None,
    grupos_produto: Optional[list[int]] = None,
    apenas_combustivel: bool = False,
    excluir_afericao: bool = True,
    strict: bool = True,
) -> AdelaideDashboardMetrics:
    combustiveis = list_fiscal_audit_rows()
    di, df, label = periodo_preset(periodo)
    if data_inicial is not None:
        di = data_inicial
    if data_final is not None:
        df = data_final
    if data_inicial is not None or data_final is not None:
        label = f"{di.isoformat()} → {df.isoformat()}"

    cfg = getattr(webposto_client, "_config", None)
    chave = getattr(cfg, "chave", "") or ""
    base_url = getattr(cfg, "base_url", "") or ""

    unidade = await fetch_unidade_webposto(
        webposto_client, base_url=base_url, chave=chave
    )

    codigos_finais = codigos_produto
    analise_por_grupos = bool(grupos_produto)
    if grupos_produto:
        idx_grupos = await fetch_produto_grupos(
            webposto_client, base_url=base_url, chave=chave
        )
        codigos_grupos = codigos_produto_dos_grupos(idx_grupos, grupos_produto)
        if not codigos_grupos:
            codigos_grupos = await fetch_codigos_produtos_grupos(
                webposto_client, grupos_produto
            )
        codigos_finais = mesclar_filtro_codigos(codigos_produto, codigos_grupos)
        # Por grupo: Adelaide analisa combustível + loja (ABASTECIMENTO + VENDA)
        apenas_combustivel = False

    incluir_vendas = True

    filtros = {
        "periodo": periodo,
        "data_inicial": di.isoformat(),
        "data_final": df.isoformat(),
        "filial": filial,
        "grupos_produto": grupos_produto,
        "codigos_produto": codigos_finais,
        "apenas_combustivel": apenas_combustivel,
        "excluir_afericao": excluir_afericao,
        "incluir_vendas_pdv": incluir_vendas,
        "motor": "adelaide_abastecimento+venda" if incluir_vendas else "adelaide_abastecimento",
    }

    resp = await fetch_executive_kpis(
        FetchExecutiveKpisRequest(
            data_inicial=di,
            data_final=df,
            periodo_label=label,
            role=role,
            filial=filial,
            codigos_produto=codigos_finais,
            apenas_combustivel=apenas_combustivel,
            excluir_afericao=excluir_afericao,
            incluir_vendas_pdv=incluir_vendas,
            strict=strict,
        ),
        webposto_client,
    )
    k = resp.kpis
    status = "dados_reais_live" if not resp.fallback else "dados_parciais"
    dados_reais = status == "dados_reais_live" and not resp.fallback
    metrics = AdelaideDashboardMetrics(
        faturamento_bruto=quantize_money(k.faturamento_total),
        faturamento_nao_combustivel=quantize_money(k.faturamento_nao_combustivel),
        galonagem_total=quantize_money(k.litros_total),
        credito_recuperavel=quantize_money(k.pis_cofins_total),
        despesas_caixa=quantize_money(k.despesas_caixa or Decimal("0")),
        margem_liquida_real=quantize_money(k.margem_liquida_total),
        periodo=label,
        status_api=status,
        fallback=resp.fallback,
        dados_reais=dados_reais,
        unidade=unidade,
        mensagem=resp.mensagem,
        combustiveis=combustiveis,
        por_produto=_por_produto_payload(k),
        qtd_abastecimentos=resp.qtd_abastecimentos,
        qtd_itens_venda=resp.qtd_itens_venda,
        data_inicial=di.isoformat(),
        data_final=df.isoformat(),
        filtros_aplicados=filtros,
    )

    return mask_metrics_for_role(metrics, role)


def demo_metrics(periodo: str = "30D") -> AdelaideDashboardMetrics:
    return AdelaideDashboardMetrics(
        faturamento_bruto=quantize_money("1250450.8500"),
        faturamento_nao_combustivel=quantize_money("145210.5000"),
        galonagem_total=quantize_money("245300.0000"),
        credito_recuperavel=quantize_money("18450.7500"),
        despesas_caixa=quantize_money("15420.5000"),
        margem_liquida_real=quantize_money("1100000.0000"),
        periodo=periodo,
        status_api="demonstracao_offline",
        fallback=True,
        mensagem="Configure WEBPOSTO_API_KEY no .env",
    )
