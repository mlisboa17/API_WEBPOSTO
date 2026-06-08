#!/usr/bin/env python3
"""
Probe automatizado de endpoints WebPosto de rede.
Gera: webposto_network_probe_result.json + postman_webposto_network_collection.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.config import load_core_config

# Filiais alvo LOGOS SPACE
TARGET_EMPRESAS = {5256, 5333, 5555, 5556, 5557, 5558, 5559, 5560, 11495, 46433, 74014}

# Mapeamento schema → path WebPosto (conhecidos + inferidos)
NETWORK_ENDPOINTS: dict[str, str] = {
    # Financeiro
    "TituloPagarRede": "/INTEGRACAO/TITULO_PAGAR",
    "TituloReceberRede": "/INTEGRACAO/TITULO_RECEBER",
    "ContaRede": "/INTEGRACAO/CONTA",
    "MovimentoConta": "/INTEGRACAO/MOVIMENTO_CONTA",
    "DespesasFinanceiroRede": "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE",
    "TransferenciaBancaria": "/INTEGRACAO/TRANSFERENCIA_BANCARIA",
    # Vendas
    "VendaRede": "/INTEGRACAO/VENDA",
    "VendaItemRede": "/INTEGRACAO/CONSULTAR_VENDA_ITEM_REDE",
    "VendaItem": "/INTEGRACAO/VENDA_ITEM",
    "VendasFormaPagamentoRede": "/INTEGRACAO/CONSULTAR_VENDA_FORMA_PAGAMENTO_REDE",
    "VendaFormaPagamento": "/INTEGRACAO/VENDA_FORMA_PAGAMENTO",
    "AbastecimentoRede": "/INTEGRACAO/ABASTECIMENTO",
    "CaixaRede": "/INTEGRACAO/CAIXA",
    "CaixaApresentadoRede": "/INTEGRACAO/CAIXA_APRESENTADO",
    "NfceRede": "/INTEGRACAO/NFCE",
    # Estoque / Produtos
    "ProdutoRede": "/INTEGRACAO/PRODUTO_REDE",
    "ProdutoEmpresaRede": "/INTEGRACAO/PRODUTO_EMPRESA_REDE",
    "ProdutoEstoque": "/INTEGRACAO/PRODUTO_ESTOQUE",
    "Produto": "/INTEGRACAO/PRODUTO",
    "ProdutoEmpresa": "/INTEGRACAO/PRODUTO_EMPRESA",
    "ProdutoCombustivel": "/INTEGRACAO/PRODUTO_COMBUSTIVEL",
    "TanqueRede": "/INTEGRACAO/TANQUE",
    "EstoquePeriodo": "/INTEGRACAO/ESTOQUE_PERIODO",
    # Combustíveis
    "LmcRede": "/INTEGRACAO/CONSULTAR_LMC_REDE",
    "AnaliseVendasCombustivel": "/INTEGRACAO/CONSULTAR_ANALISE_VENDAS_COMBUSTIVEL",
    # Rede / cadastro
    "Empresas": "/INTEGRACAO/EMPRESAS",
    # Endpoints inferidos (podem 404)
    "PlanoContaGerencial": "/INTEGRACAO/PLANO_CONTA_GERENCIAL",
    "LancamentoContabil": "/INTEGRACAO/LANCAMENTO_CONTABIL",
    "LancamentoContabilItem": "/INTEGRACAO/LANCAMENTO_CONTABIL_ITEM",
    "DRE": "/INTEGRACAO/DRE",
    "DuplicataRede": "/INTEGRACAO/DUPLICATA_REDE",
    "ClienteRede": "/INTEGRACAO/CLIENTE_REDE",
    "FornecedorRede": "/INTEGRACAO/FORNECEDOR_REDE",
    "CentroCustoRede": "/INTEGRACAO/CENTRO_CUSTO_REDE",
    "FuncionarioRede": "/INTEGRACAO/FUNCIONARIO_REDE",
    "BombaRede": "/INTEGRACAO/BOMBA_REDE",
    "BicoRede": "/INTEGRACAO/BICO_REDE",
    "LmcRedeBico": "/INTEGRACAO/CONSULTAR_LMC_REDE_BICO",
    "LmcRedeTanque": "/INTEGRACAO/CONSULTAR_LMC_REDE_TANQUE",
}


def _rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("resultados", "data", "items"):
            val = payload.get(key)
            if isinstance(val, list):
                return [r for r in val if isinstance(r, dict)]
    return []


def _extract_empresas(rows: list[dict[str, Any]]) -> list[int]:
    codes: set[int] = set()
    for row in rows:
        for key in ("empresaCodigo", "codigoEmpresa", "codWeb", "codigo"):
            val = row.get(key)
            if val is not None:
                try:
                    codes.add(int(val))
                except (TypeError, ValueError):
                    pass
    return sorted(codes)


def classify(entry: dict[str, Any]) -> str:
    status = entry.get("httpStatus", 0)
    registros = entry.get("registros", 0)
    empresas = set(entry.get("empresaCodigos") or [])
    overlap = empresas & TARGET_EMPRESAS

    if status in {401, 403}:
        return "NAO_USAR"
    if status == 404:
        return "NAO_USAR"
    if status >= 500 or entry.get("timeout"):
        return "NAO_USAR"
    if status != 200:
        return "APENAS_DIAGNOSTICO"
    if registros == 0:
        return "APENAS_DIAGNOSTICO"
    if not empresas:
        return "APENAS_DIAGNOSTICO"
    if len(overlap) >= 2:
        return "USAR_AGORA"
    if len(overlap) == 1 or registros > 0:
        return "USAR_COM_CUIDADO"
    return "APENAS_DIAGNOSTICO"


async def probe_endpoint(
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
    name: str,
    path: str,
    params: dict[str, Any],
    timeout: float = 30.0,
) -> dict[str, Any]:
    full_params = {**params, "CHAVE": api_key}
    entry: dict[str, Any] = {
        "endpoint": name,
        "path": path,
        "httpStatus": 0,
        "registros": 0,
        "empresaCodigos": [],
        "campos": [],
        "possuiDadosRede": False,
        "serveParaSistema": False,
        "observacao": "",
        "classificacao": "NAO_USAR",
        "timeout": False,
    }

    try:
        resp = await client.get(f"{base_url}{path}", params=full_params, timeout=timeout)
        entry["httpStatus"] = resp.status_code
        if resp.status_code != 200:
            entry["observacao"] = resp.text[:200]
            entry["classificacao"] = classify(entry)
            return entry

        try:
            payload = resp.json()
        except Exception:
            entry["observacao"] = "Resposta não JSON"
            entry["classificacao"] = "APENAS_DIAGNOSTICO"
            return entry

        rows = _rows(payload)
        empresas = _extract_empresas(rows)
        entry["registros"] = len(rows)
        entry["empresaCodigos"] = empresas
        entry["campos"] = list(rows[0].keys())[:30] if rows else []
        entry["possuiDadosRede"] = len(set(empresas) & TARGET_EMPRESAS) >= 2
        entry["serveParaSistema"] = name in {
            "DespesasFinanceiroRede",
            "VendaRede",
            "VendaItemRede",
            "ProdutoEstoque",
            "LmcRede",
            "Empresas",
            "ContaRede",
            "TituloPagarRede",
        } and entry["registros"] > 0 and entry["httpStatus"] == 200

        overlap = set(empresas) & TARGET_EMPRESAS
        entry["observacao"] = f"Filiais alvo com dados: {sorted(overlap)}"
        if isinstance(payload, dict) and payload.get("ultimoCodigo"):
            entry["observacao"] += "; possui ultimoCodigo (paginar)"

    except httpx.TimeoutException:
        entry["timeout"] = True
        entry["observacao"] = "Timeout"
    except Exception as exc:
        entry["observacao"] = str(exc)[:200]

    entry["classificacao"] = classify(entry)
    return entry


def build_postman_collection(base_url: str, api_key: str, results: list[dict], data_ini: str, data_fim: str) -> dict:
    items = []
    for r in results:
        if r.get("classificacao") == "NAO_USAR" and r.get("httpStatus") in {401, 403, 404}:
            continue
        path = r.get("path", "")
        items.append(
            {
                "name": f"{r.get('endpoint')} [{r.get('classificacao')}]",
                "request": {
                    "method": "GET",
                    "header": [],
                    "url": {
                        "raw": f"{base_url}{path}?CHAVE={{{{CHAVE}}}}&dataInicial={data_ini}&dataFinal={data_fim}",
                        "host": [base_url.replace("https://", "").replace("http://", "")],
                        "path": path.strip("/").split("/"),
                        "query": [
                            {"key": "CHAVE", "value": "{{CHAVE}}"},
                            {"key": "dataInicial", "value": data_ini},
                            {"key": "dataFinal", "value": data_fim},
                        ],
                    },
                },
            }
        )

    return {
        "info": {
            "name": "LOGOS SPACE — WebPosto Network Probe",
            "description": "Collection gerada por webposto_network_probe.py",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "variable": [
            {"key": "CHAVE", "value": api_key},
            {"key": "baseUrl", "value": base_url},
        ],
        "item": items,
    }


async def run_probe(data_ini: str, data_fim: str, timeout: float) -> dict[str, Any]:
    config = load_core_config()
    params = {"dataInicial": data_ini, "dataFinal": data_fim}

    results: list[dict] = []
    async with httpx.AsyncClient() as client:
        sem = asyncio.Semaphore(5)

        async def _one(name: str, path: str) -> dict:
            async with sem:
                # EMPRESAS sem datas
                p = {} if name == "Empresas" else params
                t = 15.0 if name == "Empresas" else timeout
                return await probe_endpoint(client, config.webposto_base_url, config.webposto_api_key, name, path, p, t)

        tasks = [_one(name, path) for name, path in NETWORK_ENDPOINTS.items()]
        results = await asyncio.gather(*tasks)

    by_class: dict[str, list] = {}
    for r in results:
        cls = r.get("classificacao", "NAO_USAR")
        by_class.setdefault(cls, []).append(r.get("endpoint"))

    return {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "periodo": {"dataInicial": data_ini, "dataFinal": data_fim},
        "targetEmpresas": sorted(TARGET_EMPRESAS),
        "endpoints": results,
        "resumo": {k: len(v) for k, v in by_class.items()},
        "usar_agora": [r for r in results if r.get("classificacao") == "USAR_AGORA"],
        "usar_com_cuidado": [r for r in results if r.get("classificacao") == "USAR_COM_CUIDADO"],
    }


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-inicial", default="2026-06-03")
    parser.add_argument("--data-final", default="2026-06-08")
    parser.add_argument("--timeout", type=float, default=25.0)
    args = parser.parse_args()

    config = load_core_config()
    data = await run_probe(args.data_inicial, args.data_final, args.timeout)

    json_path = ROOT / "webposto_network_probe_result.json"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    postman = build_postman_collection(
        config.webposto_base_url,
        config.webposto_api_key,
        data["endpoints"],
        args.data_inicial,
        args.data_final,
    )
    postman_path = ROOT / "postman_webposto_network_collection.json"
    postman_path.write_text(json.dumps(postman, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Probe JSON: {json_path}")
    print(f"Postman:  {postman_path}")
    print("Resumo:", data.get("resumo"))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
