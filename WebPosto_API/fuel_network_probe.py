from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from src.core.config import load_core_config


OUTPUT_JSON = Path("fuel_network_probe_result.json")
OUTPUT_MD = Path("fuel_network_probe_report.md")


@dataclass
class ProbeTarget:
    name: str
    path: str


TARGETS = [
    ProbeTarget("CONSULTAR_VENDA_ITEM_REDE", "/INTEGRACAO/CONSULTAR_VENDA_ITEM_REDE"),
    ProbeTarget("CONSULTAR_ABASTECIMENTO_REDE", "/INTEGRACAO/CONSULTAR_ABASTECIMENTO_REDE"),
    ProbeTarget("CONSULTAR_VENDA_REDE", "/INTEGRACAO/CONSULTAR_VENDA_REDE"),
    ProbeTarget("CONSULTAR_LMC_REDE", "/INTEGRACAO/CONSULTAR_LMC_REDE"),
]


def extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("resultados", "data", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    return []


def has_any(row: dict[str, Any], keys: tuple[str, ...]) -> bool:
    return any(row.get(key) not in (None, "") for key in keys)


def summarize_fields(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "existsEmpresaCodigo": False,
            "existsProdutoCodigo": False,
            "existsQuantidade": False,
            "existsData": False,
            "coverageEmpresas": [],
            "coverageCount": 0,
            "sample": None,
        }

    exists_empresa = any(has_any(row, ("empresaCodigo", "empresa")) for row in rows)
    exists_produto = any(has_any(row, ("produtoCodigo", "produtoLmcCodigo", "produto")) for row in rows)
    exists_quantidade = any(has_any(row, ("quantidade", "saida", "venda", "litros")) for row in rows)
    exists_data = any(has_any(row, ("data", "dataMovimento", "dataLmc", "dia")) for row in rows)

    empresas = sorted(
        {
            int(row.get("empresaCodigo"))
            for row in rows
            if row.get("empresaCodigo") is not None and str(row.get("empresaCodigo")).isdigit()
        }
    )

    return {
        "existsEmpresaCodigo": exists_empresa,
        "existsProdutoCodigo": exists_produto,
        "existsQuantidade": exists_quantidade,
        "existsData": exists_data,
        "coverageEmpresas": empresas,
        "coverageCount": len(empresas),
        "sample": rows[0],
    }


def call_endpoint(base_url: str, api_key: str, path: str, params: dict[str, Any]) -> dict[str, Any]:
    url = f"{base_url}{path}"
    query = {"CHAVE": api_key, **params}

    try:
        response = requests.get(url, params=query, timeout=30)
    except requests.RequestException as exc:
        return {
            "httpStatus": 0,
            "ok": False,
            "error": str(exc),
            "records": 0,
            "fields": {},
        }

    content_type = response.headers.get("content-type", "")
    payload: Any = None
    if "application/json" in content_type.lower():
        try:
            payload = response.json()
        except Exception:
            payload = None

    rows = extract_rows(payload)
    fields = summarize_fields(rows)

    return {
        "httpStatus": response.status_code,
        "ok": response.status_code == 200,
        "error": None if response.status_code == 200 else response.text[:240],
        "records": len(rows),
        "fields": fields,
    }


def build_report(result: dict[str, Any]) -> str:
    endpoints_map = {item["name"]: item for item in result["endpoints"]}
    lmc = endpoints_map.get("CONSULTAR_LMC_REDE", {})
    venda_item = endpoints_map.get("CONSULTAR_VENDA_ITEM_REDE", {})
    abastecimento = endpoints_map.get("CONSULTAR_ABASTECIMENTO_REDE", {})
    venda_rede = endpoints_map.get("CONSULTAR_VENDA_REDE", {})

    lines = [
        "# Sprint 22A - Fuel Network Probe",
        "",
        f"Data de execucao: {result['executedAt']}",
        f"Periodo: {result['periodo']['dataInicial']} ate {result['periodo']['dataFinal']}",
        "",
        "## Resumo",
        "",
        "| Endpoint | HTTP | empresaCodigo | produtoCodigo | quantidade | data | Cobertura filiais |",
        "|---|---:|:---:|:---:|:---:|:---:|---:|",
    ]

    for endpoint in result["endpoints"]:
        fields = endpoint["fields"]
        lines.append(
            "| {name} | {status} | {empresa} | {produto} | {quantidade} | {data} | {coverage} |".format(
                name=endpoint["name"],
                status=endpoint["httpStatus"],
                empresa="SIM" if fields["existsEmpresaCodigo"] else "NAO",
                produto="SIM" if fields["existsProdutoCodigo"] else "NAO",
                quantidade="SIM" if fields["existsQuantidade"] else "NAO",
                data="SIM" if fields["existsData"] else "NAO",
                coverage=fields["coverageCount"],
            )
        )

    lines.extend([
        "",
        "## Conclusoes",
        "",
        "- CONSULTAR_LMC_REDE deve ser a base oficial da Sprint 22 quando retornar HTTP 200 com campos estruturais esperados.",
        f"- CONSULTAR_VENDA_ITEM_REDE status atual: {venda_item.get('httpStatus', 'N/A')}.",
        f"- CONSULTAR_ABASTECIMENTO_REDE status atual: {abastecimento.get('httpStatus', 'N/A')}.",
        f"- CONSULTAR_VENDA_REDE status atual: {venda_rede.get('httpStatus', 'N/A')}.",
        f"- CONSULTAR_LMC_REDE cobertura de filiais no periodo: {lmc.get('fields', {}).get('coverageCount', 0)}.",
        "- Cobertura de filiais considera o conjunto distinto de empresaCodigo retornado por endpoint.",
    ])

    return "\n".join(lines)


def main() -> None:
    load_dotenv()
    cfg = load_core_config()

    today = date.today()
    start = today - timedelta(days=30)
    params = {
        "dataInicial": start.isoformat(),
        "dataFinal": today.isoformat(),
    }

    endpoints_result = []
    for target in TARGETS:
        call = call_endpoint(cfg.webposto_base_url, cfg.webposto_api_key, target.path, params)
        endpoints_result.append(
            {
                "name": target.name,
                "path": target.path,
                **call,
            }
        )

    result = {
        "executedAt": today.isoformat(),
        "periodo": params,
        "endpoints": endpoints_result,
    }

    OUTPUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    OUTPUT_MD.write_text(build_report(result), encoding="utf-8")

    print(f"Arquivo gerado: {OUTPUT_JSON}")
    print(f"Arquivo gerado: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
