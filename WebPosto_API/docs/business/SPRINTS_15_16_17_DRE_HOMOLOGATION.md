# Sprints 15–17 — Homologação da DRE departamental

## Escopo fixo

- Empresas: `11495 POSTO VIP`, `5555 AP CASA CAIADA` e `74014 POSTO DOZE FILIAL II`.
- Departamentos independentes: Combustíveis, Conveniência e Lubrificantes.
- Resultado consolidado genérico é proibido.

## Sprint 15 — Homologação das despesas

As despesas pendentes são agrupadas por empresa e código do plano de contas. A decisão pode ser aplicada ao fato individual ou reutilizada como regra permanente para o mesmo código, sempre com responsável e justificativa.

A consulta oficial `/PLANO_DE_CONTAS` retornou `401` nas três licenças. Por isso, descrições não são presumidas e nenhuma classificação é aprovada automaticamente. No período real verificado existem 23 despesas aguardando decisão gerencial.

## Sprint 16 — Rateio compartilhado

Uma conta compartilhada pode receber percentuais separados para os três departamentos. Regras:

- a soma deve ser exatamente 100%;
- somente departamentos oficiais são aceitos;
- responsável e critério do rateio são obrigatórios;
- o rateio fica persistido e auditável pelo código da conta;
- cada parcela entra somente na linha departamental correspondente.

Precedência: revisão individual, rateio compartilhado, regra permanente de conta, evidência textual e quarentena.

## Sprint 17 — Validação e homologação formal

A validação exige nove linhas: três empresas multiplicadas por três departamentos. Para cada linha:

- `margem bruta = faturamento - custo`;
- `resultado operacional = margem bruta - despesas`;
- status deve ser `LIBERADO`.

A homologação registra período, responsável, justificativa, data UTC e hash SHA-256 do conteúdo validado. Qualquer fonte incompleta, despesa sem classificação ou divergência matemática bloqueia a aprovação.

## Estado atual

A infraestrutura das três sprints está pronta. A DRE real permanece corretamente bloqueada até a Diretoria classificar ou ratear as 23 despesas e todas as fontes de faturamento e custo passarem na cobertura integral.
