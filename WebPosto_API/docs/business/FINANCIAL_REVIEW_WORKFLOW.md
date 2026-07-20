# Financial Review Workflow — fronteira Diretoria × Financeiro

## Fluxo atual (FIN-01 + FIN-02)

```
Diretoria detecta → solicita conferência → ExecutiveReviewRequest (REQUESTED)
                                              ↓
                         Financeiro abre "Conferências" (mesma request)
                                              ↓
                         FIN-01: leitura + detalhe
                                              ↓
                         FIN-02: assume responsabilidade (ASSIGNED)
                                              ↓
                         Diretoria vê "Responsável definido" (mesma request)
```

## Responsabilidades

| Etapa | Diretoria | Financeiro |
|-------|-----------|------------|
| Detectar / priorizar | ✅ | |
| Solicitar conferência | ✅ | |
| Acompanhar status executivo | ✅ | |
| **Receber na inbox** | | ✅ FIN-01 |
| **Ver itens pendentes** | | ✅ FIN-01 |
| **Atribuir responsável** | | ✅ FIN-02 |
| Conferir / anexar / responder | | 🔜 FIN-03+ |
| Concluir solicitação | | 🔜 FIN-03+ |

## FIN-01 explicitamente NÃO faz

- Assumir conferência
- Atribuir responsável
- Marcar conferido
- Anexar comprovante
- Responder Diretoria
- Concluir workflow

## FIN-02 faz

- POST assign com `responsible_name` explícito
- REQUESTED → ASSIGNED
- Reflexo automático na projeção Diretoria (sem sincronização)

## FIN-02 explicitamente NÃO faz

- Conferir lançamentos
- Anexar comprovantes
- Concluir / responder Diretoria

## Empty state honesto

> "Nenhuma conferência aguardando análise."

Não afirma saúde financeira nem ausência de divergências.
