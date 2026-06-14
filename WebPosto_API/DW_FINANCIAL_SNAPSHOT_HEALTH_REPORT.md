# DW_FINANCIAL_SNAPSHOT_HEALTH_REPORT

DDL: `dw/ddl/fact_financial_snapshot_health.sql`

Campos F08.1: snapshot_type, generated_at, health_score, confidence_level, age_hours, health_status

Linhas exportáveis (período): **4**

## Amostra

```json
[
  {
    "snapshot_key": "2026-06-01:2026-06-07:all",
    "snapshot_type": "financial_overview",
    "period_start": "2026-06-01",
    "period_end": "2026-06-07",
    "source": "live",
    "generated_at": "2026-06-13T19:44:49",
    "health_score": 97,
    "confidence_level": "ALTA",
    "age_hours": 0.44,
    "health_status": "HEALTHY",
    "record_count": 11,
    "lineage_preserved": true
  },
  {
    "snapshot_key": "2026-06-01:2026-06-07:all",
    "snapshot_type": "financial_expenses",
    "period_start": "2026-06-01",
    "period_end": "2026-06-07",
    "source": "live",
    "generated_at": "2026-06-13T19:45:38",
    "health_score": 99,
    "confidence_level": "ALTA",
    "age_hours": 0.43,
    "health_status": "HEALTHY",
    "record_count": 10,
    "lineage_preserved": true
  }
]
```

