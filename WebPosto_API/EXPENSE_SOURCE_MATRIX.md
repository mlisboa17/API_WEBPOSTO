# EXPENSE SOURCE MATRIX — F03.1-B · Agente 0

## Matriz oficial de campos por origem de negócio

| Campo | Financeiro | Caixa | PDV | Tesouraria |
|-------|------------|-------|-----|------------|
| Valor | Sim — DESPESAS_REDE.valor | Sim — CAIXA_APRESENTADO.despesaApresentado | Sim — CAIXA_APRESENTADO.despesaApurado | Sim — MOVIMENTO_CONTA / TRANSFERENCIA_BANCARIA |
| Fornecedor | Parcial — DESPESAS_REDE + TITULO_PAGAR | Não — agregado por fechamento | Não — agregado por fechamento | Parcial — MOVIMENTO_CONTA |
| Plano Conta | Sim — planoContaGerencialDescricao | Não — inferido via match financeiro | Não — inferido via match financeiro | Parcial — quando disponível |
| Centro Custo | Parcial — frequentemente null (401 CENTRO_CUSTO_REDE) | Não | Não | Parcial |
| Operador | Parcial — quando presente no lançamento | Sim — funcionarioCodigo | Sim — funcionarioCodigo | Não |
| PDV | Parcial — quando vinculado | Sim — pdvCodigo | Sim — pdvCodigo | Não |
| Turno | Parcial | Sim — turnoCodigo / turno | Sim — turnoCodigo / turno | Não |

## Lacunas documentadas

- **Centro de Custo:** `CENTRO_CUSTO_REDE` retorna HTTP 401 em parte das filiais
- **Fornecedor operacional:** não existe no fechamento — inferido via match DESPESAS_REDE
- **Tesouraria:** MOVIMENTO_CONTA/TRANSFERENCIA consumidos para contexto; não alimentam tela de despesas diretamente
