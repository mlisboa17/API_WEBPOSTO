# Director Value Demo — Runtime Validation

## Result

Director network view validated with real multi-tenant analysis, observations, follow-up and FIN-03 progress.

## Runtime

- Worktree: `Api_WebPosto/WebPosto_API`
- Branch: `feature/director-value-demo`
- Frontend: `WebPosto_API/frontend` @ `/app/financial`
- API port used: `127.0.0.1:8046` (updated stack; restart required on 8040)
- Home route: `?view=owner-diretoria&dataInicial=2026-06-05&dataFinal=2026-07-04`

## Network snapshot

| Campo | Valor |
|-------|-------|
| Tenants analyzed | 3 |
| Detectors | FuelRevenueDetector, ExpenseDetector, CardReceivableDetector |
| Priority tenant | POSTO DOZE FILIAL II |
| Priority amount | R$ 11.251,50 (ESTIMATED — API runtime) |
| Observations | 2 (CardReceivableDetector) |
| Follow-up request | `d7ff3eae-b846-4bbb-8e7b-1b49841afbf1` |
| Responsible | Marcio de Lima |
| FIN-03 progress | 3/13 (23,08%) |

## Journey (Playwright)

| Step | OK |
|------|----|
| HOME Visão da rede | yes |
| Priority hero visible | yes |
| Observations visible | yes |
| Follow-up on home | yes |
| Decision detail click | yes |
| Follow-up detail click | yes |

- Dead buttons: none detected
- False success states: none
- Mocks: none

## Limitations

- Decision evidence endpoint can take >30s on first load (nominal enrichment).
- Demo requires API restart to pick up follow-up progress fields on port in use.

## Regression

```text
31 passed, 22 warnings
```

Command:

```text
python -m pytest tests/unit/test_executive_follow_up.py tests/unit/test_financial_review_inbox.py tests/unit/test_financial_review_assignment.py -q --no-cov
```

Evidence JSON: `DIRECTOR_VALUE_DEMO_RUNTIME.json`
