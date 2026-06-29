# Database Mapping
## Mapeamento de Banco de Dados - LOGOS SPACE

**Versão:** 1.0
**Data:** 2026-06-28
**Status:** Ativo
**Sprint:** DOCS-02

---

## 🗄️ Visão Geral

```
┌─────────────────────────────────────────────────────────────────┐
│                     SUPABASE (PostgreSQL)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐  │
│  │   logos_dw          │  │   governance                  │  │
│  │   (Data Warehouse)  │  │   (Sprint 25A)                │  │
│  ├─────────────────────┤  ├─────────────────────────────────┤  │
│  │ • dim_cliente       │  │ • audit_log                   │  │
│  │ • dim_empresa       │  │ • approval_requests           │  │
│  │ • dim_produto       │  │ • security_events             │  │
│  │ • fact_receber      │  │ • copilot_audit               │  │
│  │ • fact_venda        │  │ • user_roles                  │  │
│  │ • fact_venda_item   │  │                               │  │
│  └─────────────────────┘  └─────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐  │
│  │   public            │  │   auth (Supabase)               │  │
│  ├─────────────────────┤  ├─────────────────────────────────┤  │
│  │ • tenants           │  │ • users                         │  │
│  │ • snapshots         │  │ • sessions                      │  │
│  │ • views (expostas)  │  │ • [Supabase Auth]               │  │
│  └─────────────────────┘  └─────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Schema: logos_dw

### Data Warehouse - Tabelas Dimensionais

#### dim_cliente

| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `cliente_id` | BIGINT PK | ID único do cliente | 12345 |
| `codigo` | VARCHAR | Código do cliente na origem | "CLI001" |
| `nome` | VARCHAR | Nome do cliente | "POSTO VIP" |
| `cnpj` | VARCHAR | CNPJ (mascarado) | "03.008.754/****-**" |
| `tenant_id` | VARCHAR | Tenant (RLS) | "POSTO_VIP" |
| `created_at` | TIMESTAMPTZ | Data de criação | 2026-06-01 |

#### dim_empresa

| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `empresa_id` | BIGINT PK | ID único | 1 |
| `empresa_codigo` | INTEGER | Código WebPosto | 11495 |
| `cod_web` | INTEGER | Código Web | 10 |
| `nome_fantasia` | VARCHAR | Nome fantasia | "POSTO VIP" |
| `cnpj` | VARCHAR | CNPJ completo | "03.008.754/0001-86" |
| `tenant_id` | VARCHAR | Tenant (RLS) | "POSTO_VIP" |
| `created_at` | TIMESTAMPTZ | Data de criação | 2026-06-01 |

**RLS Policy:**
```sql
CREATE POLICY tenant_isolation ON dim_empresa
    FOR SELECT USING (tenant_id = current_setting('app.current_tenant'));
```

#### dim_produto

| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `produto_id` | BIGINT PK | ID único | 456 |
| `codigo` | VARCHAR | Código do produto | "GASOLINA" |
| `descricao` | VARCHAR | Descrição | "Gasolina Comum" |
| `categoria` | VARCHAR | Categoria | "COMBUSTIVEL" |
| `unidade` | VARCHAR | Unidade de medida | "LITRO" |
| `tenant_id` | VARCHAR | Tenant (RLS) | "POSTO_VIP" |
| `created_at` | TIMESTAMPTZ | Data de criação | 2026-06-01 |

### Data Warehouse - Tabelas Fato

#### fact_venda

| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `venda_id` | BIGINT PK | ID único | 789012 |
| `data` | DATE | Data da venda | 2026-06-28 |
| `hora` | TIME | Hora da venda | 14:30:00 |
| `empresa_codigo` | INTEGER | Código da filial | 11495 |
| `cliente_id` | BIGINT FK | Referência dim_cliente | 12345 |
| `produto_id` | BIGINT FK | Referência dim_produto | 456 |
| `quantidade` | DECIMAL | Quantidade vendida | 42.50 |
| `valor_unitario` | DECIMAL | Preço unitário | 5.899 |
| `valor_total` | DECIMAL | Valor total | 250.71 |
| `status` | VARCHAR | Status (OK/CANCELADO) | "OK" |
| `tenant_id` | VARCHAR | Tenant (RLS) | "POSTO_VIP" |
| `created_at` | TIMESTAMPTZ | Data de criação no DW | 2026-06-28 15:00:00 |

#### fact_venda_item

| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `item_id` | BIGINT PK | ID único | 1234567 |
| `venda_id` | BIGINT FK | Referência fact_venda | 789012 |
| `produto_id` | BIGINT FK | Referência dim_produto | 456 |
| `quantidade` | DECIMAL | Quantidade | 42.50 |
| `valor_unitario` | DECIMAL | Preço | 5.899 |
| `valor_total` | DECIMAL | Total do item | 250.71 |
| `tenant_id` | VARCHAR | Tenant (RLS) | "POSTO_VIP" |

#### fact_receber

| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `receber_id` | BIGINT PK | ID único | 987654 |
| `data_emissao` | DATE | Data de emissão | 2026-06-20 |
| `data_vencimento` | DATE | Data de vencimento | 2026-07-20 |
| `data_pagamento` | DATE | Data de pagamento (nullable) | 2026-07-15 |
| `empresa_codigo` | INTEGER | Código da filial | 11495 |
| `cliente_id` | BIGINT FK | Referência dim_cliente | 12345 |
| `valor` | DECIMAL | Valor original | 1000.00 |
| `valor_pago` | DECIMAL | Valor pago (nullable) | 1000.00 |
| `status` | VARCHAR | Status (PENDENTE/PAGO/VENCIDO) | "PAGO" |
| `tenant_id` | VARCHAR | Tenant (RLS) | "POSTO_VIP" |
| `created_at` | TIMESTAMPTZ | Data de criação no DW | 2026-06-28 |

---

## Schema: governance

### Sprint 25A - Advanced Governance

#### audit_log

| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `id` | BIGSERIAL PK | ID único | 1 |
| `tenant_id` | VARCHAR | Tenant (RLS) | "POSTO_VIP" |
| `user_id` | VARCHAR | ID do usuário | "user_123" |
| `user_email` | VARCHAR | Email do usuário | "user@posto.com" |
| `action` | VARCHAR | Ação (LOGIN/CREATE/UPDATE/DELETE) | "CREATE" |
| `entity_type` | VARCHAR | Tipo de entidade | "FINANCIAL_CONFIG" |
| `entity_id` | VARCHAR | ID da entidade | "config_001" |
| `description` | TEXT | Descrição | "Configuração criada" |
| `metadata` | JSONB | Dados adicionais | `{}` |
| `ip_address` | INET | IP do request | 192.168.1.1 |
| `user_agent` | TEXT | User agent | "Mozilla/5.0..." |
| `request_method` | VARCHAR | Método HTTP | "POST" |
| `request_path` | TEXT | Path da request | "/v1/config" |
| `status` | VARCHAR | Status (SUCCESS/FAILURE/PENDING) | "SUCCESS" |
| `error_message` | TEXT | Mensagem de erro (se houver) | null |
| `created_at` | TIMESTAMPTZ | Timestamp | 2026-06-28 10:00:00 |

**Índices:**
```sql
CREATE INDEX idx_audit_tenant ON audit_log(tenant_id);
CREATE INDEX idx_audit_action ON audit_log(action);
CREATE INDEX idx_audit_created ON audit_log(created_at DESC);
```

#### user_roles

| Coluna | Tipo | Descrição | Exemplo |
|--------|------|-----------|---------|
| `id` | BIGSERIAL PK | ID único | 1 |
| `tenant_id` | VARCHAR | Tenant (RLS) | "POSTO_VIP" |
| `user_id` | VARCHAR | ID do usuário | "user_123" |
| `user_email` | VARCHAR | Email do usuário | "user@posto.com" |
| `role` | VARCHAR | Role (OWNER/ADMIN/MANAGER/FINANCE/OPERATIONS/VIEWER) | "FINANCE" |
| `custom_permissions` | JSONB | Permissões customizadas | `[]` |
| `is_active` | BOOLEAN | Ativo | true |
| `created_at` | TIMESTAMPTZ | Data de criação | 2026-06-28 |
| `updated_at` | TIMESTAMPTZ | Data de atualização | 2026-06-28 |

---

## Schema: public

### Views Expostas

Views criadas para permitir acesso via RLS ao Supabase.

#### vw_empresas

```sql
CREATE VIEW public.vw_empresas AS
SELECT * FROM logos_dw.dim_empresa;

-- Grant
GRANT SELECT ON public.vw_empresas TO anon, authenticated;
```

---

## 🔗 Relacionamentos

```
dim_empresa (1) ───< (N) fact_venda
    │                    │
    │                    ├──> dim_cliente
    │                    └──> dim_produto
    │
    ├──< (N) fact_receber
    │       └──> dim_cliente
    │
    └──< (N) fact_venda_item
            ├──> fact_venda
            └──> dim_produto
```

---

## 🔄 ETL - Fluxo de Dados

```
WebPosto API
    │
    ├──→ /INTEGRACAO/VENDA ──────┐
    ├──→ /INTEGRACAO/VENDA_ITEM │
    ├──→ /INTEGRACAO/EMPRESAS    │
    ├──→ /INTEGRACAO/PRODUTO     ├──→ ETL Worker ──→ logos_dw
    ├──→ /INTEGRACAO/CLIENTE    │
    └──→ /INTEGRACAO/TITULO_     │
         RECEBER/PAGAR          │
                                 │
    (Quality Automação)         │
                                 ↓
                          ┌──────────────┐
                          │  Supabase    │
                          │  logos_dw    │
                          └──────────────┘
```

---

## 📊 Mapeamento WebPosto → DW

| Endpoint WebPosto | Tabela DW | Frequência ETL |
|-------------------|-----------|----------------|
| `/INTEGRACAO/VENDA` | `fact_venda` | Diária |
| `/INTEGRACAO/VENDA_ITEM` | `fact_venda_item` | Diária |
| `/INTEGRACAO/TITULO_RECEBER` | `fact_receber` | Diária |
| `/INTEGRACAO/EMPRESAS` | `dim_empresa` | Semanal |
| `/INTEGRACAO/PRODUTO` | `dim_produto` | Semanal |
| `/INTEGRACAO/CLIENTE` | `dim_cliente` | Semanal |

---

## 🛡️ Segurança

### Row Level Security (RLS)

Todas as tabelas possuem RLS ativo:

```sql
-- Exemplo: fact_venda
ALTER TABLE logos_dw.fact_venda ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON logos_dw.fact_venda
    FOR ALL USING (tenant_id = current_setting('app.current_tenant'));
```

### Service Role

Backend usa `service_role` key para bypass RLS quando necessário.

### Anon/Authenticated

Acesso frontend apenas via Views com RLS aplicado.

---

## 📈 Performance

### Índices Otimizados

| Tabela | Índice | Campos | Uso |
|--------|--------|--------|-----|
| fact_venda | idx_venda_tenant_data | tenant_id, data | Filtro por período |
| fact_venda | idx_venda_empresa | empresa_codigo | Filtro por filial |
| fact_receber | idx_receber_vencimento | data_vencimento | Alertas |
| audit_log | idx_audit_created | created_at DESC | Logs recentes |

### Particionamento

**Futuro:** Considerar particionamento por `tenant_id` ou `created_at` para tabelas grandes.

---

## 📝 Migrations

### Histórico

| Migration | Descrição | Data | Status |
|-----------|-----------|------|--------|
| `001_init_schema.sql` | Schema inicial | 2026-04 | ✅ Aplicada |
| `002_add_rls.sql` | RLS policies | 2026-04 | ✅ Aplicada |
| `003_add_views.sql` | Views públicas | 2026-05 | ✅ Aplicada |
| `004_add_snapshots.sql` | Tabela snapshots | 2026-05 | ✅ Aplicada |
| `005_add_indexes.sql` | Performance | 2026-05 | ✅ Aplicada |
| `010_governance_schema_v2.sql` | Governança | 2026-06 | ⏳ Pendente |

### Próxima Migration

- `011_business_analyst_tables.sql` - Tabelas para Business Health Score

---

## 🚫 Proibições

### NUNCA na UI

- ❌ SQL direto do frontend
- ❌ Bypass de RLS sem autorização
- ❌ Queries sem filtro de tenant
- ❌ Dados de outros tenants

### SEMPRE no Backend

- ✅ Validação de permissões
- ✅ Filtro de tenant
- ✅ Sanitização de inputs
- ✅ Logging de ações

---

**[DATABASE MAPPING — APROVADO]**

*Atualizar ao criar novas tabelas ou migrations*
