# DIR-01 — Decision Evidence Detail

**Sprint:** DIR-01  
**Objetivo:** Diretor vê lançamentos que sustentam a decisão prioritária.

## Fluxo

Home Diretoria (`?view=owner-diretoria`) → card → detalhe (`?view=decision-detail&decisionId=…`) → evidências → ações executivas (contrato UI).

## Caso VALUE-03 validado

| Campo | Valor |
|-------|-------|
| Posto | POSTO DOZE FILIAL II (74014) |
| Categoria | Vale de funcionário referente a consolidação de caixa |
| Atual | R$ 8.401 |
| Baseline | R$ 900 |
| Excesso | R$ 7.501 |
| Lançamentos | 16 |
| Confiança | 89% |

## Linguagem executiva

- Usar: "Estes lançamentos explicam o aumento acima do comportamento de referência."
- Evitar: acusação automática, "fraude", "perda confirmada".

## Ações executivas

Botões visíveis; backend de execução **não conectado** nesta sprint — mensagem honesta ao clicar.

## DIR-01C — Prestação nominal (complementar)

- Fonte: markdown `RAW_DATA_POSTO_DOZE_2026-06.md` (PDF `Prestação de ContasDOzeReal.pdf`, empresa **74014**).
- `person_name` = beneficiário · `review_responsible` = null (conferência ainda não atribuída).
- Prestação **não** é prova financeira externa — disclaimer na UI.
- Cobertura nominal por valor permanece **5,4%** (R$ 450 / R$ 8.401); 3 lançamentos R$ 1.000 reclassificados para **AMBIGUOUS** (sem atribuir beneficiário).

## DIR-01D — Solicitar conferência

CTA **Solicitar conferência** na tela de decisão → `POST /api/v1/decisions/{id}/review-requests`.

13 lançamentos (R$ 7.951) entram na solicitação; idempotência impede duplicata por duplo clique.
