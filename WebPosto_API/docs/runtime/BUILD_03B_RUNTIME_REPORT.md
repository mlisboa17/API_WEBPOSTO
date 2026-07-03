# BUILD-03B — Runtime Report (Multi-Tenant)

Data: 2026-07-03  
Período: 2026-06-26 a 2026-07-03  
Modo: API WebPosto real (sem mock)

## Descoberta de credenciais

| credential_alias | present | masked |
|---|---|---|
| WEBPOSTO_API_KEY_POSTO_VIP_RIO_DOCE | true | ****8fd7 |
| WEBPOSTO_API_KEY_POSTO_CASA_CAIADA | true | ****53a8 |
| WEBPOSTO_API_KEY_POSTO_DOZE_FILIAL_II | true | ****43c1 |

**credentials_detected:** 3

## Tenants descobertos (via `/INTEGRACAO/EMPRESAS`)

| tenant_id | tenant_name | empresa_codigo | credential_alias | status |
|---|---|---|---|---|
| 5555 | AP CASA CAIADA | 5555 | WEBPOSTO_API_KEY_POSTO_VIP_RIO_DOCE | VALIDATED |
| 11495 | POSTO VIP | 11495 | WEBPOSTO_API_KEY_POSTO_VIP_RIO_DOCE | VALIDATED |
| 74014 | POSTO DOZE FILIAL II | 74014 | WEBPOSTO_API_KEY_POSTO_DOZE_FILIAL_II | VALIDATED |

**Nota de runtime:** token VIP Rio Doce é token de **rede** — retorna 2 empresas (5555 + 11495). Credencial Casa Caiada retorna as mesmas empresas e foi deduplicada. Isso confirma: **token ≠ tenant**.

**tenants_discovered:** 3  
**tenants_validated:** 3  
**tenants_failed:** 0

## Análise por tenant

| tenant | detector | tempo (ms) | candidates | decisions | observations | status |
|---|---|---:|---:|---:|---:|---|
| AP CASA CAIADA (5555) | FuelRevenueDetector | 79.542 | 0 | 0 | 0 | ANALYZED |
| POSTO VIP (11495) | FuelRevenueDetector | 61.023 | 0 | 0 | 0 | ANALYZED |
| POSTO DOZE FILIAL II (74014) | FuelRevenueDetector | 60.649 | 0 | 0 | 0 | ANALYZED |

**requests_count por tenant:** 2 (fuel-summary período atual + anterior)

## Agregação global

| métrica | valor |
|---|---|
| execution_time_ms (total) | 205.490 |
| monitoring_state | NORMAL |
| analysis_status | ANALYSIS_COMPLETE_NO_PRIORITY |
| decisions | 0 |
| observations | 0 |
| candidates_found | 0 |
| detectors_executed | ["FuelRevenueDetector"] |

## analysis_proof (estrutura)

```json
{
  "tenant_count": 3,
  "tenant_ids": ["5555", "11495", "74014"],
  "tenants_analyzed": 3,
  "tenants_failed": 0,
  "credentials_detected": 3,
  "period_analyzed": { "start": "2026-06-26", "end": "2026-07-03" }
}
```

## Performance

| tenant | ms |
|---|---:|
| 5555 | 79.542 |
| 11495 | 61.023 |
| 74014 | 60.649 |
| **total** | **205.490** |

Execução sequencial. Paralelização não habilitada.

## Estado esperado da Home

- monitoring_state: NORMAL
- Mensagem: "Análise concluída. Nenhuma ação prioritária..."
- Áreas verificadas: Vendas de combustível — **3 postos analisados**
- POSTO VIP, AP CASA CAIADA, POSTO DOZE FILIAL II — Analisado

## BUILD-03 vs BUILD-03A — candidatos R$ 4.200 / 72%

**Causa comprovada:** **B + C** — período/dataset atual sem queda ≥ R$ 5.000; análise limitada a VIP na BUILD-03A. Nenhum candidato no ERP para o período 2026-06-26..2026-07-03 nos 3 postos.
