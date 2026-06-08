import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.domain.entities.filial_master import list_filiais_master
from src.gateway.webposto_client import WebPostoClient


DATE_RANGES = {
    "ATIVA": {"dataInicial": "2026-06-01", "dataFinal": "2026-06-07"},
    "INATIVA": {"dataInicial": "2026-05-01", "dataFinal": "2026-05-20"},
}

NETWORK_ENDPOINTS = {
    "despesas_rede": "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
    "caixa_rede": "/INTEGRACAO/CONSULTAR_CAIXA_REDE",
    "caixa_apresentado_rede": "/INTEGRACAO/CONSULTAR_CAIXA_APRESENTADO_REDE",
}

INDIVIDUAL_ENDPOINTS = {
    "empresas": "/INTEGRACAO/EMPRESAS",
    "venda": "/INTEGRACAO/VENDA",
    "venda_item": "/INTEGRACAO/VENDA_ITEM",
    "venda_forma_pagamento": "/INTEGRACAO/VENDA_FORMA_PAGAMENTO",
    "titulo_pagar": "/INTEGRACAO/TITULO_PAGAR",
    "titulo_receber": "/INTEGRACAO/TITULO_RECEBER",
    "produto_empresa": "/INTEGRACAO/PRODUTO_EMPRESA",
    "produto_estoque": "/INTEGRACAO/PRODUTO_ESTOQUE",
}


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("resultados", "data", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    return []


def _clean_cnpj(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _match_company(row: dict[str, Any], company_code: int | None, cnpj: str) -> bool:
    row_code = row.get("empresaCodigo") or row.get("codigo") or row.get("filialCodigo")
    if company_code is not None and str(row_code) == str(company_code):
        return True
    row_cnpj = _clean_cnpj(row.get("cnpj") or row.get("cnpjCpf") or row.get("documento"))
    return bool(cnpj and row_cnpj and row_cnpj == cnpj)


async def _call_endpoint(client: WebPostoClient, path: str, params: dict[str, Any] | None) -> tuple[int, Any]:
    final_params = client._with_key(params)
    async with httpx.AsyncClient(base_url=client.config.webposto_base_url, timeout=25.0) as http_client:
        response = await http_client.get(path, params=final_params)
        try:
            payload = response.json()
        except Exception:
            payload = response.text[:1000]
        return response.status_code, payload


async def main() -> None:
    client = WebPostoClient()
    filiais = list_filiais_master()

    network_snapshot: dict[str, dict[str, Any]] = {}
    empresa_codigos_rede = set()

    for label, path in NETWORK_ENDPOINTS.items():
        status, payload = await _call_endpoint(client, path, DATE_RANGES["ATIVA"])
        rows = _extract_rows(payload) if status == 200 else []
        companies = {
            int(row.get("empresaCodigo"))
            for row in rows
            if row.get("empresaCodigo") not in (None, "") and str(row.get("empresaCodigo")).isdigit()
        }
        empresa_codigos_rede.update(companies)
        network_snapshot[label] = {
            "path": path,
            "httpStatus": status,
            "rows": len(rows),
            "empresaCodigos": sorted(companies),
        }

    status_empresas, payload_empresas = await _call_endpoint(client, INDIVIDUAL_ENDPOINTS["empresas"], None)
    rows_empresas = _extract_rows(payload_empresas) if status_empresas == 200 else []

    audit_rows: list[dict[str, Any]] = []
    globo_candidates: list[dict[str, Any]] = []

    for row in rows_empresas:
        raw_text = " ".join(str(row.get(key) or "") for key in ("fantasia", "nome", "razao", "razaoSocial", "cnpj", "cnpjCpf"))
        if "AUTO POSTO GLOBO" in raw_text.upper() or _clean_cnpj(row.get("cnpj") or row.get("cnpjCpf")) == "41043647000188":
            globo_candidates.append(row)

    for filial in filiais:
        cnpj = _clean_cnpj(filial.cnpj)
        periodo = DATE_RANGES["INATIVA"] if filial.status == "INATIVA" else DATE_RANGES["ATIVA"]
        api_match = next((row for row in rows_empresas if _match_company(row, filial.empresa_codigo, cnpj)), None)

        endpoint_results: dict[str, dict[str, Any]] = {}
        counts = {
            "despesas": False,
            "vendas": False,
            "estoque": False,
            "contasPagar": False,
            "contasReceber": False,
            "movimentacaoCaixa": False,
        }

        if filial.empresa_codigo is not None:
            for label, path in INDIVIDUAL_ENDPOINTS.items():
                if label == "empresas":
                    continue
                params = dict(periodo)
                params["empresaCodigo"] = filial.empresa_codigo
                status, payload = await _call_endpoint(client, path, params)
                rows = _extract_rows(payload) if status == 200 else []
                filtered_rows = [row for row in rows if _match_company(row, filial.empresa_codigo, cnpj)] or rows
                endpoint_results[label] = {
                    "httpStatus": status,
                    "totalRegistros": len(filtered_rows),
                }

            counts["despesas"] = filial.empresa_codigo in set(network_snapshot["despesas_rede"]["empresaCodigos"])
            counts["vendas"] = any(endpoint_results[key]["totalRegistros"] > 0 for key in ("venda", "venda_item", "venda_forma_pagamento"))
            counts["estoque"] = any(endpoint_results[key]["totalRegistros"] > 0 for key in ("produto_empresa", "produto_estoque"))
            counts["contasPagar"] = endpoint_results["titulo_pagar"]["totalRegistros"] > 0
            counts["contasReceber"] = endpoint_results["titulo_receber"]["totalRegistros"] > 0
            counts["movimentacaoCaixa"] = filial.empresa_codigo in set(network_snapshot["caixa_rede"]["empresaCodigos"])
        else:
            endpoint_results = {
                label: {"httpStatus": None, "totalRegistros": 0}
                for label in INDIVIDUAL_ENDPOINTS
                if label != "empresas"
            }

        audit_rows.append(
            {
                **filial.to_dict(),
                "existeNaApi": api_match is not None,
                "codigoApiDescoberto": api_match.get("empresaCodigo") if isinstance(api_match, dict) else None,
                "possuiDespesas": counts["despesas"],
                "possuiVendas": counts["vendas"],
                "possuiEstoque": counts["estoque"],
                "possuiContasPagar": counts["contasPagar"],
                "possuiContasReceber": counts["contasReceber"],
                "possuiMovimentacaoCaixa": counts["movimentacaoCaixa"],
                "apareceEmEndpointsRede": filial.empresa_codigo in empresa_codigos_rede if filial.empresa_codigo is not None else False,
                "endpoints": endpoint_results,
            }
        )

    summary = {
        "filiais": audit_rows,
        "networkSnapshot": network_snapshot,
        "empresaCodigosRede": sorted(empresa_codigos_rede),
        "globoInvestigacao": {
            "cnpj": "41.043.647/0001-88",
            "candidatosEmpresas": globo_candidates,
            "codigoDescoberto": globo_candidates[0].get("empresaCodigo") if globo_candidates else None,
        },
    }

    output_path = Path("audit_filial_master_resultado.json")
    output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=" * 72)
    print("AUDITORIA FILIAL MASTER")
    print("=" * 72)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nArquivo salvo em: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())