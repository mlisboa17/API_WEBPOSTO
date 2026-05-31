-- PostgreSQL 17 Initialization Script
-- Executa automaticamente na primeira inicialização do container

-- ===== CREATE DATABASE =====
-- POSTGRES_DB=webposto já cria a DB automáticamente

-- ===== CREATE EXTENSIONS =====
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ===== CREATE SCHEMAS =====
CREATE SCHEMA IF NOT EXISTS public;
CREATE SCHEMA IF NOT EXISTS audit;

-- ===== EMPRESA TABLE =====
CREATE TABLE IF NOT EXISTS public.empresas (
    empresa_id VARCHAR(50) PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    config_tipo_rateio VARCHAR(20) DEFAULT 'proporcional',
    validar_soma_100 BOOLEAN DEFAULT TRUE,
    ativo BOOLEAN DEFAULT TRUE,
    timestamp_criacao TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    timestamp_atualizacao TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT empresa_nome_unique UNIQUE (nome)
);

CREATE INDEX idx_empresas_ativo ON public.empresas(ativo);
CREATE INDEX idx_empresas_timestamp_criacao ON public.empresas(timestamp_criacao);

-- ===== CENTRO CUSTO TABLE =====
CREATE TABLE IF NOT EXISTS public.centros_custo (
    centro_custo_id VARCHAR(50) PRIMARY KEY,
    empresa_id VARCHAR(50) NOT NULL REFERENCES public.empresas(empresa_id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    percentual_padrao NUMERIC(5, 2),
    ativo BOOLEAN DEFAULT TRUE,
    timestamp_criacao TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT centro_custo_uq UNIQUE (empresa_id, nome)
);

CREATE INDEX idx_centros_custo_empresa_id ON public.centros_custo(empresa_id);
CREATE INDEX idx_centros_custo_ativo ON public.centros_custo(ativo);

-- ===== RATEIO TABLE =====
CREATE TABLE IF NOT EXISTS public.rateios (
    rateio_id VARCHAR(50) PRIMARY KEY,
    empresa_id VARCHAR(50) NOT NULL REFERENCES public.empresas(empresa_id) ON DELETE CASCADE,
    lancamento_id VARCHAR(50) NOT NULL,
    valor_total NUMERIC(19, 2) NOT NULL,
    detalhes JSONB,
    timestamp_criacao TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT rateio_lancamento_empresa_uq UNIQUE (empresa_id, lancamento_id)
);

CREATE INDEX idx_rateios_empresa_id ON public.rateios(empresa_id);
CREATE INDEX idx_rateios_lancamento_id ON public.rateios(lancamento_id);
CREATE INDEX idx_rateios_timestamp_criacao ON public.rateios(timestamp_criacao);
CREATE INDEX idx_rateios_detalhes ON public.rateios USING GIN(detalhes);

-- ===== SYNC HISTORY TABLE =====
CREATE TABLE IF NOT EXISTS public.sync_history (
    sync_id VARCHAR(50) PRIMARY KEY,
    empresa_id VARCHAR(50) NOT NULL REFERENCES public.empresas(empresa_id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    timestamp_inicio TIMESTAMP WITH TIME ZONE NOT NULL,
    timestamp_fim TIMESTAMP WITH TIME ZONE,
    total_lancamentos_processados INTEGER DEFAULT 0,
    total_rateios_criados INTEGER DEFAULT 0,
    total_divergencias_detectadas INTEGER DEFAULT 0,
    duracao_segundos NUMERIC(10, 2),
    mensagem_erro TEXT,
    CONSTRAINT sync_status_check CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'partially_failed'))
);

CREATE INDEX idx_sync_history_empresa_id ON public.sync_history(empresa_id);
CREATE INDEX idx_sync_history_status ON public.sync_history(status);
CREATE INDEX idx_sync_history_timestamp_inicio ON public.sync_history(timestamp_inicio DESC);

-- ===== OUTBOX EVENT TABLE (Garantia de Entrega) =====
CREATE TABLE IF NOT EXISTS public.outbox_events (
    outbox_id VARCHAR(50) PRIMARY KEY,
    empresa_id VARCHAR(50) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB NOT NULL,
    timestamp_criacao TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    timestamp_publicacao TIMESTAMP WITH TIME ZONE,
    processado BOOLEAN DEFAULT FALSE,
    tentativas INTEGER DEFAULT 0,
    max_tentativas INTEGER DEFAULT 3,
    CONSTRAINT outbox_max_tentativas CHECK (tentativas <= max_tentativas)
);

CREATE INDEX idx_outbox_events_processado ON public.outbox_events(processado);
CREATE INDEX idx_outbox_events_empresa_id ON public.outbox_events(empresa_id);
CREATE INDEX idx_outbox_events_event_type ON public.outbox_events(event_type);
CREATE INDEX idx_outbox_events_timestamp_criacao ON public.outbox_events(timestamp_criacao DESC);
CREATE INDEX idx_outbox_events_nao_processados ON public.outbox_events(timestamp_criacao) WHERE processado = FALSE;

-- ===== DOMAIN EVENTS TABLE (Event Sourcing) =====
CREATE TABLE IF NOT EXISTS public.domain_events (
    event_id VARCHAR(50) PRIMARY KEY,
    empresa_id VARCHAR(50) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB NOT NULL,
    timestamp_criacao TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    versao INTEGER DEFAULT 1
);

CREATE INDEX idx_domain_events_empresa_id ON public.domain_events(empresa_id);
CREATE INDEX idx_domain_events_event_type ON public.domain_events(event_type);
CREATE INDEX idx_domain_events_timestamp_criacao ON public.domain_events(timestamp_criacao DESC);

-- ===== AUDIT SCHEMA =====

CREATE TABLE IF NOT EXISTS audit.audit_log (
    audit_id BIGSERIAL PRIMARY KEY,
    event_id VARCHAR(50) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    usuario_id VARCHAR(100),
    empresa_id VARCHAR(50),
    recurso_id VARCHAR(50),
    recurso_tipo VARCHAR(50),
    descricao TEXT,
    dados JSONB,
    ip_address INET,
    user_agent VARCHAR(500),
    hash_sha256 VARCHAR(64),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT audit_log_event_type_check CHECK (event_type IN (
        'token.created', 'token.verified', 'token.expired', 'token.invalid',
        'auth.failed', 'auth.success',
        'hash.calculated', 'hash.verified', 'hash.mismatch', 'integrity.failed',
        'anomaly.detected', 'anomaly.resolved', 'anomaly.high_risk',
        'rateio.created', 'rateio.modified', 'rateio.deleted',
        'sync.started', 'sync.completed', 'sync.failed',
        'config.changed', 'key.rotated', 'backup.created'
    ))
);

CREATE INDEX idx_audit_log_empresa_id ON audit.audit_log(empresa_id);
CREATE INDEX idx_audit_log_usuario_id ON audit.audit_log(usuario_id);
CREATE INDEX idx_audit_log_event_type ON audit.audit_log(event_type);
CREATE INDEX idx_audit_log_timestamp ON audit.audit_log(timestamp DESC);
CREATE INDEX idx_audit_log_recurso_id ON audit.audit_log(recurso_id);

-- ===== GRANTS =====
GRANT USAGE ON SCHEMA public TO postgres;
GRANT USAGE ON SCHEMA audit TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA audit TO postgres;

-- ===== SAMPLE DATA =====

INSERT INTO public.empresas (empresa_id, nome, config_tipo_rateio, validar_soma_100, ativo)
VALUES 
    ('emp_001', 'Empresa Teste 1', 'proporcional', TRUE, TRUE),
    ('emp_002', 'Empresa Teste 2', 'uniforme', TRUE, TRUE),
    ('emp_003', 'Empresa Teste 3', 'customizado', TRUE, TRUE)
ON CONFLICT DO NOTHING;

INSERT INTO public.centros_custo (centro_custo_id, empresa_id, nome, percentual_padrao, ativo)
VALUES 
    ('cc_001', 'emp_001', 'Centro Administrativo', 25.00, TRUE),
    ('cc_002', 'emp_001', 'Centro Operacional', 50.00, TRUE),
    ('cc_003', 'emp_001', 'Centro Financeiro', 25.00, TRUE),
    ('cc_004', 'emp_002', 'Centro Único', 100.00, TRUE),
    ('cc_005', 'emp_003', 'Centro A', 33.33, TRUE),
    ('cc_006', 'emp_003', 'Centro B', 33.33, TRUE),
    ('cc_007', 'emp_003', 'Centro C', 33.34, TRUE)
ON CONFLICT DO NOTHING;

-- ===== DONE =====
-- Initialization complete. Tables ready for application use.
