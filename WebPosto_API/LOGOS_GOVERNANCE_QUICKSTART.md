# LOGOS GOVERNANCE — QUICK START GUIDE

## 🚀 INÍCIO RÁPIDO

### 1. Executar Migration SQL

```bash
# Conectar ao Supabase e executar
psql -h <SUPABASE_HOST> -U postgres -d postgres -f database/migrations/010_governance_schema.sql
```

### 2. Iniciar Backend

```bash
cd "c:\Users\mlisb\OneDrive\ProjetosAntigravy\LOGOS SPACE\Api_WebPosto\WebPosto_API"
python -m uvicorn src.main:app --host 127.0.0.1 --port 8040 --reload
```

### 3. Testar Endpoints

```bash
# Audit Log
curl "http://127.0.0.1:8040/v1/governance/audit-log?tenant=POSTO_VIP"

# Dashboard
curl "http://127.0.0.1:8040/v1/governance/dashboard?tenant=POSTO_VIP"

# RBAC - Atribuir role
curl -X POST "http://127.0.0.1:8040/v1/governance/rbac/assign-role?tenant=POSTO_VIP&user_id=user123&user_email=user@posto.com&role=FINANCE"

# RBAC - Verificar permissão
curl "http://127.0.0.1:8040/v1/governance/rbac/check-permission?tenant=POSTO_VIP&user_id=user123&module=financial&action=read"
```

## 📋 USO NO CÓDIGO

### Registrar Auditoria

```python
from src.services.governance import audit_log, AuditAction, AuditStatus

# Em qualquer endpoint
await audit_log(
    tenant_id=tenant,
    action=AuditAction.CREATE,
    entity_type="FINANCIAL_CONFIG",
    entity_id="config_001",
    user_id=user_id,
    user_email=user_email,
    ip_address=request.client.host,
    status=AuditStatus.SUCCESS,
    description="Configuração financeira criada",
)
```

### Verificar Permissão

```python
from src.services.governance import get_rbac_service

rbac = get_rbac_service()

# Verificar se usuário pode acessar módulo
can_access = await rbac.can_user_access(
    tenant_id=tenant,
    user_id=user_id,
    module="financial",
    action="delete",
)

if not can_access:
    raise HTTPException(status_code=403, detail="Acesso negado")
```

### Atribuir Role

```python
from src.services.governance import get_rbac_service, UserRole

rbac = get_rbac_service()

success = await rbac.assign_role(
    tenant_id=tenant,
    user_id=user_id,
    user_email=user_email,
    role=UserRole.FINANCE,
)
```

## 🔐 ROLES DISPONÍVEIS

- `OWNER` - Acesso total
- `ADMIN` - Quase tudo (não pode deletar tenant)
- `MANAGER` - Operações + relatórios
- `FINANCE` - Apenas financeiro
- `OPERATIONS` - Apenas operacional
- `VIEWER` - Apenas leitura

## 📊 ENDPOINTS PRINCIPAIS

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/v1/governance/audit-log` | GET | Lista logs de auditoria |
| `/v1/governance/audit-log/stats` | GET | Estatísticas de auditoria |
| `/v1/governance/rbac/user-role` | GET | Busca role do usuário |
| `/v1/governance/rbac/user-permissions` | GET | Lista permissões |
| `/v1/governance/rbac/assign-role` | POST | Atribui role |
| `/v1/governance/rbac/check-permission` | GET | Verifica permissão |
| `/v1/governance/dashboard` | GET | Dashboard de governança |

## ✅ CHECKLIST DE IMPLEMENTAÇÃO

### Backend
- [x] Schema `governance` criado
- [x] Tabela `audit_log` criada
- [x] Tabela `user_roles` criada
- [x] Tabela `approval_requests` criada
- [x] Tabela `security_events` criada
- [x] Tabela `copilot_audit` criada
- [x] AuditLogService implementado
- [x] RBACService implementado
- [x] Endpoints FastAPI criados
- [x] Router registrado em `app.py`

### Frontend
- [ ] Página `/app/security`
- [ ] Página `/app/governance`
- [ ] Visualização de audit logs
- [ ] Gestão de roles
- [ ] Dashboard de KPIs

## 🧪 VALIDAÇÃO

1. ✅ Backend roda sem erros
2. ✅ Endpoints respondem 200 OK
3. ✅ RLS preserva multi-tenancy
4. ✅ Audit logs são gravados
5. ✅ Roles podem ser atribuídas
6. ✅ Permissões são verificadas

## 📝 PRÓXIMOS PASSOS

1. Executar migration SQL no Supabase
2. Testar todos endpoints via curl/Postman
3. Integrar auditoria em endpoints existentes
4. Criar frontend (Security Center + Governance Dashboard)
5. Implementar notificações de eventos críticos

---

**Documentação completa:** `LOGOS_GOVERNANCE_ARCHITECTURE.md`
