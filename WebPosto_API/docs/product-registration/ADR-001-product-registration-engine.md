# ADR-001 — Motor reutilizável de cadastro

## Contexto

O cadastro da empresa 118508 foi comprovado em cinco ondas (checkpoint 249). A lógica estava espalhada em scripts de onda, o que impede reutilizar o mesmo motor em outra empresa sem copiar incidentes (empresa errada, CEST vazio como zero, reenvio após timeout).

## Decisão

Consolidar o comportamento comprovado em `src/operational/product_registration/` com fachada pública, políticas versionadas, CLI dry-run e adaptadores para os scripts antigos. Não reescrever o histórico nem reexecutar ondas.

## Alternativas

1. **Manter só scripts de onda.** Barato agora; cada empresa nova copia o risco.
2. **Reescrever do zero.** Alto risco de divergir do que já foi aceito pela API.
3. **Fachada sobre o código comprovado (escolhida).** Preserva comportamento, expõe contratos e deixa dívidas explícitas.

## Consequências

- Scripts 1-5 continuam importando módulos antigos.
- Body permanente não herda BONO/NEGRESCO.
- Escrita continua exigindo autorização explícita.
- Extensões de custo e auditor fiscal existem só como interface.

## Extensões futuras

- `CostUpdate*` para PUT controlado de custo.
- `FiscalAudit*` e `AiFiscalAdvisorPort` para análise, nunca para regra silenciosa.
