# Sprint 44 & 45 — Sessão Executiva 30s e Sanidade Financeira

## Objetivo

Preparar o sistema para sessão executiva de 30 segundos com o Presidente, garantindo
integridade de dados na ingestão, tratativa de despesas pendentes sem quebrar a DRE,
e mecanismo de rateio de custos compartilhados.

## Sprint 44 — Preparação da Sessão Executiva 30s

### 1. Validação de Integridade de Paginação

**Serviço:** `PaginationIntegrityService`

Valida completude da coleta de dados paginados comparando:
- Total esperado vs coletado
- Status de terminação da paginação
- Alertas CRITICAL/WARNING/OK

```python
from src.services.pagination_integrity_service import PaginationIntegrityService

service = PaginationIntegrityService()
result = service.validate(
    endpoint="VENDA",
    empresa_codigo=11495,
    period_start="2026-07-01",
    period_end="2026-07-25",
    pagination_metadata=response_data,
    expected_total=100,
)
```

### 2. Tratativa de Despesas Pendentes

**Serviço:** `ExpensePendingService`

Agrupa despesas não classificadas em "PENDENTE_CLASSIFICACAO" sem quebrar o pipeline:

- Centro de custo virtual para despesas pendentes
- Alerta visual com contagem e valor total
- Bloqueio da DRE quando pendentes > 2% do faturamento
- Injeção no DRE como linha separada

```python
from src.services.expense_pending_service import ExpensePendingService

service = ExpensePendingService()
summary = service.group_pending_expenses(expenses, company_revenues)
dre_lines = service.inject_pending_center_in_dre(dre_lines, summary)
```

### 3. Síntese Executiva < 1s

**Serviço:** `ExecutiveSynthesisService`

Dashboard consolidado com cache de 5 minutos:

- Faturamento total e margem bruta
- Margem por litro (Combustíveis)
- Faturamento Conveniência
- Alertas críticos de caixa
- Status da DRE

**Endpoints:**
- `GET /api/v1/executive-synthesis/dashboard`
- `GET /api/v1/executive-synthesis/fuel-margin`
- `GET /api/v1/executive-synthesis/pending-expenses`
- `GET /api/v1/executive-synthesis/alerts-critical`

## Sprint 45 — Regras de Negócio e Sanidade Financeira

### 1. Enum de Classificação de Despesas

**Enum:** `ExpenseClassification`

Categorias configuráveis com mapeamento automático por plano de contas:

| Prefixo | Classificação |
|---------|---------------|
| 1.* | OPERACIONAL |
| 2.* | ADMINISTRATIVA |
| 3.* | PESSOAL |
| 4.* | TRIBUTARIA |
| 5.* | FINANCEIRA |
| Outros | PENDENTE |

### 2. Rateio de Custos Compartilhados

**Serviço:** `CostAllocationService`

Três métodos de rateio:

| Método | Descrição |
|--------|-----------|
| `PERCENTAGE` | % fixo por departamento (soma = 100%) |
| `REVENUE_PROPORTIONAL` | Proporcional ao faturamento |
| `FIXED_VALUE` | Valor fixo por departamento |

```python
from src.services.cost_allocation_service import CostAllocationService, AllocationRule

service = CostAllocationService()
rule = AllocationRule(
    rule_id="energia-001",
    management_account_code="ENERGIA",
    method="PERCENTAGE",
    allocations={"combustiveis": 50, "conveniencia": 30, "lubrificantes": 20},
    reviewer="diretor@posto.com",
    rationale="Rateio por área ocupada",
)
service.register_rule(rule)
result = service.allocate("exp-001", "ENERGIA", 1000.00)
```

### 3. Enum de Tipos de Produto

**Enum:** `ProductType`

Padronização dos tipos C/P/U do WebPosto com fallback seguro:

| Código | Tipo | Departamento |
|--------|------|--------------|
| C | Combustível | combustiveis |
| P | Produto | conveniencia |
| U | Utilidade | lubrificantes |
| ? | Desconhecido | None |

## Migração: FastAPI Lifespan

O `app.py` foi migrado de `@app.on_event("startup/shutdown")` para `lifespan` context manager,
eliminando os warnings de deprecação do FastAPI.

## Arquivos Criados

| Arquivo | Propósito |
|---------|-----------|
| `src/domain/enums/__init__.py` | Exports dos enums |
| `src/domain/enums/product_type.py` | ProductType enum |
| `src/domain/enums/expense_classification.py` | ExpenseClassification enum |
| `src/services/pagination_integrity_service.py` | Validação de paginação |
| `src/services/expense_pending_service.py` | Despesas pendentes |
| `src/services/cost_allocation_service.py` | Rateio dinâmico |
| `src/services/executive_synthesis_service.py` | Resumo executivo |
| `src/interfaces/http/routes/executive_synthesis.py` | Rotas de síntese |
| `tests/unit/test_pagination_integrity.py` | Testes |
| `tests/unit/test_expense_pending.py` | Testes |
| `tests/unit/test_cost_allocation.py` | Testes |

## Arquivos Alterados

| Arquivo | Mudança |
|---------|---------|
| `src/interfaces/http/app.py` | `on_event` → `lifespan` + router executive_synthesis |

## Validação

```powershell
python -m pytest tests/unit/test_pagination_integrity.py tests/unit/test_expense_pending.py tests/unit/test_cost_allocation.py -o addopts= -v
```

**Resultado:** 15/15 passed

## Próximos Passos

1. Sessão real de 30 segundos com Presidente
2. Classificar as 23 despesas pendentes via interface
3. Configurar regras de rateio aprovadas pela Diretoria
4. Monitorar integridade de paginação em produção
