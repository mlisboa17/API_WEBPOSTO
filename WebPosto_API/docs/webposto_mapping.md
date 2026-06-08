# Mapeamento Oficial WebPosto (Frontend x API)

Este documento centraliza as relações de chaves baseadas no retorno do endpoint oficial `/INTEGRACAO/EMPRESAS` para o frontend.
O objetivo é garantir consistência, tipagem e evitar "hardcodes" na aplicação.

## Mapeamento de Filiais

| empresaCodigo / codWeb (API) | Nome Fantasia (API/Local) | CNPJ (API/Local) | Base Local (Nro) |
| --- | --- | --- | --- |
| 5256 | POSTO BR SHOPPING | 07.018.760/0001-75 | 1 |
| 5333 | POSTO JANGA | 05.428.059/0002-80 | 2 |
| 5556 | POSTO CIDADE PATRIMONIO | 05.428.059/0001-07 | 3 |
| 5555 | AP CASA CAIADA | 04.284.939/0001-86 | 4 |
| 5557 | POSTO ENSEADA DO NORTE | 00.338.804/0001-03 | 5 |
| 5560 | POSTO SERTÃ | 04.274.378/0001-34 | 6 |
| 7 | POSTO REAL | 24.156.978/0001-05 | 7 |
| 5559 | POSTO RJ | 08.726.064/0001-86 | 8 |
| 9 | AUTO POSTO GLOBO | 41.043.647/0001-88 | 9 |
| 11495 | POSTO VIP | 03.008.754/0001-86 | 10 |
| 46433 | POSTO DOZE | 52.308.604/0001-01 | 11 |
| 74014 | POSTO DOZE FILIAL II | 52.308.604/0002-84 | 12 |

*(A numeração de `codWeb` que varia de pequenos digitos (ex: `7`, `9`) até ordens maiores é reflexo das limitações parciais de token antes da liberação do cadastro em rede).*

## Orientações de Tipo (OpenAPI / JSDoc)

Cada entidade deve referenciar a `empresaCodigo` e nunca apresentar esse código cru (sem nome) para o cliente. O mapeamento é resolvido antes via `resolveFilialFromRow` / `mergeFiliais`.

Sempre valide adições futuras com `validateResponse` ou com JSDocs criados em `frontend/types`.
