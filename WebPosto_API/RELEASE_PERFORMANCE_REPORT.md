# RELEASE PERFORMANCE REPORT — Release 2.0

**Data:** 2026-06-08 · Evidência: `scripts/f01_snapshot_miss_hit.json`, `PERFORMANCE_BASELINE_2_0.md`

---

## Benchmark Snapshot

| Métrica | Tempo | Meta | Status |
|---------|-------|------|--------|
| Snapshot **HIT** rede | **13,5 ms** | < 500 ms | ✅ |
| Snapshot **HIT** filial (11495) | **425,7 ms** | < 500 ms | ✅ |
| Snapshot **MISS** (cold) | **6,7 ms** (fromSnapshot false) | — | ⚠️ |
| First after refresh | **1102,5 ms** | background | ✅ |
| F01.4-D build direct | **~30 s** | background refresh | ✅ |

---

## Por módulo (estimativa warm path)

| Módulo | Latência típica | Fonte |
|--------|-----------------|-------|
| Finance Center (HIT) | 13–425 ms | Snapshot store |
| Cash Flow (HIT) | ~400 ms | `f01_2_cash_flow_results.json` |
| Supplier Intelligence | Incluso no intelligence snapshot | TTL 300s compartilhado |
| Supplier Segmentation | Incluso no intelligence snapshot | Build ~30s MISS |
| Intelligence Advanced | Paralelo no `collect()` | F01.4-B fix ordem tasks |

---

## Respostas obrigatórias

### 1. Tempo médio

| Cenário | Médio |
|---------|-------|
| HIT rede (produção esperada) | **~15 ms** |
| HIT filial | **~425 ms** |
| MISS + refresh background | **~1,1 s** first paint; refresh async |

### 2. Gargalos restantes

| # | Gargalo | Impacto | Prioridade |
|---|---------|---------|------------|
| 1 | Build segmentation MISS (~30s) | Primeira carga filial | P1 — já async |
| 2 | Token WebPosto 2/11 filiais | Cobertura rede | P0 externo |
| 3 | HIT filial 425ms vs rede 13ms | UX multiselect grande | P2 |
| 4 | Snapshots JSON versionados | Tamanho repo / clone | P2 |
| 5 | pytest `--cov` sem plugin | CI friction | P3 |

### 3. Prioridades futuras

1. Redis cache distribuído (A04)
2. Pré-aquecimento snapshot rede no startup
3. Compressão snapshot store
4. Métricas Prometheus (`src/metrics/collector.py` — expandir)
5. Gate CI performance (< 500ms HIT)

**Veredito performance:** **APROVADO** para Release 2.0 funcional.
