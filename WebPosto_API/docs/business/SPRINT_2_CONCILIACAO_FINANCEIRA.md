# Sprint 2 — Conciliação Financeira

## Objetivo

Impedir dupla contagem e separar obrigação, despesa, pagamento e movimentação de
tesouraria antes da DRE da Diretoria.

## Progresso em 17/07/2026

- Vocabulário WebPosto → Diretoria formalizado.
- Contratos Pydantic dos fatos e estados de conciliação implementados.
- Motor conservador implementado: confirmado, provável, sem correspondência,
  duplicidade e quarentena departamental.
- Páginas repetidas agora interrompem a coleta, evitando multiplicação silenciosa.
- Totais executivos ficam bloqueados quando a cobertura não está comprovada.

## Descoberta crítica de paginação

`TITULO_PAGAR`, `MOVIMENTO_CONTA`, `CAIXA` e `CAIXA_APRESENTADO` ignoraram
`pagina` e `tamanhoPagina` nas três licenças. As páginas 1 e 2 devolveram os mesmos
IDs. `MOVIMENTO_CONTA` retornou exatamente 200 registros e empresas fora das três
licenças, indicando resposta de rede potencialmente truncada.

## Próximo incremento

Particionar as consultas por empresa e por dia, validar unicidade dos IDs e comparar
a união diária com intervalos maiores. A cobertura só será marcada como completa
quando nenhuma partição atingir o teto e todos os registros pertencerem às três
empresas licenciadas após o filtro obrigatório.

## Critérios de aceite

- Nenhuma página repetida é somada.
- Nenhuma empresa fora de 11495, 5555 e 74014 entra nos resultados.
- Sangria e suprimento nunca entram na DRE.
- Correspondência provável não é publicada como despesa confirmada.
- Registro sem departamento fica em quarentena.
