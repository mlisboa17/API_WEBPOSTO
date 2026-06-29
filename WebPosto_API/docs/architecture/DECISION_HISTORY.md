---
# 📜 DECISION HISTORY | LOGOS Architecture
# Type: ARCHITECTURE_SPEC
# Version: 1.0
# Sprint: PRODUCT-05 — LOGOS Impact System
# Status: SPECIFIED
---

# Decision History — Architecture

> **Sistema de registro e consulta histórica de todas as decisões geradas pelo LOGOS.**

---

## 🎯 Propósito

Criar um **histórico completo e auditável** de todas as decisões do LOGOS.

Cada decisão armazena:
- Origem e contexto
- Impacto estimado e real
- Status e resultado
- Tempo e eficiência
- Metadata de rastreabilidade

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    DECISION HISTORY                          │
│                      Storage Engine                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Decision Repository                     │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │   │
│  │  │  Active  │ │ Archived │ │  Search  │ │  Audit │  │   │
│  │  │  Store   │ │  Store   │ │  Index   │ │  Trail │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│          ┌────────────────┼────────────────┐              │
│          ▼                ▼                ▼              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │    Query     │  │   Analytics  │  │  Retention   │      │
│  │   Engine     │  │   Engine     │  │   Manager    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Model

### Decision Entity

```python
class Decision(BaseModel):
    """Complete decision record in history."""
    
    # Identification
    decision_id: str                      # UUID único
    tenant_id: str                        # Empresa
    empresa_codigo: str                   # Código WebPosto
    created_at: datetime                  # Geração
    updated_at: datetime                  # Última atualização
    
    # Categorization
    category: DecisionCategory            # RISK, RECOVERY, OPPORTUNITY
    type: DecisionType                    # Tipo específico
    priority: DecisionPriority            # CRITICAL, HIGH, MEDIUM, LOW
    
    # Detection
    detection: DetectionInfo
    
    # Investigation
    investigation: Optional[InvestigationInfo]
    
    # Explanation
    title: str                           # Título curto
    description: str                     # Descrição completa
    impact_summary: str                  # Resumo do impacto
    
    # Financial
    estimated_impact: FinancialImpact
    actual_impact: Optional[ActualImpact]
    
    # Execution
    execution: ExecutionInfo
    
    # Confidence
    confidence_score: ConfidenceScore
    
    # Metadata
    source_engine: str                   # Qual motor gerou
    source_endpoint: str                 # Qual endpoint
    trace_id: str                        # ID de rastreamento
    
    # Status
    status: DecisionStatus
    
    # Learning
    effectiveness: Optional[EffectivenessMetrics]


class DetectionInfo(BaseModel):
    """Information about how the decision was detected."""
    
    detected_at: datetime
    detector_engine: str                  # MoneyAtRisk, Recoverable, etc
    trigger_type: str                    # threshold_crossed, anomaly, etc
    baseline_value: float
    current_value: float
    deviation_percent: float
    confidence: float


class InvestigationInfo(BaseModel):
    """Investigation details for complex decisions."""
    
    investigated: bool
    investigation_id: Optional[str]
    dimensions: List[str]                # product, time, location, etc
    root_cause: Optional[str]
    contributing_factors: List[str]
    investigation_depth: str             # basic, standard, deep


class FinancialImpact(BaseModel):
    """Financial impact estimation."""
    
    currency: str = "BRL"
    amount: float
    type: str                            # recovered, saved, prevented, additional
    timeframe: str                       # daily, weekly, monthly
    calculation_method: str
    confidence: float


class ActualImpact(BaseModel):
    """Actual measured impact after execution."""
    
    measured: bool
    measured_at: Optional[datetime]
    verified_amount: Optional[float]
    verification_method: str              # owner_confirmed, automatic, estimated
    variance_from_estimate: Optional[float]


class ExecutionInfo(BaseModel):
    """Execution tracking."""
    
    generated_at: datetime
    presented_at: Optional[datetime]      # Quando foi mostrado ao owner
    executed_at: Optional[datetime]
    execution_duration_minutes: Optional[float]
    
    action_taken: Optional[str]
    action_context: Optional[str]
    
    confirmation: Optional[ConfirmationInfo]


class ConfirmationInfo(BaseModel):
    """Owner confirmation details."""
    
    confirmed: bool
    confirmed_at: Optional[datetime]
    result: str                          # YES, NO, PARTIAL
    
    # Se NÃO
    rejection_reason: Optional[str]
    rejection_detail: Optional[str]
    
    # Se PARCIAL
    progress_percent: Optional[float]
    next_action: Optional[str]


class ConfidenceScore(BaseModel):
    """Confidence in the decision."""
    
    overall: float                       # 0-100
    data_quality: float
    endpoint_health: float
    historical_sufficiency: float
    calculation_confidence: float


class EffectivenessMetrics(BaseModel):
    """Post-execution effectiveness metrics."""
    
    time_to_execution_hours: Optional[float]
    execution_success: Optional[bool]
    roi_achieved: Optional[float]
    owner_satisfaction: Optional[int]    # 1-5
    would_recommend: Optional[bool]
```

---

## 📋 Decision Status Lifecycle

```
┌─────────────┐
│  DETECTED   │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐
│ INVESTIGATING│────►│  CANCELLED  │
└──────┬──────┘     └─────────────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐
│  EXPLAINED  │────►│   EXPIRED   │
└──────┬──────┘     │  (7 dias)   │
       │            └─────────────┘
       ▼
┌─────────────┐
│   PENDING   │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐
│  EXECUTED   │────►│  DISMISSED  │
└──────┬──────┘     └─────────────┘
       │
       ▼
┌─────────────┐
│  CONFIRMED  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   MEASURED  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   LEARNED   │ ◄──┐
└─────────────┘    │
                   │
              Feedback Loop
```

### Status Definitions

| Status | Descrição | Transição Automática |
|--------|-----------|----------------------|
| **DETECTED** | Anomalia identificada | Após trigger |
| **INVESTIGATING** | Análise em progresso | Após detect |
| **EXPLAINED** | Decisão formulada | Após investigate |
| **PENDING** | Aguardando execução | Após explain |
| **EXECUTED** | Ação realizada | Manual ou auto |
| **CONFIRMED** | Resultado registrado | Após execute |
| **MEASURED** | Impacto calculado | Após confirm |
| **LEARNED** | Alimentou algoritmos | Após measure |
| **CANCELLED** | Cancelada antes de execução | Manual |
| **DISMISSED** | Ignorada pelo owner | Manual |
| **EXPIRED** | Não executada em 7 dias | Auto após 7d |

---

## 🔍 Query Capabilities

### Filtros Suportados

```python
class DecisionQuery:
    """Query parameters for decision history."""
    
    # Time
    date_from: Optional[date]
    date_to: Optional[date]
    
    # Tenant
    tenant_id: Optional[str]
    empresa_codigo: Optional[str]
    
    # Category
    category: Optional[DecisionCategory]
    type: Optional[DecisionType]
    
    # Status
    status: Optional[DecisionStatus]
    execution_result: Optional[str]       # YES, NO, PARTIAL
    
    # Financial
    min_impact: Optional[float]
    max_impact: Optional[float]
    
    # Effectiveness
    executed: Optional[bool]
    successful: Optional[bool]
    
    # Source
    engine: Optional[str]
    endpoint: Optional[str]
    
    # Sorting
    sort_by: str = "created_at"
    sort_order: str = "desc"
    
    # Pagination
    limit: int = 50
    offset: int = 0
```

### Exemplos de Query

#### Decisões do Mês por Categoria
```json
{
  "date_from": "2026-06-01",
  "date_to": "2026-06-30",
  "category": "RISK",
  "status": "EXECUTED",
  "sort_by": "estimated_impact.amount",
  "sort_order": "desc",
  "limit": 10
}
```

#### Decisões Não Executadas
```json
{
  "executed": false,
  "status": "EXPIRED",
  "date_from": "2026-01-01",
  "limit": 100
}
```

#### Maiores Impactos
```json
{
  "min_impact": 5000,
  "execution_result": "YES",
  "sort_by": "actual_impact.verified_amount",
  "limit": 20
}
```

---

## 📊 Analytics Queries

### Aggregation Examples

#### Por Categoria
```sql
SELECT 
  category,
  COUNT(*) as total,
  SUM(estimated_impact.amount) as estimated_total,
  SUM(actual_impact.verified_amount) as actual_total,
  AVG(confidence_score.overall) as avg_confidence,
  COUNT(CASE WHEN execution.confirmation.result = 'YES' THEN 1 END) as executed
FROM decisions
WHERE tenant_id = 'tenant_001'
  AND created_at >= '2026-06-01'
GROUP BY category
```

#### Por Engine
```sql
SELECT 
  source_engine,
  COUNT(*) as decisions_generated,
  AVG(execution.time_to_execution_hours) as avg_time_to_exec,
  SUM(actual_impact.verified_amount) as total_impact
FROM decisions
WHERE status IN ('CONFIRMED', 'MEASURED', 'LEARNED')
GROUP BY source_engine
ORDER BY total_impact DESC
```

#### Tendência Temporal
```sql
SELECT 
  DATE_TRUNC('week', created_at) as week,
  COUNT(*) as decisions,
  SUM(CASE WHEN execution.confirmation.result = 'YES' THEN 1 ELSE 0 END) as executed,
  SUM(actual_impact.verified_amount) as weekly_impact
FROM decisions
WHERE created_at >= NOW() - INTERVAL '3 months'
GROUP BY week
ORDER BY week
```

---

## 🔌 API Endpoints

### GET /api/v1/decisions

**Query parameters:** Todos os filtros do DecisionQuery

**Response:**
```json
{
  "total": 42,
  "limit": 10,
  "offset": 0,
  "decisions": [
    {
      "decision_id": "dec_001",
      "title": "Cobrar cliente inadimplente",
      "category": "RECOVERY",
      "status": "CONFIRMED",
      "estimated_impact": {
        "amount": 8500.00,
        "currency": "BRL"
      },
      "actual_impact": {
        "verified_amount": 8500.00,
        "measured": true
      },
      "execution": {
        "executed_at": "2026-06-15T09:30:00Z",
        "confirmation": {
          "result": "YES"
        }
      },
      "created_at": "2026-06-15T08:00:00Z"
    }
  ]
}
```

### GET /api/v1/decisions/{id}

**Response:** Decision completo com todos os campos.

### GET /api/v1/decisions/analytics

**Query parameters:** group_by, date_range

**Response:**
```json
{
  "group_by": "category",
  "results": [
    {
      "category": "RECOVERY",
      "count": 18,
      "estimated_total": 125000.00,
      "actual_total": 118000.00,
      "execution_rate": 0.94,
      "avg_confidence": 87
    },
    {
      "category": "RISK",
      "count": 12,
      "estimated_total": 89000.00,
      "actual_total": 85000.00,
      "execution_rate": 0.92,
      "avg_confidence": 91
    }
  ]
}
```

### POST /api/v1/decisions/{id}/confirm

**Request:**
```json
{
  "result": "YES",
  "actual_amount": 8500.00,
  "notes": "Cliente pagou via PIX"
}
```

---

## 💾 Storage Strategy

### Hot Store (Active Decisions)

```
Engine: PostgreSQL
Retention: 90 dias
Data: Active and recent decisions
Index: Full query capabilities
```

### Warm Store (Decision Archive)

```
Engine: PostgreSQL (partitioned)
Retention: 2 anos
Data: Decisions > 90 days
Index: Key fields only
```

### Cold Store (Deep Archive)

```
Engine: S3 / Object Storage
Retention: 7 anos (compliance)
Data: Compressed JSON
Access: Batch queries only
```

### Search Index

```
Engine: Elasticsearch / OpenSearch
Data: Key fields + full text
Use: Complex searches, analytics
```

---

## 🔄 Retention Policy

| Tier | Retention | Storage | Access |
|------|-----------|---------|--------|
| Hot | 90 dias | PostgreSQL | Real-time |
| Warm | 2 anos | Partitioned PG | < 1s |
| Cold | 7 anos | S3 | Batch |

### Auto-Transitions

```
Dia 0-90:     Hot Store (ativa)
Dia 91-730:   Warm Store (arquivo)
Dia 731+:     Cold Store (conformidade)
```

---

## 🔒 Security & Audit

### Audit Trail

Cada alteração em uma decisão gera:

```json
{
  "audit_id": "aud_001",
  "decision_id": "dec_001",
  "action": "STATUS_CHANGE",
  "from_value": "PENDING",
  "to_value": "EXECUTED",
  "performed_by": "user_001",
  "performed_at": "2026-06-15T09:30:00Z",
  "ip_address": "192.168.1.1",
  "user_agent": "LOGOS Web App"
}
```

### Permissions

| Role | Read | Write | Delete | Analytics |
|------|------|-------|--------|-----------|
| Owner | All own | Confirm | No | Full |
| Manager | All own | Confirm | No | Full |
| Auditor | All (read-only) | No | No | Full |
| System | All | System ops | Archive | Full |

---

## 📚 Referências

- [DECISION_EXECUTION_FLOW.md](../business/DECISION_EXECUTION_FLOW.md) — Fluxo de execução
- [DECISION_EFFECTIVENESS.md](../business/DECISION_EFFECTIVENESS.md) — Métricas
- [LOGOS_IMPACT_SCORE.md](LOGOS_IMPACT_SCORE.md) — Cálculo de impacto

---

**[DECISION HISTORY — Architecture]**

*Status: SPECIFIED | Retention: 7 years | Statuses: 11 | Queryable: Full-text*
