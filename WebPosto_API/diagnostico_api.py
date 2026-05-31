#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║         WEBPOSTO API — DIAGNÓSTICO COMPLETO                      ║
║         Grupo Lisboa | mlisboa17@gmail.com                       ║
╚══════════════════════════════════════════════════════════════════╝

Descobre TUDO que está liberado na sua chave de integração.

Uso:
    pip install requests python-dotenv
    python diagnostico_api.py

    Ou com chave direta:
    python diagnostico_api.py --chave $WEBPOSTO_CHAVE  # Configure em .env
"""

import sys
import json
import time
import argparse
from datetime import date, timedelta

try:
    import requests
except ImportError:
    print("❌ Instale: pip install requests")
    sys.exit(1)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
import os
DEFAULT_KEY = os.getenv("WEBPOSTO_CHAVE", "SEU_TOKEN_AQUI")  # Configure em .env
BASE_URL = "https://web.qualityautomacao.com.br"
BASE_URL_ALT = "http://web.qualityautomacao.com.br"

HOJE = date.today()
ONTEM = HOJE - timedelta(days=1)
SEMANA = HOJE - timedelta(days=7)
MES = HOJE - timedelta(days=30)

# ─── CORES ────────────────────────────────────────────────────────────────────
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

# ─── RESULTADOS ───────────────────────────────────────────────────────────────
resultados = []


def cabecalho(titulo: str):
    print(f"\n{BOLD}{BLUE}{'═'*65}{RESET}")
    print(f"{BOLD}{BLUE}  {titulo}{RESET}")
    print(f"{BOLD}{BLUE}{'═'*65}{RESET}")


def secao(titulo: str):
    print(f"\n{BOLD}{'─'*65}{RESET}")
    print(f"{BOLD}  {titulo}{RESET}")
    print(f"{'─'*65}")


def testar(
    chave: str,
    descricao: str,
    endpoint: str,
    params: dict,
    session: requests.Session,
    base: str,
) -> dict:
    """Executa um teste e retorna o resultado."""
    params_final = {
        "CHAVE": chave,
        **{k: v for k, v in params.items() if v is not None},
    }
    url = f"{base}{endpoint}"
    t0 = time.time()

    try:
        r = session.get(url, params=params_final, timeout=20, verify=False)
        latencia = (time.time() - t0) * 1000

        status = r.status_code
        ok = status == 200

        # Tenta parsear JSON
        body = None
        registros = None
        amostra = None
        try:
            body = r.json()
            if isinstance(body, list):
                registros = len(body)
                amostra = body[0] if body else None
            elif isinstance(body, dict):
                registros = 1
                amostra = body
        except Exception:
            body = r.text[:300]

        icon = (
            f"{GREEN}✅{RESET}"
            if ok
            else (f"{YELLOW}⚠️ {RESET}" if status in (403, 401) else f"{RED}❌{RESET}")
        )
        motivo = ""
        if status == 401:
            motivo = " (chave inválida)"
        elif status == 403:
            motivo = " (sem permissão neste endpoint)"
        elif status == 404:
            motivo = " (endpoint não existe)"
        elif status == 400:
            motivo = " (parâmetros inválidos)"
        elif status >= 500:
            motivo = " (erro no servidor)"

        print(f"  {icon} {BOLD}{descricao}{RESET}")
        print(f"     → {endpoint}")
        print(f"     → HTTP {status}{motivo} | {latencia:.0f}ms", end="")

        if ok and registros is not None:
            print(f" | {GREEN}{registros} registro(s){RESET}", end="")
        print()

        if ok and amostra:
            chaves = list(amostra.keys())[:8] if isinstance(amostra, dict) else []
            if chaves:
                print(f"     → Campos: {', '.join(chaves)}")

        resultado = {
            "descricao": descricao,
            "endpoint": endpoint,
            "status": status,
            "ok": ok,
            "latencia_ms": round(latencia),
            "registros": registros,
            "campos": list(amostra.keys()) if isinstance(amostra, dict) else None,
        }
        resultados.append(resultado)
        return resultado

    except requests.exceptions.ConnectionError:
        print(f"  {RED}❌ {descricao}{RESET}")
        print(f"     → {endpoint}")
        print(f"     → {RED}FALHA DE CONEXÃO — servidor inacessível{RESET}")
        r = {
            "descricao": descricao,
            "endpoint": endpoint,
            "status": "CONN_ERROR",
            "ok": False,
        }
        resultados.append(r)
        return r
    except requests.exceptions.Timeout:
        print(f"  {YELLOW}⏱️  {descricao}{RESET}")
        print("     → TIMEOUT após 20s")
        r = {
            "descricao": descricao,
            "endpoint": endpoint,
            "status": "TIMEOUT",
            "ok": False,
        }
        resultados.append(r)
        return r
    except Exception as e:
        print(f"  {RED}❌ {descricao} — ERRO: {e}{RESET}")
        r = {
            "descricao": descricao,
            "endpoint": endpoint,
            "status": "ERROR",
            "ok": False,
        }
        resultados.append(r)
        return r


def main():
    parser = argparse.ArgumentParser(description="Diagnóstico WebPosto API")
    parser.add_argument("--chave", default=DEFAULT_KEY, help="Chave de integração")
    parser.add_argument("--base-url", default=BASE_URL, help="URL base da API")
    parser.add_argument("--json", action="store_true", help="Salva resultado em JSON")
    args = parser.parse_args()

    chave = args.chave
    base = args.base_url
    base_alt = BASE_URL_ALT if base == BASE_URL else BASE_URL

    # Suprime warnings de SSL
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    session = requests.Session()
    session.headers.update({"User-Agent": "GrupoLisboa-WebPosto-Diagnostico/1.0"})

    # ─── CABEÇALHO ────────────────────────────────────────────────────────────
    cabecalho("DIAGNÓSTICO COMPLETO — WEBPOSTO API")
    print(f"\n  {BOLD}Chave:{RESET}    {chave}")
    print(f"  {BOLD}Base URL:{RESET} {base}")
    print(f"  {BOLD}Data:{RESET}     {HOJE.isoformat()}")

    # ─── STEP 1: CONECTIVIDADE ────────────────────────────────────────────────
    secao("STEP 1 — Conectividade e Autenticação")

    # Testa HTTPS
    r_filial = testar(
        chave,
        "Filial (healthcheck)",
        "/INTEGRACAO/FILIAL",
        {"pagina": 0, "tamanhoPagina": 1},
        session,
        base,
    )

    # Se falhou, tenta HTTP
    if not r_filial["ok"] and r_filial["status"] in ("CONN_ERROR", "TIMEOUT", 0):
        print(f"\n  {YELLOW}→ HTTPS falhou. Tentando HTTP...{RESET}")
        r_filial = testar(
            chave,
            "Filial via HTTP",
            "/INTEGRACAO/FILIAL",
            {"pagina": 0, "tamanhoPagina": 1},
            session,
            base_alt,
        )
        if r_filial["ok"]:
            base = base_alt
            print(f"  {GREEN}→ Usando HTTP: {base}{RESET}")

    # Usuários
    testar(chave, "Usuários", "/INTEGRACAO/USUARIO", {}, session, base)

    # Administradoras (frota/convênio)
    testar(chave, "Administradoras", "/INTEGRACAO/ADMINISTRADORA", {}, session, base)

    # ─── STEP 2: COMBUSTÍVEL ──────────────────────────────────────────────────
    secao("STEP 2 — Combustível e Abastecimento")

    testar(
        chave,
        "Abastecimentos (últimos 7 dias)",
        "/INTEGRACAO/ABASTECIMENTO",
        {"dataInicial": SEMANA.isoformat(), "dataFinal": HOJE.isoformat()},
        session,
        base,
    )

    testar(
        chave,
        "Abastecimentos (ontem)",
        "/INTEGRACAO/ABASTECIMENTO",
        {"dataInicial": ONTEM.isoformat(), "dataFinal": HOJE.isoformat()},
        session,
        base,
    )

    testar(
        chave,
        "Encerrantes (últimos 7 dias)",
        "/INTEGRACAO/ABASTECIMENTO_ENCERRANTE",
        {"dataInicial": SEMANA.isoformat(), "dataFinal": HOJE.isoformat()},
        session,
        base,
    )

    testar(
        chave,
        "Divergências de Abastecimento",
        "/INTEGRACAO/ABASTECIMENTO_DIVERGENCIA",
        {"dataInicial": SEMANA.isoformat(), "dataFinal": HOJE.isoformat()},
        session,
        base,
    )

    testar(
        chave,
        "Pedido de Combustível",
        "/INTEGRACAO/PEDIDO_COMBUSTIVEL",
        {"dataInicial": MES.isoformat(), "dataFinal": HOJE.isoformat()},
        session,
        base,
    )

    testar(
        chave,
        "LMC (Livro Movimento Combustível)",
        "/INTEGRACAO/LMC",
        {"dataInicial": MES.isoformat(), "dataFinal": HOJE.isoformat()},
        session,
        base,
    )

    # ─── STEP 3: VENDAS & FINANCEIRO ──────────────────────────────────────────
    secao("STEP 3 — Vendas e Financeiro")

    testar(
        chave,
        "Vendas (últimos 7 dias)",
        "/INTEGRACAO/VENDA",
        {"dataInicial": SEMANA.isoformat(), "dataFinal": HOJE.isoformat()},
        session,
        base,
    )

    testar(
        chave,
        "Vendas Rede",
        "/INTEGRACAO/VENDA_REDE",
        {"dataInicial": SEMANA.isoformat(), "dataFinal": HOJE.isoformat()},
        session,
        base,
    )

    testar(
        chave,
        "Títulos a Receber",
        "/INTEGRACAO/TITULO_RECEBER",
        {"dataInicial": MES.isoformat(), "dataFinal": HOJE.isoformat()},
        session,
        base,
    )

    testar(
        chave,
        "Títulos a Pagar",
        "/INTEGRACAO/TITULO_PAGAR",
        {"dataInicial": MES.isoformat(), "dataFinal": HOJE.isoformat()},
        session,
        base,
    )

    testar(
        chave,
        "Caixa",
        "/INTEGRACAO/CAIXA",
        {"dataInicial": SEMANA.isoformat(), "dataFinal": HOJE.isoformat()},
        session,
        base,
    )

    testar(
        chave,
        "Transferências",
        "/INTEGRACAO/TRANSFERENCIA",
        {"dataInicial": SEMANA.isoformat(), "dataFinal": HOJE.isoformat()},
        session,
        base,
    )

    testar(
        chave,
        "Adiantamento Fornecedor",
        "/INTEGRACAO/ADIANTAMENTO_FORNECEDOR",
        {"dataInicial": MES.isoformat(), "dataFinal": HOJE.isoformat()},
        session,
        base,
    )

    # ─── STEP 4: CLIENTES & PRODUTOS ──────────────────────────────────────────
    secao("STEP 4 — Clientes e Produtos")

    testar(
        chave,
        "Clientes",
        "/INTEGRACAO/CLIENTE",
        {"pagina": 0, "tamanhoPagina": 10},
        session,
        base,
    )

    testar(
        chave,
        "Veículos",
        "/INTEGRACAO/VEICULO",
        {"pagina": 0, "tamanhoPagina": 10},
        session,
        base,
    )

    testar(
        chave,
        "Produtos",
        "/INTEGRACAO/PRODUTO",
        {"pagina": 0, "tamanhoPagina": 10},
        session,
        base,
    )

    testar(
        chave, "Combustível (cadastro)", "/INTEGRACAO/COMBUSTIVEL", {}, session, base
    )

    testar(chave, "Preço por Produto", "/INTEGRACAO/PRECO_PRODUTO", {}, session, base)

    testar(chave, "Estoque", "/INTEGRACAO/ESTOQUE", {}, session, base)

    # ─── STEP 5: NF & COMPRAS ─────────────────────────────────────────────────
    secao("STEP 5 — Notas Fiscais e Pedidos de Compra")

    testar(
        chave,
        "NF Entrada",
        "/INTEGRACAO/NOTA_FISCAL_ENTRADA",
        {"dataInicial": MES.isoformat(), "dataFinal": HOJE.isoformat()},
        session,
        base,
    )

    testar(
        chave,
        "NF Saída",
        "/INTEGRACAO/NOTA_FISCAL_SAIDA",
        {"dataInicial": MES.isoformat(), "dataFinal": HOJE.isoformat()},
        session,
        base,
    )

    testar(
        chave,
        "Pedidos de Compras",
        "/INTEGRACAO/PEDIDO_COMPRAS",
        {"dataInicial": MES.isoformat(), "dataFinal": HOJE.isoformat()},
        session,
        base,
    )

    # ─── STEP 6: SWAGGER / DOCS ───────────────────────────────────────────────
    secao("STEP 6 — Swagger / API Docs")

    for ep in ["/v3/api-docs", "/v3/api-docs/swagger-config"]:
        url_full = f"{base}{ep}"
        try:
            r = session.get(url_full, params={"CHAVE": chave}, timeout=10, verify=False)
            status = r.status_code
            icon = f"{GREEN}✅{RESET}" if status == 200 else f"{RED}❌{RESET}"
            print(f"  {icon} {ep} → HTTP {status}")
            if status == 200:
                try:
                    data = r.json()
                    urls = data.get("urls", [])
                    if urls:
                        print(
                            f"     → Grupos encontrados: {[u.get('name') for u in urls]}"
                        )
                except Exception:
                    pass
        except Exception as e:
            print(f"  {RED}❌ {ep} → ERRO: {e}{RESET}")

    # ─── RESUMO ───────────────────────────────────────────────────────────────
    cabecalho("RESUMO FINAL")

    ok_list = [r for r in resultados if r.get("ok")]
    err_list = [r for r in resultados if not r.get("ok")]
    total = len(resultados)
    ok_count = len(ok_list)

    print(f"\n  {GREEN}{BOLD}{ok_count}/{total} endpoints operacionais{RESET}\n")

    if ok_list:
        print(f"  {GREEN}{BOLD}✅ FUNCIONANDO:{RESET}")
        for r in ok_list:
            reg = f" ({r['registros']} registros)" if r.get("registros") else ""
            print(f"    • {r['endpoint']}{reg}")

    if err_list:
        print(f"\n  {RED}{BOLD}❌ COM ERRO:{RESET}")
        for r in err_list:
            print(f"    • {r['endpoint']} → {r['status']}")

    # Verifica se a chave está totalmente bloqueada
    if ok_count == 0:
        print(f"\n  {RED}{BOLD}⛔ CHAVE NÃO AUTORIZADA OU SERVIDOR INACESSÍVEL{RESET}")
        print(
            """
  Possíveis causas:
    1. A chave ainda não foi ativada pelo suporte Quality Automação
    2. URL incorreta (tente http:// ao invés de https://)
    3. IP não liberado no firewall do servidor
    4. Chave com permissões restritas (peça ao suporte quais endpoints estão liberados)

  Contato Quality Automação:
    → Email: suporte@webposto.com.br
    → Confluenece: https://qualityautomacao.atlassian.net
        """
        )
    elif ok_count < 5:
        print(
            f"\n  {YELLOW}⚠️  Poucos endpoints liberados. Solicite ao suporte da Quality Automação{RESET}"
        )
        print("     quais endpoints estão incluídos no seu contrato.")

    # Salva JSON
    if args.json or ok_count > 0:
        output_file = "diagnostico_resultado.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "data": HOJE.isoformat(),
                    "chave": chave[:8] + "****",
                    "base_url": base,
                    "total": total,
                    "ok": ok_count,
                    "resultados": resultados,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"\n  {BLUE}→ Resultado salvo em: {output_file}{RESET}")

    print(f"\n{'═'*65}\n")
    return 0 if ok_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
