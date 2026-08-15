# Inventário de implementação — motor de cadastro

Estado registrado em 2026-08-15, commit inicial `cf3192cc00718ffb68a2c39caed5f08f0aef5148`.

Checkpoint comprovado: **249** registros em `data/product_registration/execution/checkpoint_118508.json`.

API writes nesta consolidação: **0**. Artefatos históricos de `data/product_registration/` não foram alterados.

## Locks das ondas

| Lote | status | reexecution | POSTs |
| --- | --- | --- | --- |
| wave_01_118508 | (legado, sem campo) | — | 11 |
| wave_02_batch_01 a _03 | (legado) | — | 20 / 10 / 20 |
| wave_02_batch_04 | COMPLETED | LOCKED | 32 |
| wave_02_batch_05 | COMPLETED | LOCKED | 1 |
| wave_03_batch_01 | COMPLETED | LOCKED | 9 |
| wave_04_batch_01 | COMPLETED | LOCKED | 65 |
| wave_05_batch_01 | COMPLETED | LOCKED | 57 |

## Commits relevantes

- `c5698b6` cadastro automático FASES 3-10
- `973407c` executor contínuo A-I
- `1c6d578` perfis fiscais reutilizáveis
- `1dc2a7b` payload fiscal, gates de GTIN, trilha
- `3dec351` checkpoint antes da fila
- `6e12274` / `cbe7c6b` qualificadores de modelo e conector
- `c8947ce` / `5aec7a2` esgotar ondas 2 e 4
- `b63d486` onda 3 sem CEST e retomada sem reenvio
- `cf3192c` onda final com risco assumido

## Módulos utilizados (domínio)

| Módulo | Papel |
| --- | --- |
| `company_credentials.py` | profile exato, sentinel, fingerprint |
| `ean_service.py` / `gtin_service.py` | GTIN |
| `duplicate_checker.py` / `final_wave.py` / `duplicate_detection.py` | duplicidade |
| `dfe_cost_resolver.py` | custo DF-e |
| `fiscal_resolver.py` / `fiscal_profiles.py` / `tax_table_matcher.py` | fiscal |
| `fiscal_sheet_loader.py` | NCM/CEST com zeros à esquerda |
| `body_builder.py` | deprecated; adaptador temporário; não herda BONO |
| `registration_body.py` | body permanente, sem herança silenciosa |
| `checkpoint_store.py` | legado FASE 4 |
| `stores.py` / `checkpoint_migration.py` | checkpoint v2 + leitura v1 |
| `registration_executor.py` / `post_verifier.py` | legado FASE 7-8 |
| `gateway.py` | POST CHAVE_ONLY + GET independente |
| `service.py` | orquestrador antigo |
| `registration_engine.py` | fachada permanente |
| `policies/` | decisões versionadas |

## Scripts

| Script | Situação |
| --- | --- |
| `execute_wave_118508.py` | ondas 1-5; POST só via fachada |
| `execute_microbatch_118508.py` | microbatch; POST só via fachada |
| `execute_negresco_pilot_118508.py` | piloto; POST só via fachada |
| `execute_ready_products_118508.py` | READY; body sem BONO; POST via fachada |
| `build_onda_final_118508.py` | montagem da onda 5; permanece |
| `build_fiscal_profiles_118508.py` | geração original; não rerodar no 257 |
| `build_onda3_no_cest_118508.py` | específico da onda 3 |
| `product_registration.py` | CLI permanente (dry-run) |

## Testes permanentes

- `test_company_credential_guard.py`
- `test_gtin_prefix_conflict.py` / `test_fabricated_gtin.py`
- `test_duplicate_classification.py` / `test_description_duplicates.py`
- `test_dfe_cost_policy.py` / `test_sale_unit_conversion.py` / `test_pending_dfe_cost_flag.py`
- `test_fiscal_resolver_st_evidence.py` / `test_icms_entry_rate_match.py` / `test_fiscal_profiles.py`
- `test_wave_executor.py` / `test_final_wave.py`
- `test_registration_engine.py` / `test_registration_golden_master.py`
- `test_registration_migration.py`

## Funções duplicadas (a unificar via fachada)

- `body_hash` em vários scripts → `RegistrationBodyBuilder.hash`
- `validate_cost` no executor de onda → `CostPolicy.evaluate`
- `paginate` / `barcodes` em scripts de build → gateway/reader
- `build_body` em `build_onda3` e `build_onda_final` → `RegistrationBodyBuilder`

## Funções específicas de uma onda

- `build_wave4_queue` / `wave4_category`
- `classify_final_duplicate` nasceu na onda final; agora é política permanente
- CEST omitido (onda 3) vira `cest_status=NOT_PROVIDED` no body builder

## O que deve ser reutilizável

Tudo que a fachada `ProductRegistrationService` expõe: preflight, register, verify, resume, status, políticas, stores, gateway e auditoria.
