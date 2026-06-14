# IA-8 — Financial Fix Proposal Report

> **Não implementado** — aguardando aprovação pós-evidência.

## Classificação da causa

| Classe | Aplica? | Detalhe |
|--------|---------|---------|
| A) Frontend | ❌ | Apenas exibe mensagem do backend |
| B) Backend | ✅ | Circuit breaker `src/gateway/webposto_client.py` |
| C) Gateway Onda 2 | ❌ | Não participa do fluxo financeiro |
| D) Snapshot | ⚠️ Parcial | Snapshot financeiro existe mas **vazio**; telas não usam snapshot-first |
| E) Configuração | ✅ | `circuit_block_seconds=3600`, estado in-memory |

## Causa raiz

O endpoint `/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE` está com **circuit breaker aberto** (tipo `CIRCUIT_OPEN`), provavelmente após falhas ou 401 anteriores. Permissão atual é `true`, mas o breaker impede nova tentativa live por até **1 hora**.

Receitas e Despesas compartilham este upstream → **ambas quebradas pelo mesmo motivo**.

## Correções mínimas propostas (ordem de risco)

### 1. Operacional imediata (zero código)

- **Reiniciar o processo API** → zera circuit breaker in-memory
- Validar credencial WebPosto e resposta live do endpoint
- Aguardar expiração natural (3600s)

**Risco:** baixo | **Escopo:** ops

### 2. Resiliência backend (correção mínima de código)

- Em `call_endpoint()`, se `permissions[endpoint_key]==true` e circuito aberto por 401 antigo, **permitir probe** ou **auto-clear** após TTL parcial
- Expor `POST /v1/circuit-breaker/{key}/reset` (admin) espelhando padrão de observabilidade

**Risco:** médio | **Escopo:** `src/gateway/webposto_client.py`

### 3. Snapshot-first nas telas financeiras (alinhamento arquitetural)

- Receitas/Despesas carregarem `/api/v1/financial/snapshot` antes do live (padrão F04+)
- Popular snapshot via job homologado quando live indisponível
- **Não inventar dados** — usar snapshots existentes (`snapshots/expense_*`)

**Risco:** médio-alto | **Escopo:** frontend `app.js` + snapshot service

### 4. UX de erro (opcional)

- Diferenciar `CIRCUIT_OPEN` de erro genérico: "Integração temporariamente pausada — retry em X min"

**Risco:** baixo | **Escopo:** frontend apenas

## O que NÃO fazer

- ❌ Mocks ou dados sintéticos
- ❌ Remover circuit breaker
- ❌ Alterar F03–F07
- ❌ Ativar `allow_live=True` global na Onda 2 sem governança

## Recomendação

**Curto prazo:** reiniciar API + validar live WebPosto (opção 1).  
**Médio prazo:** opção 2 + opção 3 para paridade com motores snapshot-first.

## Parecer IA-8

Correção segura imediata = **operacional**. Correção estrutural = **snapshot-first + reset de circuito** sem tocar motores F03–F07.
