# RECEIVABLE_ANALYSIS_MODEL — A03.7

**Registros TITULO_RECEBER:** 11
**Valor total:** R$ 176.31

## Situações

TITULO_RECEBER **não expõe campo `situacao`**. Usar:
- `pendente: true` → **11/11 pendentes** no período
- `dataPagamento: null` → não recebido
- `dataVencimento` → aging

**Vencidos estimados (período):** 11 (todos pendentes com vencimento ≤ 07/06/2026)

## Campos disponíveis

`empresaCodigo`, `tituloCodigo`, `dataMovimento`, `dataVencimento`, `valor`, `vendaCodigo`, `duplicataCodigo`, `tipo`, `pendente`, `clienteCodigo`, `dataPagamento`, `planoContaGerencialCodigo`, `nomeCliente`, `cpfCnpjCliente`, `convertido`, `documento`, `tituloNumero`, `codigo`

## Análises futuras (F05)

- Carteira por cliente
- Inadimplência aging (0-30, 31-60, 61+)
- DSO (Days Sales Outstanding)

**LOGOS hoje:** integrado = False — prioridade A04/F05
