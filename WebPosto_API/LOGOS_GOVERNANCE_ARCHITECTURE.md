# LOGOS_GOVERNANCE_ARCHITECTURE.md

## SPRINT 25A — ADVANCED GOVERNANCE

**Data:** 27/06/2026  
**Sistema:** LOGOS FastAPI Oficial  
**Status:** Implementado (Backend) | Em Progresso (Frontend)

---

## 🎯 VISÃO GERAL

Camada completa de governança empresarial para o LOGOS, garantindo:

- ✅ **Auditoria** completa de todas as ações
- ✅ **Rastreabilidade** total de eventos
- ✅ **Controle de acesso** baseado em roles (RBAC)
- 🔄 **Compliance** com padrões de segurança
- 🔄 **Operação segura** para crescimento comercial

---

## 🗄️ ARQUITETURA DE DADOS

### Schema: `governance`

Novo schema dedicado à governança, separado dos dados operacionais.

### Tabelas Criadas

#### 1. `governance.audit_log`

**Propósito:** Registro completo de todas as ações auditáveis.

**Campos principais:**
- `tenant_id`, `user_id`, `user_email`
- `action` (LOGIN, CREATE, UPDATE, DELETE, ETL_START, etc.)
- `entity_type`, `entity_id`
- `status` (SUCCESS, FAILURE, PENDING)
- `ip_address`, `user_agent`, `request_path`
- `metadata` (JSONB para dados adicionais)

**Índices:**
- `idx_audit_log_tenant`
- `idx_audit_log_user`
- `idx_audit_log_action`
- `idx_audit_log_created`

**RLS:** ✅ Tenant isolation ativo

#### 2. `governance.approval_requests`

**Propósito:** Fluxo de aprovação para ações críticas.

**Campos principais:**
- `request_id` (UUID único)
- `tenant_id`
- `requester_user_id`, `requester_email`
- `action_type` (DELETE_TENANT, RESET_WATERMARK, etc.)
- `status` (PENDING, APPROVED, REJECTED, EXECUTED, EXPIRED)
- `approver_user_id`, `approval_comment`
- `executed_at`, `execution_result`

**Fluxo:**
1. Solicitação criada → PENDING
2. Aprovador revisa → APPROVED/REJECTED
3. Sistema executa → EXECUTED
4. Auto-expiração → EXPIRED (após 7 dias)

**RLS:** ✅ Tenant isolation ativo

#### 3. `governance.security_events`

**Propósito:** Eventos de segurança (falhas, acessos suspeitos).

**Campos principais:**
- `tenant_id`, `user_id`, `user_email`
- `event_type` (LOGIN_FAILED, SUSPICIOUS_ACCESS, RATE_LIMIT)
- `severity` (LOW, MEDIUM, HIGH, CRITICAL)
- `ip_address`, `user_agent`
- `action_taken` (BLOCKED, LOGGED, ALERTED)

**RLS:** ✅ Tenant isolation ativo

#### 4. `governance.copilot_audit`

**Propósito:** Auditoria de uso do Copilot (IA).

**Campos principais:**
- `tenant_id`, `user_id`, `session_id`
- `question`, `response`
- `context_used` (JSONB)
- `model_used`, `tokens_prompt`, `tokens_completion`
- `estimated_cost_usd`
- `response_time_ms`
- `user_feedback`, `user_rating`

**RLS:** ✅ Tenant isolation ativo

#### 5. `governance.user_roles`

**Propósito:** Controle de acesso baseado em roles (RBAC).

**Campos principais:**
- `tenant_id`, `user_id`, `user_email`
- `role` (OWNER, ADMIN, MANAGER, FINANCE, OPERATIONS, VIEWER)
- `custom_permissions` (JSONB)
- `is_active`

**Constraint:** Um usuário = uma role por tenant

**RLS:** ✅ Tenant isolation ativo

---

## 🔐 RBAC — ROLE-BASED ACCESS CONTROL

### Roles Disponíveis

| Role | Descrição | Acesso |
|------|-----------|--------|
| **OWNER** | Dono do tenant | Acesso total, incluindo deletar tenant |
| **ADMIN** | Administrador | Quase tudo, exceto deletar tenant |
| **MANAGER** | Gerente | Operações + relatórios + analytics |
| **FINANCE** | Financeiro | Apenas módulos financeiros |
| **OPERATIONS** | Operações | Apenas módulos operacionais |
| **VIEWER** | Visualizador | Apenas leitura em dashboards |

### Matriz de Permissões

#### OWNER
- Módulos: `*` (todos)
- Ações: `*` (todas)

#### ADMIN
- Módulos: `*` (todos)
- Ações: `create`, `read`, `update`, `export`, `import`
- Proibido: `delete_tenant`

#### MANAGER
- Módulos: `dashboard`, `financial`, `operations`, `reports`, `analytics`, `copilot`
- Ações: `read`, `create`, `update`, `export`

#### FINANCE
- Módulos: `dashboard`, `financial`, `accounts_payable`, `accounts_receivable`, `cards`, `reports`
- Ações: `read`, `create`, `update`, `export`

#### OPERATIONS
- Módulos: `dashboard`, `operations`, `fuel`, `inventory`, `sales`, `reports`
- Ações: `read`, `create`, `update`

#### VIEWER
- Módulos: `dashboard`, `reports`, `analytics`
- Ações: `read`

---

## 🛣️ API ENDPOINTS

### Base Path: `/v1/governance`

#### Audit Log

**`GET /v1/governance/audit-log`**
- Query params: `tenant`, `limit`, `action`, `user_id`
- Retorna: Lista de logs de auditoria

**`GET /v1/governance/audit-log/stats`**
- Query params: `tenant`, `days`
- Retorna: Estatísticas agregadas

#### RBAC

**`GET /v1/governance/rbac/user-role`**
- Query params: `tenant`, `user_id`
- Retorna: Role do usuário

**`GET /v1/governance/rbac/user-permissions`**
- Query params: `tenant`, `user_id`
- Retorna: Todas as permissões do usuário

**`POST /v1/governance/rbac/assign-role`**
- Query params: `tenant`, `user_id`, `user_email`, `role`
- Atribui role a um usuário

**`GET /v1/governance/rbac/check-permission`**
- Query params: `tenant`, `user_id`, `module`, `action`
- Verifica se usuário tem permissão específica

#### Security

**`GET /v1/governance/security/events`**
- Query params: `tenant`, `limit`, `severity`
- Retorna: Eventos de segurança

#### Dashboard

**`GET /v1/governance/dashboard`**
- Query params: `tenant`
- Retorna: KPIs de governança

---

## 💻 BACKEND SERVICES

### AuditLogService

**Arquivo:** `src/services/governance/audit_log_service.py`

**Métodos principais:**
- `async log()` - Registra ação auditável
- `async get_recent_logs()` - Busca logs recentes
- `async get_stats()` - Estatísticas

**Uso:**
```python
from src.services.governance import audit_log, AuditAction

await audit_log(
    tenant_id="POSTO_VIP",
    action=AuditAction.LOGIN,
    user_id="user123",
    user_email="user@posto.com",
    ip_address="192.168.1.1",
    status=AuditStatus.SUCCESS,
)
```

### RBACService

**Arquivo:** `src/services/governance/rbac_service.py`

**Métodos principais:**
- `async get_user_role()` - Busca role do usuário
- `async assign_role()` - Atribui role
- `has_permission()` - Verifica permissão
- `async can_user_access()` - Verifica acesso

**Uso:**
```python
from src.services.governance import get_rbac_service, UserRole

rbac = get_rbac_service()

# Atribuir role
await rbac.assign_role(
    tenant_id="POSTO_VIP",
    user_id="user123",
    user_email="user@posto.com",
    role=UserRole.FINANCE,
)

# Verificar acesso
can_access = await rbac.can_user_access(
    tenant_id="POSTO_VIP",
    user_id="user123",
    module="financial",
    action="read",
)
```

---

## 🔒 SEGURANÇA

### Row-Level Security (RLS)

**Todas as tabelas possuem RLS ativo.**

**Políticas:**
- `SELECT`: Usuário só vê dados do próprio tenant
- `INSERT`: Service role pode inserir
- `UPDATE/DELETE`: Controlado por tenant_id

### Tenant Isolation

**100% garantido.**

Nenhum tenant pode:
- Ver logs de outro tenant
- Ver roles de outro tenant
- Ver eventos de segurança de outro tenant
- Ver auditorias de Copilot de outro tenant

### PII Redaction

**Dados sensíveis não são logados:**
- Senhas
- API keys
- Tokens
- Cartões de crédito

---

## 📊 AÇÕES AUDITADAS

### Autenticação
- `LOGIN`, `LOGOUT`, `LOGIN_FAILED`

### CRUD
- `CREATE`, `READ`, `UPDATE`, `DELETE`

### Operações Especiais
- `EXPORT`, `IMPORT`, `BULK_UPDATE`, `BULK_DELETE`

### ETL
- `ETL_START`, `ETL_SUCCESS`, `ETL_FAILURE`

### Configuração
- `CONFIG_CHANGE`, `PERMISSION_CHANGE`

### Onboarding
- `TENANT_ONBOARD`, `TENANT_OFFBOARD`

### Relatórios
- `REPORT_GENERATED`, `ALERT_SENT`

---

## 🧪 TESTES

### SQL Migration

```bash
# Executar migration no Supabase
psql -h <host> -U postgres -d postgres -f database/migrations/010_governance_schema.sql
```

### Testar Endpoints

```bash
# Backend rodando em http://127.0.0.1:8040

# Audit Log
curl "http://127.0.0.1:8040/v1/governance/audit-log?tenant=POSTO_VIP&limit=10"

# User Role
curl "http://127.0.0.1:8040/v1/governance/rbac/user-role?tenant=POSTO_VIP&user_id=user123"

# Check Permission
curl "http://127.0.0.1:8040/v1/governance/rbac/check-permission?tenant=POSTO_VIP&user_id=user123&module=financial&action=read"

# Dashboard
curl "http://127.0.0.1:8040/v1/governance/dashboard?tenant=POSTO_VIP"
```

---

## 📝 PRÓXIMAS IMPLEMENTAÇÕES

### Backend (TODO)

- [ ] Approval Service completo
- [ ] Security Events Service
- [ ] Copilot Audit integration
- [ ] Auto-expiration de approvals (scheduled job)
- [ ] Notificações de eventos críticos

### Frontend (TODO)

- [ ] Página `/app/security` (Security Center)
- [ ] Página `/app/governance` (Governance Dashboard)
- [ ] Visualização de logs de auditoria
- [ ] Gestão de roles de usuários
- [ ] Aprovação de ações críticas
- [ ] Gráficos de eventos de segurança

---

## 🎯 CRITÉRIOS DE ACEITE

| # | Critério | Status |
|---|----------|--------|
| 1 | Schema governance criado | ✅ |
| 2 | Tabelas criadas com RLS | ✅ |
| 3 | Audit Log Service funcional | ✅ |
| 4 | RBAC Service funcional | ✅ |
| 5 | Endpoints FastAPI criados | ✅ |
| 6 | Multi-tenant preservado | ✅ |
| 7 | Approval Service | ⏳ (estrutura criada) |
| 8 | Copilot Audit | ⏳ (estrutura criada) |
| 9 | Security Center frontend | ⏳ (TODO) |
| 10 | Governance Dashboard frontend | ⏳ (TODO) |

**Status Geral:** 6/10 completos (60%) — Backend funcional, frontend pendente

---

## 📈 MÉTRICAS DE GOVERNANÇA

### KPIs Disponíveis (via API)

- Total de eventos auditados
- Usuários ativos
- Aprovações pendentes
- Eventos de segurança
- Queries do Copilot
- Custos estimados de IA

### Score de Governança

**Fórmula:**
```
score = (
    audit_coverage * 0.3 +
    rbac_coverage * 0.25 +
    approval_coverage * 0.20 +
    security_coverage * 0.15 +
    compliance_score * 0.10
)
```

**Meta:** Score ≥ 85% para Enterprise Readiness

---

**Última atualização:** 27/06/2026 23:50 UTC-3
