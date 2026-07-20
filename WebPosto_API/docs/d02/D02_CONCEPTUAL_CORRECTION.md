# D02 — Reconstrução da Prestação e Pré-Conferência Interna

## Classificação oficial

| Antes (incorreto) | Agora (correto) |
|---|---|
| Conferência Financeira final | **Reconstrução da Prestação e Pré-Conferência Interna** |
| Financeiro validado | **Consistência interna verificada** |
| Dinheiro/cartões conferidos | **Prestação reconstruída · pendente de fonte externa** |

## O que a D02 faz

A D02 **reconstrói** totais e diferenças da Prestação de Contas a partir de **fontes internas** do WebPosto/API (CAIXA_APRESENTADO, VFP, DESPESAS, MOVIMENTO_CONTA, etc.) e compara com a **expectativa** registrada na Prestação/PDF do WebPosto.

Isso valida **consistência operacional interna** (operador × sistema × prestação), **não** recebimento financeiro externo.

## O que a D02 não faz

- Não comprova que dinheiro está no cofre ou no banco.
- Não comprova liquidação de cartões na adquirente.
- Não comprova PIX/transferência no extrato bancário.
- Não comprova vales na folha/saldo/desconto.
- Não substitui comprovante/autorização de despesa.
- **Não fecha auditoria** — apenas prepara a fila do que ainda exige evidência externa.

## Regras de fonte (expectativa × evidência)

| # | Natureza / tema | Expectativa (interna) | Evidência externa obrigatória para conferência real |
|---|---|---|---|
| 1 | **Toda a D02** | WebPosto / PDF Prestação | — (expectativa, não prova) |
| 2 | **Conferência financeira real** | — | Fonte externa independente do operador |
| 3 | **Dinheiro** | CAIXA_APRESENTADO (apresentado/apurado) | Banco, cofre, conferência física |
| 4 | **Cartões** | CAIXA_APRESENTADO + VFP | Adquirente, portal de cartões, NSU quando aplicável |
| 5 | **PIX / transferência** | transfBanc* / MOVIMENTO_CONTA (parcial) | Extrato bancário |
| 6 | **Vales** | valeFun* / DESPESAS / ledger interno | Folha, saldo, desconto futuro |
| 7 | **Despesas** | despesa* / DESPESAS | Comprovante, autorização |
| 8 | **Auditoria** | Só após Δ entre expectativa e evidência externa | Audit Signal = revisão recomendada, não acusação |

## Linguagem permitida vs proibida

### Proibido

- conferência concluída
- dinheiro conferido
- cartões conferidos
- financeiro validado
- D02 substitui a conferência manual (sem qualificação)

### Permitido

- prestação reconstruída
- pré-conferência realizada
- consistência interna verificada
- pendente de fonte externa
- AUTO_MATCHED = coerência interna dentro da tolerância (não prova banco/adquirente)
- DIVERGENT / NEEDS_REVIEW = fila para conferência humana com evidência externa

## Relação com o relatório de paridade (POSTO VIP)

Métricas como **apresentado MATCH 100%** significam: LOGOS leu a mesma expectativa da Prestação via API.

Métricas como **sangria SOURCE_GAP**, **apurado Δ R$ 8.006,36** ou **0,02% MATCH centavo por natureza** significam: a reconstrução interna **não fechou** nem substitui validação externa.

Os **14/14 checks runtime** provam **fluxo funcional** (API, UI, justify, signals) — **não** paridade de recebimento financeiro externo.

## Pergunta direta

### “D02 substitui a conferência manual?”

**NÃO.**

Ela **prepara** a conferência: reconstrói a prestação, classifica itens (AUTO_MATCHED / NEEDS_REVIEW / DIVERGENT), gera sinais de revisão e registra justificativas.

A **validação definitiva** ainda exige cruzamento com **banco, adquirente, comprovantes, folha e demais fontes externas** — etapa posterior à D02.

## Documentos D02 afetados

Todos os arquivos em `docs/d02/` passam a usar esta classificação. O rótulo de UI **Executivo › Conferência** permanece operacional, mas o escopo documentado é **pré-conferência interna**, não fechamento financeiro.
