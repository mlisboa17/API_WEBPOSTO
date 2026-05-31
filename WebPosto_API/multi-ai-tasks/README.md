# Divisão paralela de tarefas (3 IAs)

## Gemini 2.0 — Performance, Proxy & UI Lionda (40%)

- `src/presentation/app.py` — entrypoint unificado
- `dashboard_vendas.html` — shell OLED + CHAVE
- `theme/executive.js` — proxy `wpFetch`

**Checklist:** proxy `/api/webposto/proxy`, GZip, CORS, campo CHAVE, cockpit Lionda (`static/dashboard_logos.html` + `theme/cockpit.js`), cards semânticos (verde/azul/vermelho), CLS fixo.

## Claude 3.7 — Adelaide Tax & KPIs (40%)

- `src/domain/adelaide/` — catálogo combustíveis + `tax_profile.py`
- `src/application/usecases/fetch_executive_kpis.py`

**Checklist:** Decimal, Pydantic v2, `/api/v1/adelaide/metrics`, masking por role, graceful fallback + cache 60s.

## Grok 4 — Cache, Testes & Anomalias (20%)

- `src/infrastructure/cache/valkey_manager.py`
- `src/infrastructure/anomaly/caixa_anomaly.py`
- `tests/fix_suite.py`

**Checklist:** cache TTL 60s, `scripts/seed_real_data.py --prewarm`, prewarm startup, `redis_adapter`, anomalias caixa.

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
