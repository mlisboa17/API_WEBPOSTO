# Divisão paralela de tarefas (3 IAs)

## Gemini 2.0 — Performance, Proxy & UI Lionda (40%)

- `src/presentation/app.py` — entrypoint unificado
- `dashboard_vendas.html` — shell OLED + CHAVE
- `theme/executive.js` — proxy `wpFetch`

**Checklist:** proxy `/api/webposto/proxy`, GZip, CORS, campo CHAVE, zero CORS.

## Claude 3.7 — Adelaide Tax & KPIs (40%)

- `src/domain/adelaide/` — catálogo combustíveis + `tax_profile.py`
- `src/application/usecases/fetch_executive_kpis.py`

**Checklist:** Decimal, Pydantic v2, masking por role, graceful fallback.

## Grok 4 — Cache, Testes & Anomalias (20%)

- `src/infrastructure/cache/valkey_manager.py`
- `src/infrastructure/anomaly/caixa_anomaly.py`
- `tests/fix_suite.py`

**Checklist:** cache TTL 60s, testes 500/RetryError, health da chave.

## Setup local (30s)

```bash
cd WebPosto_API
docker compose up -d valkey
python -m pytest tests/unit -q
python src/presentation/app.py
```

URLs:

- `http://localhost:8000/health` — gateway
- `http://localhost:8000/dashboard` — cockpit Logos Space (Adelaide)
- `http://localhost:8000/` — dashboard operacional WebPosto
