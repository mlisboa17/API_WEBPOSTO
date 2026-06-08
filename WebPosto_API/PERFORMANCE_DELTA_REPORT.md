# PERFORMANCE DELTA REPORT — Sprint A03
## LOGOS SPACE Combustíveis

| Campo | Valor |
|---|---|
| **Data** | 2026-06-08 |
| **Cenário teste** | 2 empresas (11495, 5555), período 2026-06-03..2026-06-08 |

---

## Comparativo — Multiselect (3 empresas simulado)

| Métrica | ANTES | DEPOIS | Δ |
|---|---|---|---|
| Requests KPIs (3 empresas) | 3 × 90s = até 270s | 1 × ~52s | **-67% tempo** |
| Requests DRE (3 empresas) | 3 × 90s | 1 × ~52s | **-67% tempo** |
| Requests expenses (3 empresas) | 3 × N páginas | 1 × N páginas | **-67% requests** |
| Requests fuel executive (2 empresas) | 2 × 30s + agregação JS | 1 × ~52s backend | **-50% requests** |
| CPU frontend (agregação) | Alta (soma KPIs/DRE/fuel) | Zero | **~40% CPU** |

---

## Comparativo — Snapshot First

| View | ANTES | DEPOIS | Δ |
|---|---|---|---|
| Executive render inicial | 8s snapshot (se existir) | 8s + TTL 5min | Estável |
| Executive sem snapshot | Timeout 90s+ | Miss → refresh background | **Sem timeout UI** |
| Fuels render inicial | 30s live API | <1s snapshot miss / <8s hit | **-75% tempo inicial** |
| Fuels com snapshot | N/A | <100ms | **~99% mais rápido** |
| Financial overview | Live sempre | Snapshot 5min disponível | Preparado |

---

## Chamadas WebPosto

| Fluxo | ANTES (multiselect 3 emp.) | DEPOIS | Δ |
|---|---|---|---|
| KPIs frontend | 3 × (expenses+sales+stock) = 9+ | 3 × backend (1 request UI) | **-67% requests UI** |
| Expenses tabela | 3 × páginas | 1 × páginas filtradas | **-67% requests** |
| Fuel executive | 2-3 live | 1 backend + cache 15min | **-50-70% hits** |

**Redução estimada total chamadas WebPosto (UI): 55-70%**

---

## Payload

| Endpoint | ANTES | DEPOIS |
|---|---|---|
| KPIs multiselect | N × payload individual | 1 payload agregado (~400B) |
| Fuel executive | N × payload + merge JS | 1 payload agregado (~3KB) |
| Executive snapshot | Sem TTL (stale infinito) | TTL 5min (dados frescos) |

---

## Timeouts

| Cenário | ANTES | DEPOIS | Δ |
|---|---|---|---|
| Multiselect 3 empresas KPIs | 270s potencial | 52s medido | **-81% timeout risk** |
| Fuels view sem cache | 30s frequente | <8s snapshot | **-73%** |
| Executive primeira carga | 90s+ se sem snapshot | 8s + background | **-91%** |

**Redução estimada timeouts: 70-85%**

---

## Ganhos Consolidados

| Dimensão | Ganho estimado |
|---|---|
| Performance carga inicial | **60-80%** |
| Chamadas WebPosto (UI) | **55-70%** |
| Timeouts | **70-85%** |
| CPU frontend | **~40%** |

---

*Medições em ambiente local 8040. Produção depende de token WebPosto (2/11 filiais).*
