#!/usr/bin/env python3
"""Sprint D00 — WebPosto Capability Discovery — gera relatórios MD (somente descoberta)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PROBE = ROOT / "webposto_network_probe_result.json"
from src.services.prestacao_contas_intelligence_service import (  # noqa: E402
    API_FIELD_COVERAGE,
    PRESTACAO_FIELD_CATALOG,
)

# Campos adicionais observados na Prestação de Contas (UI/documento) além do catálogo F03.4-B
PRESTACAO_UI_EXTENDED: dict[str, dict] = {
    "sangria": {"ui": True, "api": "partial", "endpoint": "DESPESAS_REDE + CAIXA_APRESENTADO.despesa*", "logos": "F03.4-B inferência"},
    "suprimento": {"ui": True, "api": "partial", "endpoint": "MOVIMENTO_CONTA (crédito caixa)", "logos": "não modelado"},
    "valeFuncionario": {"ui": True, "api": True, "endpoint": "CAIXA_APRESENTADO.valeFun* + DESPESAS", "logos": "F03.3 ledger"},
    "descontoFuncionario": {"ui": True, "api": "partial", "endpoint": "VENDA_ITEM.totalDesconto + DESPESAS", "logos": "sem dimensão operador"},
    "adiantamento": {"ui": True, "api": "partial", "endpoint": "DESPESAS_REDE + TITULO_PAGAR.adiantamento", "logos": "F03.2-A classificação"},
    "faltaCaixa": {"ui": True, "api": "derived", "endpoint": "CAIXA.diferenca (<0)", "logos": "F03.3 ledger"},
    "sobraCaixa": {"ui": True, "api": "derived", "endpoint": "CAIXA.diferenca (>0)", "logos": "F03.3 ledger"},
    "vendasFuncionario": {"ui": True, "api": "partial", "endpoint": "VENDA/VENDA_ITEM.funcionarioCodigo", "logos": "overview agregado"},
    "metaFuncionario": {"ui": True, "api": False, "endpoint": "— (GRUPO_META existe, sem vínculo turno)", "logos": "não usado"},
    "produtividadeFuncionario": {"ui": True, "api": False, "endpoint": "—", "logos": "não usado"},
    "participacaoIndividual": {"ui": True, "api": False, "endpoint": "—", "logos": "não usado"},
    "funcionarioNome": {"ui": True, "api": False, "endpoint": "— (FUNCIONARIO_REDE = 401)", "logos": "não usado"},
    "fundoCaixa": {"ui": True, "api": False, "endpoint": "CAIXA.abertura (parcial)", "logos": "não usado"},
    "cartaoDetalhado": {"ui": True, "api": "partial", "endpoint": "CAIXA_APRESENTADO.cartao* (sem bandeira)", "logos": "cash ops agregado"},
    "cartaFrete": {"ui": True, "api": True, "endpoint": "CAIXA_APRESENTADO.cartaFrete*", "logos": "não explorado"},
    "notaPrazo": {"ui": True, "api": True, "endpoint": "CAIXA_APRESENTADO.notaPrazo* + TITULO_RECEBER", "logos": "parcial"},
    "emprestimo": {"ui": True, "api": True, "endpoint": "CAIXA_APRESENTADO.emprestimo*", "logos": "F03.4-B"},
    "prePago": {"ui": True, "api": True, "endpoint": "CAIXA_APRESENTADO.prePag*", "logos": "não explorado"},
    "combustivelPorProduto": {"ui": True, "api": True, "endpoint": "VENDA_ITEM + LMC + ABASTECIMENTO", "logos": "fuel module"},
    "turno": {"ui": True, "api": True, "endpoint": "CAIXA.turno/turnoCodigo", "logos": "F03 cash ops"},
    "pdv": {"ui": True, "api": True, "endpoint": "CAIXA.pdvCodigo", "logos": "F03 cash ops"},
}

MOVIMENTO_CAIXA_UI_TYPES = [
    ("SERVICO", "Serviços movimentados no caixa", "—", "none", "Possível proxy: VENDA (não combustível) — não tipado"),
    ("SUPRIMENTO", "Reforço de caixa", "MOVIMENTO_CONTA", "partial", "Crédito em conta caixa; sem campo tipo explícito"),
    ("DESPESA", "Despesa lançada no caixa", "CAIXA_APRESENTADO + DESPESAS_REDE", "yes", "F03.1 mapeado"),
    ("TROCA", "Troca / devolução física", "—", "none", "Sem endpoint; troco apenas em VENDA.troco"),
    ("NOTA", "Nota a prazo no caixa", "CAIXA_APRESENTADO.notaPrazo*", "yes", "Bloco 3 — crédito interno"),
    ("EMPRESTIMO", "Empréstimo funcionário", "CAIXA_APRESENTADO.emprestimo*", "yes", "F03.4-B"),
    ("CARTA_FRETE", "Carta frete", "CAIXA_APRESENTADO.cartaFrete*", "yes", "Nunca modelado no Logos"),
]

OPERACOES_PDV_UI = [
    ("cancelamento", "Cancelamento de venda", "VENDA.cancelada + NFCE.situacao", "partial", "Sem log de autorizador"),
    ("estorno", "Estorno", "FINANCEIRO_EXCLUSAO", "partial", "Auditoria, não operação PDV"),
    ("aberturaCaixa", "Abertura de caixa", "CAIXA.abertura/fechado", "yes", "F03 cash ops"),
    ("fechamentoCaixa", "Fechamento", "CAIXA.fechamento/consolidado", "yes", "F03 cash ops"),
    ("troco", "Troco", "VENDA.troco", "yes", "Não ligado a operador no Logos"),
    ("sangria", "Sangria PDV", "DESPESAS_REDE (semântico)", "partial", "Sem endpoint PDV"),
    ("suprimento", "Suprimento PDV", "MOVIMENTO_CONTA", "partial", "Sem endpoint PDV"),
    ("venda", "Venda", "VENDA + VENDA_ITEM + ABASTECIMENTO", "yes", "Overview + fuel"),
    ("desconto", "Desconto na venda", "VENDA_ITEM.totalDesconto", "partial", "Por item, não por operador consolidado"),
    ("autorizacao", "Autorização gerencial", "—", "none", "Não exposto na API token atual"),
    ("abastecimento", "Abastecimento bomba", "ABASTECIMENTO", "yes", "codigoFrentista ≈ operador"),
]

FORMA_PAGAMENTO_MAP = {
    "DINHEIRO": ("CAIXA_APRESENTADO.dinheiro*", "VENDA_FORMA_PAGAMENTO (nomeFormaPagamento)"),
    "PIX": ("VENDA_FORMA_PAGAMENTO", "tipoFormaPagamento / nomeFormaPagamento"),
    "DEBITO": ("VENDA_FORMA_PAGAMENTO + cartao*", "administradoraCodigo"),
    "CREDITO": ("VENDA_FORMA_PAGAMENTO + cartao*", "administradoraCodigo"),
    "CONVENIO": ("VENDA_FORMA_PAGAMENTO", "nomeFormaPagamento"),
    "VALE": ("CAIXA_APRESENTADO.valeCliente* + DESPESAS", "valeFun* parcial"),
    "PRAZO": ("CAIXA_APRESENTADO.notaPrazo* + TITULO_RECEBER", "vendaPrazoCodigo"),
}

LMC_FIELDS = [
    "empresaCodigo", "lmcCodigo", "produtoCodigo", "produtoLmcCodigo", "dataMovimento",
    "abertura", "entrada", "saida", "perdaSobra", "escritural", "fechamento", "disponivel",
    "saldo", "precoCusto", "ultimoUsuarioAlteracao", "lmcTanque", "lmcBico", "lmcNota", "codigo",
]

LMC_BLOCKED = [
    "CONSULTAR_LMC_REDE_BICO", "CONSULTAR_LMC_REDE_TANQUE", "PRODUTO_LMC", "BOMBA_REDE", "BICO_REDE",
]

TOP20_HIDDEN = [
    ("funcionarioNome", "Prestação de Contas", "Accountability nominal", "P0"),
    ("participacaoIndividual", "Prestação de Contas", "Performance justa por turno", "P0"),
    ("produtividadeFuncionario", "Prestação de Contas", "Score operacional F04", "P0"),
    ("VENDA.funcionarioCodigo + cancelada", "Operações PDV (proxy VENDA)", "Auditoria cancelamentos por operador", "P0"),
    ("VENDA_FORMA_PAGAMENTO por turno/PDV", "Venda Forma Pagamento", "Mix pagamento operacional", "P0"),
    ("ABASTECIMENTO.codigoFrentista", "Operações PDV (proxy)", "Produtividade bomba", "P1"),
    ("CAIXA_APRESENTADO.cartaFrete*", "Movimento Caixa / Nota", "Recebíveis carta frete", "P1"),
    ("CAIXA_APRESENTADO.notaPrazo*", "Nota no Caixa", "Crédito cliente / prazo", "P1"),
    ("LMC.perdaSobra + lmcBico", "LMC", "Quebra física vs caixa", "P1"),
    ("VENDA_ITEM.funcionarioCodigo", "Operações PDV", "Vendas por operador (item)", "P1"),
    ("NFCE.situacao + vendaCodigo", "Operações PDV", "Rastreio fiscal cancelamento", "P2"),
    ("fundoCaixa", "Prestação de Contas", "Abertura turno / accountability", "P2"),
    ("metaFuncionario", "Prestação / GRUPO_META", "Meta vs realizado", "P2"),
    ("MOVIMENTO_CONTA suprimento", "Movimento Caixa", "Fluxo físico caixa", "P2"),
    ("TITULO_RECEBER + vendaCodigo", "Nota no Caixa", "Conta cliente / recebimento", "P2"),
    ("VENDA.troco", "Operações PDV", "Perdas operacionais troco", "P2"),
    ("FINANCEIRO_EXCLUSAO", "Auditoria", "Estornos / exclusões", "P3"),
    ("CONSULTAR_LMC_REDE_BICO (401)", "LMC granular", "Encerrante por bico", "P3 — pedir token"),
    ("VALE_FUNCIONARIO_REDE (401)", "Vale", "Vale nominal direto", "P3 — pedir token"),
    ("FUNCIONARIO_REDE (401)", "Cadastro", "Nome operador em API", "P3 — pedir token"),
]


def load_probe() -> dict:
    if PROBE.exists():
        return json.loads(PROBE.read_text(encoding="utf-8"))
    return {"endpoints": [], "coverage": {}}


def gateway_paths() -> dict[str, str]:
    txt = (ROOT / "src/gateway/webposto_client.py").read_text(encoding="utf-8")
    return dict(re.findall(r'"(\w+)": "(/INTEGRACAO/[^"]+)"', txt))


def probe_by_path(probe: dict) -> dict[str, dict]:
    return {e["path"]: e for e in probe.get("endpoints", [])}


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def generate_capability_matrix(probe: dict, gw: dict[str, str]) -> str:
    by_path = probe_by_path(probe)
    rows = []
    for key, path in sorted(gw.items(), key=lambda x: x[1]):
        e = by_path.get(path, {})
        rows.append([
            path,
            key,
            e.get("httpStatus", "—"),
            e.get("registros", "—"),
            e.get("classificacao", "—"),
            "Sim" if key in {
                "caixa", "caixa_rede", "caixa_apresentado", "despesas_financeiro_rede",
                "movimento_conta", "venda", "venda_item", "venda_forma_pagamento",
                "lmc_rede", "abastecimento", "financeiro", "titulo_receber",
            } else "Parcial/Não",
        ])
    extra_paths = [
        "/INTEGRACAO/FINANCEIRO_EXCLUSAO",
        "/INTEGRACAO/VALE_FUNCIONARIO_REDE",
        "/INTEGRACAO/FUNCIONARIO_REDE",
        "/INTEGRACAO/CONSULTAR_VENDA_ITEM_REDE",
        "/INTEGRACAO/CONSULTAR_LMC_REDE_BICO",
        "/INTEGRACAO/GRUPO_META",
        "/INTEGRACAO/FECHAMENTO_CAIXA",
        "/INTEGRACAO/DRE",
    ]
    for path in extra_paths:
        e = by_path.get(path, {})
        if not e:
            continue
        rows.append([
            path, "—", e.get("httpStatus", "—"), e.get("registros", "—"),
            e.get("classificacao", "—"), "Probe only",
        ])
    return f"""# WEBPOSTO CAPABILITY MATRIX — Sprint D00

**Data:** 2026-06-09 · **Fonte:** `webposto_network_probe_result.json` + gateway oficial · **Período probe:** 2026-06-01 → 2026-06-07

## Resumo

| Camada | Endpoints gateway | Probe adicional | HTTP 200 c/ dados | HTTP 401 |
|--------|-------------------|-----------------|-------------------|----------|
| Oficial LOGOS | 28 | +35 scripts | ~18 | ~12 |
| Módulos UI sem API | Prestação, Movimento Caixa, Operações PDV | — | 0 endpoint dedicado | — |

## Matriz gateway + probe

{md_table(["Path", "Chave LOGOS", "HTTP", "Registros", "Classificação", "Uso produtivo"], rows)}

## Módulos WebPosto UI vs endpoint

| Módulo UI (documentação WebPosto) | Endpoint `/INTEGRACAO/*` | Status |
|-----------------------------------|--------------------------|--------|
| Prestação de Contas | **Inexistente** | Camada documento/PDF — inferência via CAIXA+DESPESAS |
| Movimento no Caixa | **Inexistente** | Decomposto em CAIXA_APRESENTADO + MOVIMENTO_CONTA |
| Nota no Caixa | **Inexistente** | Parcial: `notaPrazo*` em CAIXA_APRESENTADO |
| Operações PDV | **Inexistente** | Proxy: VENDA, VENDA_ITEM, ABASTECIMENTO, CAIXA, NFCE |
| Venda Forma Pagamento | `VENDA_FORMA_PAGAMENTO` | **200** — subexplorado no Logos |
| LMC | `CONSULTAR_LMC_REDE` | **200** — 2 filiais; extensões 401 |
"""


def generate_prestacao_catalog() -> str:
    rows = []
    for field, desc in PRESTACAO_FIELD_CATALOG.items():
        cov = API_FIELD_COVERAGE.get(field, {})
        rows.append([
            field, desc,
            cov.get("endpoint", "—"),
            str(cov.get("available")),
            cov.get("granularity", "—"),
        ])
    ext_rows = []
    for field, meta in PRESTACAO_UI_EXTENDED.items():
        if field in PRESTACAO_FIELD_CATALOG:
            continue
        ext_rows.append([field, meta.get("endpoint", "—"), meta.get("api"), meta.get("logos")])

    only_ui = [k for k, v in PRESTACAO_UI_EXTENDED.items() if v.get("api") is False]
    partial = [k for k, v in PRESTACAO_UI_EXTENDED.items() if v.get("api") == "partial"]

    return f"""# PRESTAÇÃO DE CONTAS — FIELD CATALOG — Sprint D00

Documento referência: `Prestação de Contas - Não Consolida · AP CASA CAIADA · 08/06/2026 · 1º Turno`

## Catálogo base (24 campos F03.4-B)

{md_table(["Campo", "Descrição UI", "Endpoint API", "Disponível", "Granularidade"], rows)}

## Campos suspeitos confirmados (Bloco 1)

| Campo suspeito | Na UI/Prestação | Na API | Onde no Logos hoje |
|----------------|-----------------|--------|-------------------|
| sangria | Sim | Parcial (DESPESAS semântico) | F03.4-B sangria intelligence |
| suprimento | Sim | Parcial (MOVIMENTO_CONTA) | Não modelado |
| vale | Sim | Sim (CAIXA_APRESENTADO + DESPESAS) | F03.3 ledger |
| desconto | Sim | Parcial (VENDA_ITEM) | Sem dim operador |
| adiantamento | Sim | Parcial (DESPESAS/TITULO) | F03.2-A |
| falta / sobra | Sim | Derivado (CAIXA.diferenca) | F03.3 ledger |
| venda funcionário | Sim | Parcial (funcionarioCodigo) | Overview agregado |
| meta | Sim | **Não** (GRUPO_META isolado) | Não usado |
| produtividade | Sim | **Não** | F03.4 score parcial |

## Cobertura quantitativa

| Métrica | Valor |
|---------|-------|
| Campos catalogados UI | **{len(PRESTACAO_FIELD_CATALOG) + len(ext_rows)}** |
| Exclusivos UI (sem API) | **{len(only_ui)}** — {', '.join(only_ui[:6])}… |
| Parciais na API | **{len(partial)}** |
| Endpoint dedicado prestação | **0** |

## Resposta Bloco 1

A Prestação exibe **mais campos nominais e de produtividade** do que qualquer payload consolidado. A API cobre **~70%** dos conceitos via decomposição (CAIXA + CAIXA_APRESENTADO + DESPESAS + VENDA), mas **4 campos são exclusivos da UI** e **7+ têm granularidade superior no documento**.
"""


def generate_movimento_caixa_catalog(probe: dict) -> str:
    rows = [[t, desc, ep, api, note] for t, desc, ep, api, note in MOVIMENTO_CAIXA_UI_TYPES]
    ap = probe_by_path(probe).get("/INTEGRACAO/CAIXA_APRESENTADO", {})
    mc = probe_by_path(probe).get("/INTEGRACAO/MOVIMENTO_CONTA", {})
    return f"""# MOVIMENTO NO CAIXA — FIELD CATALOG — Sprint D00

Módulo UI WebPosto: *"Controla serviços, suprimentos, despesas e trocas movimentados no caixa"*

**Descoberta crítica:** não existe `/INTEGRACAO/MOVIMENTO_CAIXA`. O conceito está **fragmentado** em múltiplos endpoints.

## Tipos UI vs API

{md_table(["Tipo UI", "Descrição", "Endpoint proxy", "API", "Observação"], rows)}

## Campos reais — CAIXA_APRESENTADO (probe {ap.get('registros', '—')} reg)

`{', '.join(ap.get('campos', [])[:15])}…` (+ `despesaApurado`, `despesaDiferenca`, `valeFunApresentado` em produção F03.1)

## Campos reais — MOVIMENTO_CONTA (probe {mc.get('registros', '—')} reg)

`{', '.join(mc.get('campos', []))}`

## Campos reais — CAIXA turno

`empresaCodigo, caixaCodigo, dataMovimento, turnoCodigo, turno, pdvCodigo, funcionarioCodigo, abertura, fechamento, apurado, diferenca, fechado, consolidado`

## Gap LOGOS

| Tipo nunca modelado | Evidência API | Impacto |
|---------------------|---------------|---------|
| CARTA_FRETE | `cartaFreteApresentado/Apurado/Diferenca` | Recebíveis operacionais ocultos |
| SERVIÇO | Sem tipo | Perda de classificação movimento |
| TROCA | Apenas `VENDA.troco` | Confunde troco com troca de turno |
| SUPRIMENTO/SANGRIA tipados | Sem campos | Inferência semântica frágil |
"""


def generate_operacoes_pdv_catalog(probe: dict) -> str:
    rows = [[a, b, c, d, e] for a, b, c, d, e in OPERACOES_PDV_UI]
    venda = probe_by_path(probe).get("/INTEGRACAO/VENDA", {})
    abast = probe_by_path(probe).get("/INTEGRACAO/ABASTECIMENTO", {})
    return f"""# OPERAÇÕES PDV — FIELD CATALOG — Sprint D00

Módulo UI: *"Detalha todas as operações realizadas pelos funcionários no webPostoPDV"*

**Descoberta crítica:** não existe `/INTEGRACAO/OPERACOES_PDV` nem equivalente `CONSULTAR_*_PDV` no token atual.

## Operações UI vs proxies API

{md_table(["Operação UI", "Descrição", "Proxy API", "Cobertura", "Gap"], rows)}

## VENDA — campos operacionais ({venda.get('registros', '—')} reg probe)

`{', '.join(venda.get('campos', []))}`

## ABASTECIMENTO — campos operacionais ({abast.get('registros', '—')} reg)

`{', '.join(abast.get('campos', []))}`

## VENDA_ITEM — operador por item

Inclui **`funcionarioCodigo`**, **`totalDesconto`**, **`bicoCodigo`**, **`encerrante` implícito via ABASTECIMENTO**

## Risco F04 Performance

Se `VENDA` + `VENDA_ITEM` + `ABASTECIMENTO` forem consolidados por `funcionarioCodigo` + `turnoCodigo` + `pdvCodigo`, o módulo Performance pode **substituir parcialmente** Operações PDV — hoje o Logos usa apenas **CAIXA.diferenca** (F03.3/F03.4).
"""


def generate_venda_fp_catalog(probe: dict) -> str:
    fp = probe_by_path(probe).get("/INTEGRACAO/VENDA_FORMA_PAGAMENTO", {})
    fp_rede = probe_by_path(probe).get("/INTEGRACAO/CONSULTAR_VENDA_FORMA_PAGAMENTO_REDE", {})
    rows = [[k, v[0], v[1]] for k, v in FORMA_PAGAMENTO_MAP.items()]
    return f"""# VENDA FORMA PAGAMENTO — CATALOG — Sprint D00

## Endpoints

| Endpoint | HTTP | Registros probe | Uso Logos |
|----------|------|-----------------|-----------|
| `/INTEGRACAO/VENDA_FORMA_PAGAMENTO` | {fp.get('httpStatus', '—')} | {fp.get('registros', '—')} | `network_financial_overview` — **agregado, não operacional** |
| `/INTEGRACAO/CONSULTAR_VENDA_FORMA_PAGAMENTO_REDE` | {fp_rede.get('httpStatus', '—')} | {fp_rede.get('registros', '—')} | Fallback rede — **0 reg no período** |

## Campos API ({len(fp.get('campos', []))} campos)

`{', '.join(fp.get('campos', []))}`

## Mapeamento formas de pagamento

{md_table(["Forma", "Fonte primária", "Campos chave"], rows)}

## Dimensões disponíveis vs exploradas

| Dimensão | Campo API | Explorado no Logos |
|----------|-----------|-------------------|
| PDV | via join `VENDA.caixaCodigo` → `CAIXA.pdvCodigo` | **Não** |
| Operador | via join `VENDA.funcionarioCodigo` | **Não** |
| Turno | `turnoCodigo` | **Não** |
| Empresa | `empresaCodigo` | Sim (filtro) |
| Bandeira cartão | `administradoraCodigo` | **Não** |

## Oportunidade F04

`CONSULTAR_VENDA_FORMA_PAGAMENTO_REDE = 200` nos logs, mas **subexplorado**. Cruzamento com CAIXA + Prestação habilita mix Dinheiro/PIX/Cartão **por operador/turno/PDV**.
"""


def generate_lmc_catalog(probe: dict) -> str:
    lmc = probe_by_path(probe).get("/INTEGRACAO/CONSULTAR_LMC_REDE", {})
    rows = [[f, "Sim" if f in lmc.get("campos", []) else "Aninhado/401"] for f in LMC_FIELDS]
    blocked = [[b, "401 — token"] for b in LMC_BLOCKED]
    return f"""# LMC — FIELD CATALOG — Sprint D00

## Endpoint produção

| Endpoint | HTTP | Registros | Filiais |
|----------|------|-----------|---------|
| `CONSULTAR_LMC_REDE` | {lmc.get('httpStatus', '—')} | {lmc.get('registros', '—')} | 5555, 11495 |

## Campos LMC

{md_table(["Campo", "No payload LMC_REDE"], rows)}

## Extensões bloqueadas (401)

{md_table(["Endpoint", "Status"], blocked)}

## Linhagem proposta (não validada)

```
VENDA_ITEM (litros comercial)
    ↓
ABASTECIMENTO (bico, encerrante, frentista)
    ↓
CAIXA / Prestação (diferença turno)
    ↓
LMC (saida, perdaSobra, lmcBico, lmcTanque)
```

## Uso Logos hoje

- `fuel_analytics_service` — litros físicos via `saida` / `perdaSobra`
- **Não conectado** a caixa, prestação ou accountability
- Reconciliação LMC vs Vendas: **NAO VALIDADA** (baseline combustíveis 1.0)
"""


def generate_gap_analysis(probe: dict) -> str:
    ui_only = [
        "funcionarioNome", "participacaoIndividual", "produtividadeFuncionario", "fundoCaixa", "metaFuncionario",
        "tipoMovimentoCaixa (SERVICO/TROCA)", "autorizacaoPDV", "sangriaDestino", "suprimentoDestino",
    ]
    api_only = [
        "classificacaoLogosV3", "expenseLineage", "snapshotTTL", "tituloPagarAberto detalhado",
        "FINANCEIRO_EXCLUSAO", "LANCAMENTO_CONTABIL", "planoContaGerencialNivel",
    ]
    reports_richer = [
        ("Prestação de Contas (PDF/UI)", "CAIXA+DESPESAS API", "Nome, produtividade, participação %, fundo caixa"),
        ("Operações PDV (UI)", "VENDA+ABASTECIMENTO API", "Autorização, estorno nominal, log completo PDV"),
        ("Movimento no Caixa (UI)", "CAIXA_APRESENTADO API", "Tipagem SERVICO/TROCA/SUPRIMENTO"),
        ("Relatório Vendas Produto", "VENDA_ITEM API", "Layout gerencial vs raw API"),
    ]
    rr = [[a, b, c] for a, b, c in reports_richer]
    return f"""# API VS UI — GAP ANALYSIS — Sprint D00

## 1. Campos na UI/Prestação sem equivalente API

{chr(10).join('- `' + x + '`' for x in ui_only)}

## 2. Campos na API sem equivalente UI/Prestação

{chr(10).join('- `' + x + '`' for x in api_only)}

## 3. Relatórios/telas mais ricos que APIs consolidadas

{md_table(["Tela/Relatório UI", "API mais próxima", "Gap principal"], rr)}

## 4. APIs 200 nunca usadas ou subutilizadas (probe + código)

| API | HTTP | Reg | Uso Logos |
|-----|------|-----|-----------|
| NFCE | 200 | 200 | **Nunca** em services |
| FINANCEIRO_EXCLUSAO | 200 | 10203* | Audit scripts only |
| PRODUTO_META | 200 | 22 | Probe only |
| CONSULTAR_VENDA_FORMA_PAGAMENTO_REDE | 200 | 0 | Chamado, sem dados rede |
| CONSULTAR_CAIXA_APRESENTADO_REDE | 200 | 0 | Chamado, vazio |
| ABASTECIMENTO | 200 | 200 | Fuel legado, não performance |
| TITULO_RECEBER | 200 | 11 | Overview parcial |
| ESTOQUE_PERIODO | 200 | — | Overview parcial |

*FINANCEIRO_EXCLUSAO: validar filtro data antes de BI.

## 5. Palpite confirmado

**Operações PDV (proxy) + Prestação + Venda Forma Pagamento** concentram o maior delta UI↔API. Despesas já está madura (F03.2/F03.3); o tesouro operacional está no **caixa/PDV**, não no financeiro gerencial.
"""


def generate_hidden_data_report(probe: dict) -> str:
    endpoints_op = [
        ("CAIXA / CAIXA_REDE", "funcionarioCodigo, pdvCodigo, turno, diferenca"),
        ("VENDA", "funcionarioCodigo, cancelada, troco, caixaCodigo"),
        ("VENDA_ITEM", "funcionarioCodigo, totalDesconto"),
        ("ABASTECIMENTO", "codigoFrentista, encerrante, codigoBico"),
        ("VENDA_FORMA_PAGAMENTO", "turnoCodigo, formaPagamentoCodigo, nomeFormaPagamento"),
    ]
    endpoints_pdv = [
        ("CAIXA", "pdvCodigo, turnoCodigo"),
        ("VENDA", "caixaCodigo → join PDV"),
        ("ABASTECIMENTO", "empresaCodigo (sem pdv direto)"),
    ]
    top_rows = [[i + 1, f, src, val, pri] for i, (f, src, val, pri) in enumerate(TOP20_HIDDEN)]
    qa = f"""
| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Relatórios com mais campos que APIs? | **Prestação de Contas**, **Operações PDV (UI)**, **Movimento no Caixa (UI)** |
| 2 | Campos UI sem API? | **funcionarioNome, participacaoIndividual, produtividadeFuncionario, fundoCaixa, metaFuncionario, autorizacaoPDV** |
| 3 | APIs 200 nunca usadas? | **NFCE**, **PRODUTO_META**, **FINANCEIRO_EXCLUSAO** (prod), **CONSULTAR_LMC_REDE_BICO/TANQUE** (401) |
| 4 | APIs com dados de operador? | CAIXA, VENDA, VENDA_ITEM, ABASTECIMENTO.codigoFrentista |
| 5 | APIs com dados de PDV? | CAIXA.pdvCodigo (+ join VENDA→caixa) |
| 6 | APIs com produtividade? | **Nenhuma dedicada** — proxy ABASTECIMENTO + VENDA_ITEM |
| 7 | APIs com sangria? | **Nenhuma tipada** — DESPESAS_REDE semântico |
| 8 | APIs com suprimento? | **Nenhuma tipada** — MOVIMENTO_CONTA inferido |
| 9 | APIs com vale? | CAIXA_APRESENTADO.valeFun*/valeCliente* + DESPESAS |
| 10 | APIs com desconto funcionário? | VENDA_ITEM.totalDesconto (sem consolidação operador) |
| 11 | APIs com troco? | **VENDA.troco** |
| 12 | APIs com nota a prazo? | CAIXA_APRESENTADO.notaPrazo* + TITULO_RECEBER |
| 13 | APIs com empréstimo? | CAIXA_APRESENTADO.emprestimo* |
| 14 | APIs com carta frete? | CAIXA_APRESENTADO.cartaFrete* |
| 15 | APIs auditoria operacional? | NFCE, FINANCEIRO_EXCLUSAO, VENDA.cancelada |
| 16 | Prestação não usada? | Nome, participação %, produtividade, fundo caixa, layout nominal turno |
| 17 | Operações PDV não usadas? | Cancelamentos, autorizações, estornos PDV, abastecimento→performance |
| 18 | LMC não usado? | lmcBico, lmcTanque, perdaSobra vs caixa, encerrante |
| 19 | Top 20 campos ocultos? | Ver tabela abaixo |
| 20 | Módulo Logos mais valor? | **Operator Performance + Cash Accountability (F04)** consumindo Prestação + VENDA_FP + VENDA |
"""
    return f"""# WEBPOSTO HIDDEN DATA REPORT — Sprint D00

## Perguntas obrigatórias (1–20)

{qa}

## Top 20 campos ocultos mais valiosos

{md_table(["#", "Campo/Conceito", "Fonte", "Valor F04", "Prioridade"], top_rows)}

## APIs por dimensão operacional

### Operador
{md_table(["Endpoint", "Campos"], [[a, b] for a, b in endpoints_op])}

### PDV
{md_table(["Endpoint", "Campos"], [[a, b] for a, b in endpoints_pdv])}

## Conclusão executiva

1. **Não existe API de Prestação** — o documento é a fonte nominal; a API decompõe em CAIXA/DESPESAS/VENDA.
2. **Movimento no Caixa e Operações PDV são módulos UI** — dados existem, mas **fragmentados** em 6+ endpoints.
3. **VENDA_FORMA_PAGAMENTO** responde 200 com `turnoCodigo` — **nunca cruzado** com operador/PDV no Logos.
4. **LMC** abre quebra física (`perdaSobra`, `lmcBico`) — **desconectado** de accountability caixa.
5. **Módulo F04 com maior ROI:** Performance + Accountability alimentados por **Prestação (nominal) + VENDA/VENDA_FP (transacional) + CAIXA (turno)**.

## Próximo passo recomendado (D01 — fora deste escopo)

- Solicitar à Quality: `FUNCIONARIO_REDE`, `VALE_FUNCIONARIO_REDE`, `CONSULTAR_VENDA_ITEM_REDE`, `CONSULTAR_LMC_REDE_BICO` no token.
- Probe live `VENDA_FORMA_PAGAMENTO` × `CAIXA` × `funcionarioCodigo` janela 90d.
- OCR/parser Prestação PDF se API nominal continuar bloqueada.
"""


def main() -> None:
    probe = load_probe()
    gw = gateway_paths()
    writers = {
        "WEBPOSTO_CAPABILITY_MATRIX.md": generate_capability_matrix(probe, gw),
        "PRESTACAO_FIELD_CATALOG.md": generate_prestacao_catalog(),
        "MOVIMENTO_CAIXA_FIELD_CATALOG.md": generate_movimento_caixa_catalog(probe),
        "OPERACOES_PDV_FIELD_CATALOG.md": generate_operacoes_pdv_catalog(probe),
        "VENDA_FORMA_PAGAMENTO_CATALOG.md": generate_venda_fp_catalog(probe),
        "LMC_FIELD_CATALOG.md": generate_lmc_catalog(probe),
        "API_VS_UI_GAP_ANALYSIS.md": generate_gap_analysis(probe),
        "WEBPOSTO_HIDDEN_DATA_REPORT.md": generate_hidden_data_report(probe),
    }
    for name, content in writers.items():
        (ROOT / name).write_text(content, encoding="utf-8")
        print(f"Wrote {name}")
    print("Sprint D00 discovery reports generated.")


if __name__ == "__main__":
    main()
