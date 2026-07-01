# LOGOS_PRODUCTION_MIGRATION_CHECKLIST.md

## CHECKLIST DE EXECUÇÃO — MIGRATION 010 GOVERNANCE

**Migration:** `010_governance_schema_v2.sql`  
**Data de execução:** ___/___/2026  
**Responsável:** ________________

---

## ✅ PRÉ-EXECUÇÃO

### 1. Preparação

- [ ] Ler auditoria completa (`LOGOS_MIGRATION_REVIEW_010.md`)
- [ ] Ler avaliação de risco (`LOGOS_DATABASE_RISK_ASSESSMENT.md`)
- [ ] Confirmar que migration v2 será usada (não v1)
- [ ] Confirmar horário de baixo tráfego (opcional)

### 2. Backup (Recomendado)

- [ ] Criar backup manual do Supabase (se disponível)
- [ ] Documentar ponto de restore

**Comando Supabase:**
```bash
# Via dashboard: Database > Backups > Create backup
```

### 3. Validação Ambiente

- [ ] Backend FastAPI está rodando
- [ ] Service role key está configurada em `.env`
- [ ] Supabase connection está ativa
- [ ] SQL Editor do Supabase está acessível

---

## 🚀 EXECUÇÃO

### 1. Abrir Migration

- [ ] Abrir arquivo: `database/migrations/010_governance_schema_v2.sql`
- [ ] Copiar **TODO** o conteúdo (Ctrl+A, Ctrl+C)

### 2. Acessar Supabase

- [ ] Acessar: https://supabase.com/dashboard
- [ ] Selecionar projeto LOGOS
- [ ] Ir em: **SQL Editor**
- [ ] Criar nova query

### 3. Executar Migration

- [ ] Colar conteúdo da migration
- [ ] Revisar visualmente (não precisa ler tudo)
- [ ] Clicar em **Run** (ou F5)
- [ ] Aguardar conclusão (~1 segundo)

### 4. Validar Erros

- [ ] Verificar se há mensagem de erro
- [ ] Se erro: ler mensagem, documentar, NÃO prosseguir
- [ ] Se sucesso: prosseguir para validação

---

## ✅ PÓS-EXECUÇÃO

### 1. Validar Objetos Criados

**Query de validação:**
```sql
-- 1. Verificar schema
SELECT nspname FROM pg_namespace WHERE nspname = 'governance';
-- Esperado: 1 linha

-- 2. Verificar tabelas
SELECT tablename FROM pg_tables WHERE schemaname = 'governance';
-- Esperado: 5 linhas (audit_log, approval_requests, security_events, copilot_audit, user_roles)

-- 3. Verificar índices
SELECT indexname FROM pg_indexes WHERE schemaname = 'governance';
-- Esperado: 19+ linhas

-- 4. Verificar RLS
SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'governance';
-- Esperado: rowsecurity = true para todas

-- 5. Verificar policies
SELECT schemaname, tablename, policyname FROM pg_policies WHERE schemaname = 'governance';
-- Esperado: 7 policies

-- 6. Verificar função
SELECT routine_name FROM information_schema.routines WHERE routine_schema = 'governance';
-- Esperado: 1 linha (expire_old_approval_requests)
```

**Checklist:**
- [ ] Schema `governance` existe
- [ ] 5 tabelas criadas
- [ ] 19+ índices criados
- [ ] RLS ativo em todas as tabelas
- [ ] 7 policies criadas
- [ ] 1 função criada

### 2. Testar RLS (Tenant Isolation)

```sql
-- Teste 1: Inserir registro de teste
SET ROLE service_role;
INSERT INTO governance.audit_log (tenant_id, action, status, user_id)
VALUES ('TEST_TENANT_A', 'LOGIN', 'SUCCESS', 'user1');

-- Teste 2: Filtrar por tenant
SET app.current_tenant = 'TEST_TENANT_A';
SELECT * FROM governance.audit_log WHERE tenant_id = 'TEST_TENANT_A';
-- Esperado: Ver o registro

-- Teste 3: Tentar ver outro tenant
SET app.current_tenant = 'TEST_TENANT_B';
SELECT * FROM governance.audit_log WHERE tenant_id = 'TEST_TENANT_A';
-- Esperado: 0 registros (tenant isolation funcionando)

-- Limpar teste
SET ROLE service_role;
DELETE FROM governance.audit_log WHERE user_id = 'user1';
```

**Checklist:**
- [ ] INSERT funcionou
- [ ] SELECT com tenant correto retornou dados
- [ ] SELECT com tenant diferente NÃO retornou dados (isolation OK)
- [ ] Registro de teste foi removido

### 3. Testar Backend

**Iniciar backend:**
```bash
cd "c:\Users\mlisb\OneDrive\ProjetosAntigravy\LOGOS SPACE\Api_WebPosto\WebPosto_API"
python -m uvicorn src.main:app --host 127.0.0.1 --port 8040 --reload
```

**Testar endpoints:**
```bash
# 1. Health check
curl http://127.0.0.1:8040/health

# 2. Governance dashboard
curl "http://127.0.0.1:8040/v1/governance/dashboard?tenant=POSTO_VIP"

# 3. Audit log
curl "http://127.0.0.1:8040/v1/governance/audit-log?tenant=POSTO_VIP&limit=10"

# 4. RBAC - atribuir role
curl -X POST "http://127.0.0.1:8040/v1/governance/rbac/assign-role?tenant=POSTO_VIP&user_id=test123&user_email=test@posto.com&role=VIEWER"

# 5. RBAC - verificar permissão
curl "http://127.0.0.1:8040/v1/governance/rbac/check-permission?tenant=POSTO_VIP&user_id=test123&module=financial&action=read"
```

**Checklist:**
- [ ] Backend iniciou sem erros
- [ ] `/health` retorna 200 OK
- [ ] `/v1/governance/dashboard` retorna 200 OK
- [ ] `/v1/governance/audit-log` retorna 200 OK (mesmo vazio)
- [ ] `/v1/governance/rbac/assign-role` retorna 200 OK
- [ ] `/v1/governance/rbac/check-permission` retorna 200 OK

### 4. Testar Frontend

**Acessar páginas:**
```
http://127.0.0.1:8040/pages/security.html
http://127.0.0.1:8040/pages/governance.html
```

**Checklist:**
- [ ] Página Security Center carrega
- [ ] Página Governance Dashboard carrega
- [ ] KPIs são exibidos (mesmo com valor 0)
- [ ] Nenhum erro no console do navegador
- [ ] Botão "Atualizar" funciona

---

## 📊 MONITORAMENTO (Primeiras 24h)

### Métricas para Acompanhar

- [ ] Tamanho da tabela `audit_log` (crescimento esperado)
- [ ] Performance de queries (< 50ms)
- [ ] Logs de erro do backend (relacionados a governance)
- [ ] Taxa de INSERT em audit_log

**Query de monitoramento:**
```sql
-- Tamanho das tabelas
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables 
WHERE schemaname = 'governance'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Contagem de registros
SELECT 
    'audit_log' as table, COUNT(*) as count FROM governance.audit_log
UNION ALL
SELECT 'approval_requests', COUNT(*) FROM governance.approval_requests
UNION ALL
SELECT 'security_events', COUNT(*) FROM governance.security_events
UNION ALL
SELECT 'copilot_audit', COUNT(*) FROM governance.copilot_audit
UNION ALL
SELECT 'user_roles', COUNT(*) FROM governance.user_roles;
```

---

## 🚨 TROUBLESHOOTING

### Problema 1: Migration falhou com erro

**Sintomas:** Mensagem de erro no SQL Editor

**Ações:**
1. Copiar mensagem de erro completa
2. Verificar linha do erro
3. Se erro é "relation already exists": OK, já foi executada
4. Se erro é "permission denied": verificar role
5. Se outro erro: documentar e não prosseguir

### Problema 2: RLS não funciona

**Sintomas:** Tenant isolation não está funcionando

**Ações:**
1. Verificar se policies foram criadas: `\dRp governance.*`
2. Verificar se RLS está ativo: `SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'governance'`
3. Verificar se backend configura `current_setting('app.current_tenant')`

### Problema 3: Backend não consegue INSERT

**Sintomas:** Erro 403 ou permission denied

**Ações:**
1. Verificar se service_role key está correta em `.env`
2. Verificar grants: `SELECT * FROM information_schema.role_table_grants WHERE grantee = 'service_role' AND table_schema = 'governance'`
3. Re-executar grants manualmente se necessário

### Problema 4: Frontend não carrega

**Sintomas:** Erro 404 ou página em branco

**Ações:**
1. Verificar se backend está rodando
2. Verificar console do navegador (F12)
3. Verificar se endpoints backend funcionam via curl
4. Verificar CORS (se erro de CORS)

---

## 🎯 CRITÉRIOS DE SUCESSO

**Migration é considerada bem-sucedida se:**

- ✅ Nenhum erro durante execução SQL
- ✅ Todos os objetos foram criados
- ✅ RLS funciona (tenant isolation validado)
- ✅ Backend inicia sem erros
- ✅ Endpoints retornam 200 OK
- ✅ Frontend carrega sem erros
- ✅ Primeiro INSERT em audit_log funciona

**Se TODOS os critérios acima foram atendidos:** ✅ **SUCESSO**

---

## 📝 REGISTRO DE EXECUÇÃO

**Data:** ___/___/2026  
**Hora início:** ____:____  
**Hora fim:** ____:____  
**Duração:** ____ segundos  
**Erros:** [ ] Sim [ ] Não  
**Rollback necessário:** [ ] Sim [ ] Não  
**Status final:** [ ] SUCESSO [ ] FALHA [ ] PARCIAL  

**Observações:**
```
_____________________________________________________________________________
_____________________________________________________________________________
_____________________________________________________________________________
```

**Responsável:** ________________  
**Assinatura:** ________________

---

## ✅ CONCLUSÃO

- [ ] Migration executada com sucesso
- [ ] Validações concluídas
- [ ] Testes passaram
- [ ] Sistema está operacional
- [ ] Monitoramento ativo
- [ ] Documentação atualizada

**Status:** [ ] APROVADO [ ] REPROVADO

---

**Última atualização:** 27/06/2026
