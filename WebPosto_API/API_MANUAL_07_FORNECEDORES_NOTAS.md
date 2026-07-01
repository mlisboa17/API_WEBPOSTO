# API Manual — Sprint 07: Fornecedores e Notas de Entrada

**Projeto:** LOGOS SPACE / WebPosto API  
**Sprint:** 07 — Fornecedores / Notas de Entrada  
**Data:** 2026-06-17  
**Período de probe:** 2026-06-01 → 2026-06-07  
**Filiais testadas:** 11495, 5555  
**Referências:** Manuais 01–06, `API_DEPENDENCY_MAP.md`, probe ao vivo 2026-06-17

---

## 1. Visão geral

Sprint focada no mapeamento da **cadeia de compras e entrada de mercadorias**:

```text
FORNECEDOR
    ↓ fornecedorCodigo
PEDIDO_COMPRAS / PEDIDO_COMBUSTIVEL (bloqueados)
    ↓
NOTA_ENTRADA (bloqueada — inferida via TITULO_PAGAR)
    ↓ notaEntradaCodigo
TITULO_PAGAR
    ↓
PRODUTO / ESTOQUE
```

**Particularidade combustíveis:**

```text
LMC.lmcNota[]
    ├─ compraCodigo (9 únicos em 18 LMC)
    ├─ numeroNota
    ├─ volumeRecebido
    └─ tanqueCodigo → TANQUE → PRODUTO
```

---

## 2. Respostas às 9 perguntas da missão

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Como nasce uma compra? | ❌ Endpoint **PEDIDO_COMPRAS** bloqueado (401) |
| 2 | Como o produto entra no estoque? | ⚠️ Via **LMC.lmcNota** (combustíveis: **18/56** LMC com notas); **PRODUTO_ESTOQUE** não expõe origem |
| 3 | Como a nota se relaciona com fornecedor? | ✅ Via **TITULO_PAGAR**: **59/70** títulos com `notaEntradaCodigo` + **70/70** com `fornecedorCodigo` |
| 4 | Como a nota se relaciona com produto? | ⚠️ Combustíveis: **LMC.lmcNota** → **TANQUE** (3/3) → **PRODUTO** via `produtoCodigo` |
| 5 | Como a nota se relaciona com estoque? | ⚠️ **LMC.lmcNota** → **TANQUE** (`estoqueEscritural`); **PRODUTO_ESTOQUE** sem campo direto |
| 6 | Como a nota se relaciona com financeiro? | ✅ **NOTA_ENTRADA** ← **TITULO_PAGAR** (59/70) ← **FORNECEDOR** (70/70) |
| 7 | Como a nota se relaciona com LMC? | ✅ **LMC.lmcNota[]** contém `compraCodigo`, `numeroNota`, `volumeRecebido` |
| 8 | Quais joins são comprovados? | Ver seção 6 |
| 9 | Quais joins são negados? | Ver seção 7 |

---

## 3. Endpoint FORNECEDOR

### 3.1 Rota oficial

`GET /INTEGRACAO/FORNECEDOR`

### 3.2 Status HTTP

**200** — disponível

### 3.3 O que faz

Cadastro de fornecedores da rede (não segmentado por `empresaCodigo`).

### 3.4 Parâmetros

| Parâmetro | Obrigatório | Descrição |
|-----------|-------------|-----------|
| `CHAVE` | Sim | Chave |
| `dataInicial` / `dataFinal` | Sim | Período |

### 3.5 Response exemplo (anonimizado)

```json
{
  "resultados": [
    {
      "fornecedorCodigo": 128673,
      "razao": "GETNET S.A.",
      "fantasia": "GETNET S.A.",
      "cnpjCpf": "10.440.482/0001-54",
      "logradouro": "Alexandre Dumas, 1711",
      "bairro": "Chácara Santo Antônio",
      "cidade": "SAO PAULO",
      "uf": "SP",
      "telefone": null,
      "email": null,
      "fornecedorReferencia": "000001",
      "tipoPessoa": "J",
      "codigo": 128673
    }
  ]
}
```

**Campos confirmados (30):** `fornecedorCodigo`, `razao`, `fantasia`, `cnpjCpf`, `logradouro`, `tipoLogradouro`, `numero`, `bairro`, `cidade`, `telefone`, `celular`, `observacoes`, `codigoMunicipio`, `uf`, `email`, `ultimoUsuarioAlteracao`, `dataHoraAtualizacao`, `website`, `complemento`, `cep`, `pais`, `inscricaoEstadual`, `inscricaoMunicipal`, `contasFornecedor`, `fax`, `fornecedorReferencia`, `tipoPessoa`, `contatoEmail`, `fornecedorCodigoExterno`, `contatoWhatsapp`, `codigo`.

**Ausentes:** `empresaCodigo` (cadastro compartilhado rede).

### 3.6 Teste manual

```powershell
$env:WEBPOSTO_API_KEY = "SUA_CHAVE"
Invoke-WebRequest -Uri "https://web.qualityautomacao.com.br/INTEGRACAO/FORNECEDOR?CHAVE=$env:WEBPOSTO_API_KEY&dataInicial=2026-06-01&dataFinal=2026-06-07" -UseBasicParsing
```

### 3.7 Dependências

- `TITULO_PAGAR` — via `fornecedorCodigo` (**70/70** títulos, Sprint 05A)

### 3.8 Nível de confiança

**ALTO**

---

## 4. Endpoint NOTA_ENTRADA / NOTA_FISCAL_ENTRADA (bloqueados)

### 4.1 Rotas testadas

| Rota | HTTP | Observação |
|------|------|------------|
| `/INTEGRACAO/NOTA_ENTRADA` | **401** | Bloqueado |
| `/INTEGRACAO/NOTA_FISCAL_ENTRADA` | **401** | Bloqueado |

### 4.2 Relação inferida via TITULO_PAGAR

Embora os endpoints de nota estejam bloqueados, a relação **NOTA_ENTRADA → TITULO_PAGAR** é comprovada:

- **59/70** títulos a pagar (período 7d) têm campo `notaEntradaCodigo` preenchido
- `TITULO_PAGAR` expõe: `fornecedorCodigo`, `nomeFornecedor`, `notaEntradaCodigo`

**Exemplo:**

```json
{
  "tituloPagarCodigo": 3073237,
  "fornecedorCodigo": 496719,
  "notaEntradaCodigo": 3068754,
  "valorTotal": null
}
```

### 4.3 Observação

O WebPosto **registra internamente** as notas de entrada (códigos 3068754, 3068755, etc.), mas o endpoint de leitura não está disponível no token atual. Uso recomendado: inferir compras via **TITULO_PAGAR** + **FORNECEDOR**.

---

## 5. Endpoint PEDIDO_COMPRAS / PEDIDO_COMBUSTIVEL (bloqueados)

### 5.1 Status

| Endpoint | HTTP | Observação |
|----------|------|------------|
| `PEDIDO_COMPRAS` | **401** | Bloqueado |
| `PEDIDO_COMBUSTIVEL` | **401** | Bloqueado |
| `PEDIDO_COMBUSTIVEL/PEDIDO` | **500** | GET não suportado (provavelmente POST) |

### 5.2 Relação via LMC.lmcNota

O array **`lmcNota`** dentro de `LMC` (Sprint 06) expõe campo **`compraCodigo`**, que sugere relação com pedidos/compras:

**Evidência:**

- **18/56** registros LMC (11495, 7d) têm `lmcNota` preenchido
- **9** `compraCodigo` únicos
- Campos: `compraCodigo`, `numeroNota`, `dataEntrada`, `volumeRecebido`, `tanqueCodigo`

**Exemplo:**

```json
{
  "compraCodigo": 2146538,
  "numeroNota": "002888237",
  "dataEntrada": "2026-06-02",
  "volumeRecebido": 5000.0,
  "tanqueCodigo": 29882
}
```

---

## 6. Joins comprovados

| Relação | Campo de join | Evidência |
|---------|---------------|-----------|
| **FORNECEDOR → TITULO_PAGAR** | `fornecedorCodigo` | **70/70** títulos (Sprint 05A) |
| **NOTA_ENTRADA → TITULO_PAGAR** | `notaEntradaCodigo` | **59/70** títulos (probe 2026-06-17) |
| **LMC.lmcNota → TANQUE** | `tanqueCodigo` | **3/3** tanques únicos (probe 2026-06-17) |
| **LMC.lmcNota → (COMPRA)** | `compraCodigo` | **9** códigos únicos em 18 LMC — endpoint bloqueado |

---

## 7. Joins negados

| Relação | Motivo |
|---------|--------|
| **NOTA_FISCAL_ENTRADA** | HTTP 401 |
| **NOTA_ENTRADA** | HTTP 401 |
| **PEDIDO_COMPRAS** | HTTP 401 |
| **PEDIDO_COMBUSTIVEL** | HTTP 401 |
| **PEDIDO_COMBUSTIVEL/PEDIDO** | HTTP 500 (GET não suportado) |
| **PRODUTO_ESTOQUE ← NOTA_ENTRADA** | Campo `notaEntradaCodigo` ausente em `PRODUTO_ESTOQUE` |
| **FORNECEDOR ← EMPRESAS** | Campo `empresaCodigo` ausente em `FORNECEDOR` (cadastro compartilhado rede) |
| **MOVIMENTO_CONTA → TITULO_PAGAR** | `documentoOrigemCodigo` ≠ `tituloPagarCodigo` (Sprint 05B.1) |

---

## 8. Campos críticos — matriz

| Campo | FORNECEDOR | TITULO_PAGAR | LMC.lmcNota | PRODUTO_ESTOQUE |
|-------|:----------:|:------------:|:-----------:|:---------------:|
| `fornecedorCodigo` | ✅ | ✅ | — | — |
| `notaEntradaCodigo` | — | ✅ (59/70) | — | ❌ |
| `compraCodigo` | — | — | ✅ (18/56) | — |
| `numeroNota` | — | — | ✅ | — |
| `tanqueCodigo` | — | — | ✅ | — |
| `volumeRecebido` | — | — | ✅ | — |
| `empresaCodigo` | ❌ | ✅ | — | ✅ |
| `cnpjCpf` | ✅ | — | — | — |

---

## 9. Impacto no LOGOS

| Módulo LOGOS | Endpoints WebPosto | Observação |
|--------------|-------------------|------------|
| **Supplier Intelligence** | `FORNECEDOR` + `TITULO_PAGAR` | Via join `fornecedorCodigo` |
| **Compras (módulo futuro)** | `NOTA_ENTRADA` (401 — aguarda token) | Base para `fact_compra` no DW |
| **Governança combustíveis** | `LMC.lmcNota` | Notas de entrada de combustível (18/56 LMC) |
| **Financeiro** | `TITULO_PAGAR.notaEntradaCodigo` | 59/70 títulos vinculados a notas |

**Bloqueio atual:** módulo de compras detalhadas aguarda liberação de token para `NOTA_ENTRADA` / `PEDIDO_COMPRAS`.

---

## 10. Cadeia comprovada FORNECEDOR → FINANCEIRO

```text
FORNECEDOR
    ↓ fornecedorCodigo (70/70)
TITULO_PAGAR
    ↓ notaEntradaCodigo (59/70)
(NOTA_ENTRADA — bloqueada)
```

**Cadeia combustíveis:**

```text
(PEDIDO/COMPRA — bloqueado)
    ↓ compraCodigo
LMC.lmcNota (18/56)
    ↓ tanqueCodigo (3/3)
TANQUE
    ↓ produtoCodigo
PRODUTO
```

---

## 11. Nível de confiança

| Recurso | Classificação |
|---------|---------------|
| `FORNECEDOR` | **ALTO** (200, cadastro rede) |
| `TITULO_PAGAR → NOTA_ENTRADA` | **ALTO** (join indireto 59/70) |
| `LMC.lmcNota` | **MÉDIO** (18/56 LMC, combustíveis) |
| `NOTA_ENTRADA` | **BLOQUEADO** (401) |
| `PEDIDO_COMPRAS` | **BLOQUEADO** (401) |
| `PEDIDO_COMBUSTIVEL` | **BLOQUEADO** (401/500) |

---

## 12. Próxima Sprint

**API-MANUAL-08 — DESPESAS / CENTRO DE CUSTO**

Endpoints prováveis: `DESPESAS_REDE`, `CENTRO_CUSTO`, classificação de despesas operacionais.

---

*Volumes e identificadores anonimizados onde aplicável.*
