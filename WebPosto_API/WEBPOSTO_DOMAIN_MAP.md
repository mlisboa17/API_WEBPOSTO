# WebPosto Domain Map — Cadeias Comprovadas

**Projeto:** LOGOS SPACE / WebPosto API  
**Atualizado:** 2026-06-17 (Sprint 07)  
**Regra:** apenas relações **comprovadas** com evidência de campo de join em probe ao vivo

---

## Cadeia operacional completa (comprovada)

```text
FORNECEDORES
    ↓ fornecedorCodigo (70/70)
COMPRAS
    ↓ notaEntradaCodigo (59/70 — endpoint bloqueado)
NOTAS
    ↓ (inferido via TITULO_PAGAR)
    ├─ Combustíveis: LMC.lmcNota → TANQUE
    └─ Geral: sem endpoint disponível
PRODUTOS
    ↓ produtoCodigo
ESTOQUE
    ├─ PRODUTO_ESTOQUE (saldo)
    └─ TANQUE (combustíveis, estoqueEscritural)
VENDAS
    ↓ vendaCodigo + clienteCodigo
    ├─ VENDA → VENDA_ITEM → PRODUTO
    ├─ VENDA → VENDA_FORMA_PAGAMENTO
    └─ ABASTECIMENTO → VENDA_ITEM (pista)
FINANCEIRO
    ├─ TITULO_RECEBER ← CLIENTE + VENDA
    ├─ TITULO_PAGAR ← FORNECEDOR + NOTA_ENTRADA
    ├─ MOVIMENTO_CONTA ← TRANSFERENCIA_BANCARIA
    └─ CAIXA ← VENDA
COMBUSTÍVEIS
    ├─ LMC (lmcTanque, lmcBico, lmcNota)
    ├─ TANQUE → PRODUTO
    └─ ABASTECIMENTO → VENDA_ITEM
```

---

## 1. FORNECEDORES

### Endpoint

- **`FORNECEDOR`** — HTTP 200 (200 registros, cadastro rede)

### Join comprovado

```text
FORNECEDOR --fornecedorCodigo--> TITULO_PAGAR
```

**Evidência:** `fornecedorCodigo` em **70/70** títulos a pagar (Sprint 05A, 07).

### Observação

- Campo `empresaCodigo` **ausente** — cadastro compartilhado rede
- Campos principais: `fornecedorCodigo`, `razao`, `fantasia`, `cnpjCpf`

---

## 2. COMPRAS

### Endpoints

| Endpoint | Status | Observação |
|----------|--------|------------|
| `PEDIDO_COMPRAS` | ❌ 401 | Bloqueado |
| `PEDIDO_COMBUSTIVEL` | ❌ 401 | Bloqueado |
| `PEDIDO_COMBUSTIVEL/PEDIDO` | ❌ 500 | GET não suportado |

### Join comprovado (indireto — combustíveis)

```text
LMC.lmcNota --compraCodigo--> (PEDIDO/COMPRA — não acessível)
```

**Evidência:** campo `compraCodigo` em **18/56** LMC com notas (Sprint 07); **9** códigos únicos.

---

## 3. NOTAS

### Endpoints

| Endpoint | Status | Observação |
|----------|--------|------------|
| `NOTA_ENTRADA` | ❌ 401 | Bloqueado |
| `NOTA_FISCAL_ENTRADA` | ❌ 401 | Bloqueado |

### Join comprovado (indireto via TITULO_PAGAR)

```text
NOTA_ENTRADA --notaEntradaCodigo--> TITULO_PAGAR
```

**Evidência:** `notaEntradaCodigo` preenchido em **59/70** títulos a pagar (Sprint 07).

### Join comprovado (combustíveis via LMC)

```text
LMC.lmcNota --numeroNota+compraCodigo--> (NOTA_ENTRADA combustível)
LMC.lmcNota --tanqueCodigo--> TANQUE
```

**Evidência:** **18/56** LMC com `lmcNota` preenchido; **3/3** `tanqueCodigo` únicos presentes em `TANQUE` (Sprint 07).

---

## 4. PRODUTOS

### Endpoints

- **`PRODUTO`** — HTTP 200 (catálogo geral)
- **`PRODUTO_EMPRESA`** — HTTP 200 (preço/custo por filial)

### Joins comprovados

```text
PRODUTO --produtoCodigo--> VENDA_ITEM
PRODUTO --produtoCodigo--> PRODUTO_ESTOQUE
PRODUTO --produtoCodigo--> TANQUE
PRODUTO --produtoCodigo--> LMC
PRODUTO --produtoCodigo--> ABASTECIMENTO (codigoProduto)
```

**Evidência:**

- `VENDA_ITEM.produtoCodigo` (Sprint 04)
- `PRODUTO_ESTOQUE.produtoCodigo` — lookup **5/5** retorna 200 (Sprint 06)
- `TANQUE.produtoCodigo` — **3/4** códigos únicos no catálogo (Sprint 06)
- `LMC.produtoCodigo[]` — **6** códigos encontrados (Sprint 06)
- `ABASTECIMENTO.codigoProduto` (Sprint 04)

---

## 5. ESTOQUE

### Endpoints

- **`PRODUTO_ESTOQUE`** — HTTP 200 (com `empresaCodigo`)
- **`TANQUE`** — HTTP 200 (combustíveis)
- **`ESTOQUE`** — HTTP 200 (cadastro de depósitos)
- **`ESTOQUE_PERIODO`** — HTTP 200 (movimentação mensal)

### Joins comprovados

```text
PRODUTO_ESTOQUE --produtoCodigo--> PRODUTO
PRODUTO_ESTOQUE --empresaCodigo--> EMPRESAS
TANQUE --produtoCodigo--> PRODUTO
```

**Evidência:**

- **4973/4973** registros `PRODUTO_ESTOQUE` com `empresaCodigo` (Sprint 06)
- **6/6** tanques com `produtoCodigo` (Sprint 06)

### Joins negados

```text
PRODUTO_ESTOQUE --notaEntradaCodigo-->   ❌
```

Campo `notaEntradaCodigo` **ausente** em `PRODUTO_ESTOQUE`.

---

## 6. VENDAS

### Endpoints

- **`VENDA`** — HTTP 200 (cabeçalho)
- **`VENDA_ITEM`** — HTTP 200 (itens)
- **`VENDA_FORMA_PAGAMENTO`** — HTTP 200 (pagamentos)
- **`ABASTECIMENTO`** — HTTP 200 (pista)

### Joins comprovados

```text
CLIENTE --clienteCodigo--> VENDA
VENDA --vendaCodigo--> VENDA_ITEM
VENDA --vendaCodigo--> VENDA_FORMA_PAGAMENTO
VENDA --vendaCodigo--> TITULO_RECEBER
VENDA --caixaCodigo--> CAIXA
PRODUTO --produtoCodigo--> VENDA_ITEM
ABASTECIMENTO --vendaItemCodigo--> VENDA_ITEM
ABASTECIMENTO --codigoProduto--> PRODUTO
```

**Evidência:**

- `VENDA.clienteCodigo` (Sprint 04)
- `VENDA.vendaCodigo` → `VENDA_ITEM` / `VENDA_FORMA_PAGAMENTO` / `TITULO_RECEBER` (Sprint 04)
- `VENDA.caixaCodigo` → `CAIXA` (Sprint 05B.1)
- `VENDA_ITEM.produtoCodigo` (Sprint 04)
- `ABASTECIMENTO.vendaItemCodigo` → `VENDA_ITEM` (Sprint 04)

---

## 7. FINANCEIRO

### Endpoints

- **`TITULO_RECEBER`** — HTTP 200 (contas a receber)
- **`TITULO_PAGAR`** — HTTP 200 (contas a pagar)
- **`MOVIMENTO_CONTA`** — HTTP 200 (extrato bancário)
- **`CAIXA`** — HTTP 200 (turnos de caixa)
- **`CONTA`** — HTTP 200 (cadastro de contas)
- **`PLANO_CONTA_GERENCIAL`** — HTTP 200 (plano de contas)

### Joins comprovados

```text
CLIENTE --clienteCodigo--> TITULO_RECEBER
VENDA --vendaCodigo--> TITULO_RECEBER
FORNECEDOR --fornecedorCodigo--> TITULO_PAGAR
NOTA_ENTRADA --notaEntradaCodigo--> TITULO_PAGAR
PLANO_CONTA_GERENCIAL --planoContaGerencialCodigo--> TITULO_PAGAR
PLANO_CONTA_GERENCIAL --planoContaGerencialCodigo--> MOVIMENTO_CONTA
CONTA --contaCodigo--> MOVIMENTO_CONTA
TRANSFERENCIA_BANCARIA --transferenciaBancariaCodigo--> MOVIMENTO_CONTA
TRANSFERENCIA_BANCARIA --vendaCodigo--> VENDA
TRANSFERENCIA_BANCARIA --caixaCodigo--> CAIXA
CAIXA_APRESENTADO --caixaCodigo--> CAIXA
CARTAO --vendaCodigo--> VENDA_FORMA_PAGAMENTO
```

**Evidência:**

- `TITULO_RECEBER.clienteCodigo` — **11/11** (Sprint 05A)
- `TITULO_RECEBER.vendaCodigo` — **11/11** (Sprint 05A)
- `TITULO_PAGAR.fornecedorCodigo` — **70/70** (Sprint 05A)
- `TITULO_PAGAR.notaEntradaCodigo` — **59/70** (Sprint 07)
- `TITULO_PAGAR.planoContaGerencialCodigo` — **55/70** (Sprint 05B.2)
- `MOVIMENTO_CONTA.planoContaGerencialCodigo` — **1000/1000** (Sprint 05B.2)
- `MOVIMENTO_CONTA.contaCodigo` — **200/200** (Sprint 05B.1)
- `TRANSFERENCIA_BANCARIA.transferenciaBancariaCodigo` — **26/200** (Sprint 05B.2)
- `CAIXA_APRESENTADO.caixaCodigo` — **21/21** (Sprint 05B.2)
- `CARTAO.vendaCodigo` — **73/200** (Sprint 05B.2)

### Joins negados

```text
MOVIMENTO_CONTA --documentoOrigemCodigo=tituloPagarCodigo-->   ❌
```

**3/13** movimentos (5555) com `tipoDocumentoOrigem=TITULO_PAGAR`, mas `documentoOrigemCodigo` **≠** `tituloPagarCodigo` (Sprint 05B.1, 07).

---

## 8. COMBUSTÍVEIS

### Endpoints

- **`LMC`** / **`CONSULTAR_LMC_REDE`** — HTTP 200 (livro de combustíveis)
- **`TANQUE`** — HTTP 200 (tanques físicos)
- **`ABASTECIMENTO`** — HTTP 200 (vendas na pista)

### Joins comprovados

```text
TANQUE --produtoCodigo--> PRODUTO
LMC --lmcTanque.tanqueCodigo--> TANQUE
LMC --produtoCodigo--> PRODUTO
LMC.lmcBico --bicoCodigo--> ABASTECIMENTO
LMC.lmcNota --tanqueCodigo--> TANQUE
```

**Evidência:**

- `TANQUE.produtoCodigo` — **3/4** códigos únicos no catálogo (Sprint 06)
- `LMC.lmcTanque.tanqueCodigo` — **4/6** (Sprint 06)
- `LMC.produtoCodigo[]` — **6** códigos (Sprint 06)
- `LMC.lmcBico.bicoCodigo` — **13/20** overlap com `ABASTECIMENTO.codigoBico` (Sprint 06)
- `LMC.lmcNota.tanqueCodigo` — **3/3** (Sprint 07)

### Joins negados

```text
TANQUE --tanqueCodigo--> ABASTECIMENTO   ❌
PEDIDO_COMBUSTIVEL --> FORNECEDOR | PRODUTO | NOTA_ENTRADA   ❌
```

- Campo `tanqueCodigo` **ausente** em `ABASTECIMENTO` (Sprint 06)
- Endpoints de pedido bloqueados (Sprint 07)

---

## 9. Fundamentos transversais

```text
EMPRESAS --empresaCodigo--> VENDA | VENDA_ITEM | TITULO_RECEBER | TITULO_PAGAR | MOVIMENTO_CONTA | CAIXA | CONTA | PRODUTO_ESTOQUE
```

**Evidência:** campo `empresaCodigo` presente em todos os payloads transacionais.

---

## 10. Bloqueios conhecidos

| Endpoint | Status | Impacto |
|----------|--------|---------|
| `NOTA_ENTRADA` / `NOTA_FISCAL_ENTRADA` | 401 | Módulo compras limitado a join indireto via `TITULO_PAGAR.notaEntradaCodigo` |
| `PEDIDO_COMPRAS` | 401 | Sem origem de pedidos |
| `PEDIDO_COMBUSTIVEL` | 401/500 | Pedidos de combustível não disponíveis para leitura |
| `PRODUTO_LMC` | 401 | Cadastro LMC bloqueado |
| Endpoints `_REDE` | 401 (maioria) | Acesso via endpoint por filial + loop |
| `MOVIMENTO_CONTA` join direto TITULO_PAGAR | Códigos não batem | Relação operacional, não técnica |

---

## 11. Referências

- `API_DEPENDENCY_MAP.md` — Mapa detalhado de joins
- `API_MANUAL_INDEX.md` — Índice de sprints
- Sprints 01–07
- Probes: 2026-06-17, período 2026-06-01 → 2026-06-07

---

*Apenas relações comprovadas por campo de join em probe ao vivo ou sprint anterior documentada.*
