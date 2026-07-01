-- ============================================================================
-- LOGOS GOVERNANCE SCHEMA
-- Sprint: 25A — Advanced Governance
-- Data: 2026-06-27
-- ============================================================================

-- Criar schema
CREATE SCHEMA IF NOT EXISTS governance;

-- ============================================================================
-- TABELA: audit_log
-- Registra todas as ações auditáveis do sistema
-- ============================================================================
CREATE TABLE governance.audit_log (
    id BIGSERIAL PRIMARY KEY,
    
    -- Identificação
    tenant_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100),
    user_email VARCHAR(255),
    
    -- Ação
    action VARCHAR(100) NOT NULL,  -- Ex: LOGIN, CREATE, UPDATE, DELETE, EXPORT
    entity_type VARCHAR(100),      -- Ex: TENANT, USER, FINANCIAL_CONFIG
    entity_id VARCHAR(100),
    
    -- Contexto
    description TEXT,
    metadata JSONB DEFAULT '{}',   -- Dados adicionais em JSON
    
    -- Request info
    ip_address INET,
    user_agent TEXT,
    request_method VARCHAR(10),    -- GET, POST, PUT, DELETE
    request_path TEXT,
    
    -- Resultado
    status VARCHAR(20) NOT NULL,   -- SUCCESS, FAILURE, PENDING
    error_message TEXT,
    
    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Índices para performance
    CONSTRAINT audit_log_tenant_fk 
        FOREIGN KEY (tenant_id) 
        REFERENCES public.tenants(tenant_id) 
        ON DELETE CASCADE
);

-- Índices
CREATE INDEX idx_audit_log_tenant ON governance.audit_log(tenant_id);
CREATE INDEX idx_audit_log_user ON governance.audit_log(user_id);
CREATE INDEX idx_audit_log_action ON governance.audit_log(action);
CREATE INDEX idx_audit_log_entity ON governance.audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_log_created ON governance.audit_log(created_at DESC);
CREATE INDEX idx_audit_log_status ON governance.audit_log(status);

-- RLS (Row Level Security)
ALTER TABLE governance.audit_log ENABLE ROW LEVEL SECURITY;

-- Política: Usuário só vê logs do próprio tenant
CREATE POLICY audit_log_tenant_isolation ON governance.audit_log
    FOR SELECT
    USING (tenant_id = current_setting('app.current_tenant', true));

-- Política: Service role pode inserir
CREATE POLICY audit_log_service_insert ON governance.audit_log
    FOR INSERT
    WITH CHECK (true);

-- ============================================================================
-- TABELA: approval_requests
-- Fluxo de aprovação para ações críticas
-- ============================================================================
CREATE TABLE governance.approval_requests (
    id BIGSERIAL PRIMARY KEY,
    
    -- Identificação
    tenant_id VARCHAR(100) NOT NULL,
    request_id UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    
    -- Solicitante
    requester_user_id VARCHAR(100) NOT NULL,
    requester_email VARCHAR(255) NOT NULL,
    
    -- Ação solicitada
    action_type VARCHAR(100) NOT NULL,  -- Ex: DELETE_TENANT, RESET_WATERMARK
    entity_type VARCHAR(100),
    entity_id VARCHAR(100),
    action_description TEXT NOT NULL,
    action_payload JSONB DEFAULT '{}',
    
    -- Aprovação
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',  -- PENDING, APPROVED, REJECTED, EXECUTED
    approver_user_id VARCHAR(100),
    approver_email VARCHAR(255),
    approval_comment TEXT,
    approved_at TIMESTAMPTZ,
    
    -- Execução
    executed_at TIMESTAMPTZ,
    execution_result JSONB,
    execution_error TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '7 days',
    
    -- Constraints
    CONSTRAINT approval_requests_tenant_fk 
        FOREIGN KEY (tenant_id) 
        REFERENCES public.tenants(tenant_id) 
        ON DELETE CASCADE,
    
    CONSTRAINT approval_requests_status_check 
        CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'EXECUTED', 'EXPIRED'))
);

-- Índices
CREATE INDEX idx_approval_tenant ON governance.approval_requests(tenant_id);
CREATE INDEX idx_approval_status ON governance.approval_requests(status);
CREATE INDEX idx_approval_requester ON governance.approval_requests(requester_user_id);
CREATE INDEX idx_approval_created ON governance.approval_requests(created_at DESC);

-- RLS
ALTER TABLE governance.approval_requests ENABLE ROW LEVEL SECURITY;

CREATE POLICY approval_requests_tenant_isolation ON governance.approval_requests
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant', true));

-- ============================================================================
-- TABELA: security_events
-- Eventos de segurança (falhas login, acessos suspeitos, etc.)
-- ============================================================================
CREATE TABLE governance.security_events (
    id BIGSERIAL PRIMARY KEY,
    
    -- Identificação
    tenant_id VARCHAR(100),
    user_id VARCHAR(100),
    user_email VARCHAR(255),
    
    -- Evento
    event_type VARCHAR(100) NOT NULL,  -- LOGIN_FAILED, SUSPICIOUS_ACCESS, RATE_LIMIT
    severity VARCHAR(20) NOT NULL,     -- LOW, MEDIUM, HIGH, CRITICAL
    description TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    
    -- Request info
    ip_address INET,
    user_agent TEXT,
    
    -- Resposta
    action_taken VARCHAR(100),  -- BLOCKED, LOGGED, ALERTED
    
    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT security_events_severity_check 
        CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'))
);

-- Índices
CREATE INDEX idx_security_tenant ON governance.security_events(tenant_id);
CREATE INDEX idx_security_event_type ON governance.security_events(event_type);
CREATE INDEX idx_security_severity ON governance.security_events(severity);
CREATE INDEX idx_security_created ON governance.security_events(created_at DESC);

-- RLS
ALTER TABLE governance.security_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY security_events_tenant_isolation ON governance.security_events
    FOR SELECT
    USING (
        tenant_id IS NULL OR 
        tenant_id = current_setting('app.current_tenant', true)
    );

-- ============================================================================
-- TABELA: copilot_audit
-- Auditoria de uso do Copilot (IA)
-- ============================================================================
CREATE TABLE governance.copilot_audit (
    id BIGSERIAL PRIMARY KEY,
    
    -- Identificação
    tenant_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    user_email VARCHAR(255),
    session_id UUID,
    
    -- Query
    question TEXT NOT NULL,
    response TEXT,
    
    -- Contexto IA
    context_used JSONB,           -- Documentos/dados usados como contexto
    model_used VARCHAR(100),      -- Ex: gpt-4, claude-3
    tokens_prompt INTEGER,
    tokens_completion INTEGER,
    tokens_total INTEGER,
    estimated_cost_usd DECIMAL(10, 6),
    
    -- Performance
    response_time_ms INTEGER,
    
    -- Feedback
    user_feedback VARCHAR(20),    -- HELPFUL, NOT_HELPFUL, INACCURATE
    user_rating INTEGER,          -- 1-5
    
    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT copilot_audit_tenant_fk 
        FOREIGN KEY (tenant_id) 
        REFERENCES public.tenants(tenant_id) 
        ON DELETE CASCADE
);

-- Índices
CREATE INDEX idx_copilot_tenant ON governance.copilot_audit(tenant_id);
CREATE INDEX idx_copilot_user ON governance.copilot_audit(user_id);
CREATE INDEX idx_copilot_session ON governance.copilot_audit(session_id);
CREATE INDEX idx_copilot_created ON governance.copilot_audit(created_at DESC);
CREATE INDEX idx_copilot_model ON governance.copilot_audit(model_used);

-- RLS
ALTER TABLE governance.copilot_audit ENABLE ROW LEVEL SECURITY;

CREATE POLICY copilot_audit_tenant_isolation ON governance.copilot_audit
    FOR SELECT
    USING (tenant_id = current_setting('app.current_tenant', true));

CREATE POLICY copilot_audit_service_insert ON governance.copilot_audit
    FOR INSERT
    WITH CHECK (true);

-- ============================================================================
-- TABELA: user_roles
-- Controle de acesso baseado em roles (RBAC)
-- ============================================================================
CREATE TABLE governance.user_roles (
    id BIGSERIAL PRIMARY KEY,
    
    -- Identificação
    tenant_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    
    -- Role
    role VARCHAR(50) NOT NULL,  -- OWNER, ADMIN, MANAGER, FINANCE, OPERATIONS, VIEWER
    
    -- Permissões específicas (opcional, sobrescreve role padrão)
    custom_permissions JSONB DEFAULT '[]',
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT true,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT user_roles_tenant_fk 
        FOREIGN KEY (tenant_id) 
        REFERENCES public.tenants(tenant_id) 
        ON DELETE CASCADE,
    
    CONSTRAINT user_roles_role_check 
        CHECK (role IN ('OWNER', 'ADMIN', 'MANAGER', 'FINANCE', 'OPERATIONS', 'VIEWER')),
    
    -- Um usuário pode ter apenas uma role por tenant
    UNIQUE(tenant_id, user_id)
);

-- Índices
CREATE INDEX idx_user_roles_tenant ON governance.user_roles(tenant_id);
CREATE INDEX idx_user_roles_user ON governance.user_roles(user_id);
CREATE INDEX idx_user_roles_role ON governance.user_roles(role);

-- RLS
ALTER TABLE governance.user_roles ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_roles_tenant_isolation ON governance.user_roles
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant', true));

-- ============================================================================
-- GRANTS
-- ============================================================================

-- Service role (backend) pode fazer tudo
GRANT ALL ON SCHEMA governance TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA governance TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA governance TO service_role;

-- Anon/authenticated pode apenas ler (controlado por RLS)
GRANT USAGE ON SCHEMA governance TO anon, authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA governance TO anon, authenticated;

-- ============================================================================
-- FUNÇÕES AUXILIARES
-- ============================================================================

-- Função para expirar approval requests antigas
CREATE OR REPLACE FUNCTION governance.expire_old_approval_requests()
RETURNS INTEGER AS $$
DECLARE
    expired_count INTEGER;
BEGIN
    UPDATE governance.approval_requests
    SET status = 'EXPIRED'
    WHERE status = 'PENDING' 
      AND expires_at < NOW();
    
    GET DIAGNOSTICS expired_count = ROW_COUNT;
    RETURN expired_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- COMENTÁRIOS
-- ============================================================================

COMMENT ON SCHEMA governance IS 'Schema de governança, auditoria e compliance';
COMMENT ON TABLE governance.audit_log IS 'Log de auditoria de todas as ações do sistema';
COMMENT ON TABLE governance.approval_requests IS 'Solicitações de aprovação para ações críticas';
COMMENT ON TABLE governance.security_events IS 'Eventos de segurança (falhas, acessos suspeitos)';
COMMENT ON TABLE governance.copilot_audit IS 'Auditoria de uso do Copilot (IA)';
COMMENT ON TABLE governance.user_roles IS 'Roles e permissões de usuários (RBAC)';

-- ============================================================================
-- FIM
-- ============================================================================
