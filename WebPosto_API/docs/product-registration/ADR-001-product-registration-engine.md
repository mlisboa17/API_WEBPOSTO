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

## Estado da migração (final)

Executores operacionais de escrita (`execute_wave_118508`, `execute_microbatch_118508`, `execute_negresco_pilot_118508`, `execute_ready_products_118508`, `RegistrationExecutor`) não chamam o gateway nem `client.post` no endpoint legado. O único POST operacional é `ProductRegistrationService.post_product`.

`compatibility.py` adapta argumentos antigos e termina na fachada. `body_builder.py` permanece como adaptador deprecated: `get_default_bono_template()` devolve body vazio e não herda fiscal, custo ou grupo.

Locks históricos sem `status` são interpretados só na leitura (`interpret_lock`). Arquivos em `data/` não são reescritos. Novos locks exigem `status` explícito.

Esta migração não executa cadastro e não altera checkpoint 249.

## Extensões futuras

- `CostUpdate*` para PUT controlado de custo.
- `FiscalAudit*` e `AiFiscalAdvisorPort` para análise, nunca para regra silenciosa.
