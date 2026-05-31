#!/usr/bin/env python3
"""
Exemplo de alteração de produto via PUT /INTEGRACAO/ALTERAR_PRODUTO
=====================================================================

Demonstra como atualizar completamente um produto existente.
A API exige que o payload contenha TODOS os campos do produto,
não apenas os que deseja alterar (não suporta patch parcial).

Uso:
    python scripts/exemplo_alterar_produto.py
"""

import requests
import json
from datetime import datetime

BASE_URL = "https://web.qualityautomacao.com.br"
API_KEY = "<WEBPOSTO_API_TOKEN>"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

def get_produto(codigo: str):
    """Fetch um produto existente pela descrição."""
    url = f"{BASE_URL}/INTEGRACAO/PRODUTO"
    params = {"descricao": codigo}

    resp = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    data = resp.json()

    if data and len(data) > 0:
        return data[0]
    return None

def alterar_produto(produto_id: str, payload: dict):
    """
    Altera um produto existente.

    Args:
        produto_id: ID do produto (INTEGRACAO/PRODUTO/{id})
        payload: Dicionário completo com todos os campos do produto

    Returns:
        Response JSON com resultado da operação
    """
    url = f"{BASE_URL}/INTEGRACAO/ALTERAR_PRODUTO/{produto_id}"

    print(f"\n📤 PUT {url}")
    print(f"Body: {json.dumps(payload, indent=2)}\n")

    resp = requests.put(url, headers=HEADERS, json=payload)

    print(f"Status: {resp.status_code}")
    try:
        result = resp.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        return result
    except:
        print(f"Response: {resp.text}")
        return None

if __name__ == "__main__":
    print("=" * 70)
    print("EXEMPLO: Alteração de Produto via PUT /INTEGRACAO/ALTERAR_PRODUTO")
    print("=" * 70)

    # Exemplo 1: Alterar preço de venda
    print("\n1️⃣  Exemplo: Aumentar preço de venda de GASOLINA COMUM")
    print("-" * 70)

    payload = {
        "codigoBarras": "000004",
        "descricao": "GASOLINA COMUM.",
        "precoVenda": "7.5500",  # ALTERADO (era 7.0200)
        "precoCusto": "6.0209",
        "ativo": True,
        "estoqueAtual": "0.0000",
        "unidadeMedida": "L",
        "ncm": "27101259",
        "cest": "0600201",
        "cstIcms": None,
        "aliquotaIcms": None,
        "codigoGrupo": 24554,
        "nomeGrupo": None,
        "subGrupo1Codigo": None,
        "subGrupo2Codigo": None,
        "subGrupo3Codigo": None,
        "tipoProduto": "C",
        "tipoCombustivel": "GASOLINA",
        "combustivel": True,
    }

    # Descomente para executar:
    # alterar_produto("1257884", payload)

    # Exemplo 2: Desativar um produto
    print("\n2️⃣  Exemplo: Desativar um produto")
    print("-" * 70)

    payload_inativo = payload.copy()
    payload_inativo["ativo"] = False  # ALTERADO
    payload_inativo["descricao"] = "GASOLINA COMUM. (DESCONTINUADO)"

    # Descomente para executar:
    # alterar_produto("1257884", payload_inativo)

    # Exemplo 3: Atualizar NCM e CEST
    print("\n3️⃣  Exemplo: Atualizar classificação fiscal (NCM/CEST)")
    print("-" * 70)

    payload_fiscal = payload.copy()
    payload_fiscal["ncm"] = "27101100"  # NCM atualizado
    payload_fiscal["cest"] = "0600199"  # CEST atualizado
    payload_fiscal["cstIcms"] = "60"    # CST ICMS (0-90)
    payload_fiscal["aliquotaIcms"] = "18"  # Alíquota

    # Descomente para executar:
    # alterar_produto("1257884", payload_fiscal)

    print("\n" + "=" * 70)
    print("⚠️  IMPORTANTE:")
    print("=" * 70)
    print("""
1. TODOS os campos devem estar presentes no payload (PUT é substitutivo, não patch).
2. Se omitir um campo, a API pode resetá-lo ou rejeitá-lo.
3. Campos com None/null são permitidos (ex: cstIcms, aliquotaIcms).
4. A resposta pode incluir status 200 OK ou um erro com código de negócio.
5. Para testes, descomente as linhas de alterar_produto() acima.

Referência de campos:
  - codigoBarras: string, code de barras
  - descricao: string, nome do produto
  - precoVenda: string/decimal, preço de venda
  - precoCusto: string/decimal, preço de custo
  - ativo: boolean, produto ativo?
  - unidadeMedida: string (L, KG, UN, etc.)
  - ncm: string, código NCM (sempre 8 dígitos)
  - cest: string, código CEST (sempre 7 dígitos)
  - cstIcms: null ou string (00-90)
  - aliquotaIcms: null ou número/string (0-100)
  - tipoProduto: "C" (combustível) ou "P" (produto)
  - combustivel: boolean
""")
