# DIR-01C — Prestação Nominal Evidence Enrichment

**Decision ID:** `175da101-6f68-42f4-9d2b-9b42e6cedea2`  
**Posto:** POSTO DOZE FILIAL II · **empresaCodigo:** 74014  
**Período VALUE-03:** 2026-06-05 a 2026-07-04

## 1. Fonte nominal usada

| Camada | Componente | Papel |
|--------|------------|-------|
| API (existente) | `PrestacaoContasIntelligenceService.vale_forensics` | Auditoria — vales consolidados sem `funcionarioCodigo` linha a linha |
| Markdown (novo) | `prestacao_nominal_extractor.load_prestacao_nominal_items` | Extração da seção **Vale de Funcionários** |
| Arquivo | `NewWebLogos/docs/validation/RAW_DATA_POSTO_DOZE_2026-06.md` | Export do PDF `Prestação de ContasDOzeReal.pdf` |
| Período do arquivo | 01/06/2026 — 28/06/2026 | Sobrepõe parcialmente VALUE-03 (junho) |

**Contrato:** `NominalEvidenceItem` com `source=PRESTACAO_CONTAS`, `financial_nature=VALE_FUNCIONARIO`, `capture_origin=ACCOUNTABILITY_REPORT`.

## 2. Prestação correta para 74014

**SIM** — localizada via `empresaCodigo=74014` no markdown; **não** foi usado PDF/markdown de outro posto (5555/VIP).

## 3. Cobertura antes / depois

| Métrica | Antes (DIR-01B) | Depois (DIR-01C) |
|---------|-----------------|------------------|
| EXACT | 0 | 0 |
| PROBABLE | 3 | 3 |
| AMBIGUOUS | 0 | 3 |
| NO_MATCH | 13 | 10 |
| Com beneficiário (qtd) | 3 | 3 |
| Valor identificado | R$ 450 | R$ 450 |
| Valor sem beneficiário | R$ 7.951 | R$ 7.951 |
| Cobertura por qtd | 18,8% | 18,8% |
| Cobertura por valor | 5,4% | 5,4% |

**Itens nominais extraídos da Prestação:** 13 funcionários (totais mensais de vale).

**Efeito DIR-01C:** os 3 lançamentos de R$ 1.000 passaram de `NO_MATCH` para `AMBIGUOUS` (1 funcionário na Prestação × 3 lançamentos financeiros), **sem** atribuir beneficiário — evita match forçado.

## 4. Limitações

- Seção **Vale de Funcionários** da Prestação é **agregado mensal por funcionário**, não espelho dos 16 lançamentos financeiros consolidados (150, 40, 1150, 1931…).
- Julho/2026 (fim de VALUE-03) não está no markdown disponível.
- `funcionario_codigo` permanece `null` na Prestação markdown (apenas nome).
- Match Prestação só roda após falha CAIXA; matches CAIXA existentes não são sobrescritos.

## 5. Riscos

- Atribuir totais mensais a lançamentos diários geraria falsa precisão — mitigado com regra de ambiguidade quando `same_financial > 1`.
- Uso indevido da Prestação como “prova de pagamento” — mitigado com disclaimer na API/UI.

## 6. Prestação ≠ prova financeira externa

A Prestação de Contas reflete o **relatório operacional de accountability** exportado do WebPosto. Ela **não** confirma crédito bancário, **não** substitui extrato/conciliação externa e **não** encerra conferência. Nesta etapa serve **apenas** para enriquecer identidade nominal (`person_name`), mantendo `review_responsible=null`.

## Arquivos alterados

- `src/services/decision_evidence/models.py`
- `src/services/decision_evidence/prestacao_nominal_extractor.py` (novo)
- `src/services/decision_evidence/nominal_matcher.py`
- `src/services/decision_evidence/nominal_enrichment_service.py`
- `frontend/pages/decisionDetail.js`
- `frontend/styles.css`
- `tests/unit/test_decision_evidence.py`
- `scripts/dir01c_nominal_prestacao_validation.py` (novo)

**Commits:** NENHUM (conforme escopo).
