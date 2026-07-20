# Sprints 12, 13 e 14 — Operação da DRE Departamental

## Sprint 12 — Tela de classificação

- Fila de despesas sem departamento no Centro Financeiro.
- Empresa, data, valor e código do plano visíveis.
- Seleção entre Combustíveis, Conveniência e Lubrificantes.
- Responsável e justificativa obrigatórios.
- Reprocessamento da conciliação após salvar.

## Sprint 13 — Regras permanentes

- Opção “Reutilizar plano” cria regra por `planoContaGerencialCodigo`.
- Regra registra departamento, responsável, justificativa, data e estado ativo.
- Precedência: revisão manual do fato → regra do plano → evidência textual → quarentena.
- Endpoint `GET /api/v1/finance/director-reconciliation/department-rules`.
- Lançamentos futuros reutilizam decisões aprovadas.

## Sprint 14 — DRE completa

- Endpoint `GET /api/v1/finance/director-reconciliation/dre-complete`.
- Nove linhas obrigatórias: três empresas × três departamentos.
- Faturamento, custo, margem bruta, despesas, resultado e margem operacional.
- Cada linha informa evidências ausentes quando bloqueada.
- Nenhum zero é inventado para fonte ausente.
- Nenhum resultado genérico consolidado é produzido.
- A tela carrega a DRE completa somente quando a classificação das despesas estiver liberada.

## Gate de qualidade

- 20 testes focados aprovados.
- Sintaxe dos arquivos JavaScript validada.
