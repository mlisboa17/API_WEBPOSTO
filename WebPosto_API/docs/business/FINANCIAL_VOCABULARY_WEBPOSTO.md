# Vocabulário financeiro — WebPosto → Diretoria

## Regra central

O webposto CODEX não tratará **despesa**, **conta a pagar**, **sangria** e
**movimentação de conta** como sinônimos. A tela executiva mostrará o nome gerencial
e conservará a origem WebPosto para auditoria.

| Nome na Diretoria | Evidência WebPosto | Significado gerencial | DRE | Caixa/tesouraria |
|---|---|---|---|---|
| Despesas financeiras e operacionais | `CONSULTAR_DESPESAS_FINANCEIRO_REDE`: empresa, plano gerencial, documento, data e valor | Despesa classificada no financeiro | Sim | Confirmar por conciliação |
| Contas a pagar | `TITULO_PAGAR`: valor, valor pago, vencimento, pagamento e situação | Obrigação com fornecedor, aberta ou paga | Não somar automaticamente | Saída somente quando paga |
| Despesas pagas no caixa | `CAIXA_APRESENTADO`: despesa apurada, apresentada e diferença | Gasto registrado no fechamento do turno | Conciliar antes de somar | Sim |
| Sangrias (retiradas de numerário) | Nenhum campo direto confirmado | Dinheiro transferido do caixa para cofre/tesouraria | Não | Não altera o caixa consolidado |
| Suprimentos de caixa | `CAIXA_APRESENTADO.suprimentoCaixa` | Reforço de numerário no caixa | Não | Transferência interna |
| Movimentações de contas e tesouraria | `MOVIMENTO_CONTA`: débito/crédito, conta, origem e conciliação | Movimento financeiro, não necessariamente receita/despesa | Depende da origem | Sim |
| Fechamentos de caixa | `CAIXA` + `CAIXA_APRESENTADO` | Conferência do turno e do operador | Não | Evidência de auditoria |

## Linguagem proibida nas telas

- Não chamar sangria de despesa.
- Não chamar suprimento de receita.
- Não apresentar título em aberto como valor já pago.
- Não somar despesa de caixa e despesa financeira sem conciliação; pode ser o mesmo gasto.
- Não interpretar todo débito de conta como despesa ou todo crédito como receita.
- Não converter diferença/quebra de caixa automaticamente em despesa operacional.

## Separação obrigatória

Todos os valores devem preservar `empresaCodigo`, período, plano de contas/centro de
custo e departamento. A apresentação será independente para Combustíveis,
Conveniência e Lubrificantes. Registros sem vínculo departamental comprovado ficam em
**Não classificado / aguardando revisão**, fora dos comparativos departamentais.

## Pendência de fonte

O termo **sangria** existe hoje em regras heurísticas internas, mas ainda não foi
encontrado como campo explícito nos contratos consultados. Até localizar uma fonte
direta, a interface deve exibir “Sangria inferida” e informar a origem da inferência,
nunca contabilizá-la como despesa.

## Evidência de cobertura em 17/07/2026

- `pagina` e `tamanhoPagina` foram ignorados por `TITULO_PAGAR`, `MOVIMENTO_CONTA`,
  `CAIXA` e `CAIXA_APRESENTADO` nas três licenças.
- Páginas 1 e 2 devolveram os mesmos identificadores.
- `MOVIMENTO_CONTA` devolveu exatamente 200 registros e incluiu empresas fora das
  três licenças; a fonte aparenta ser de rede e pode estar truncada.
- Até existir estratégia de cursor ou particionamento por período que prove cobertura
  integral, totais derivados de `MOVIMENTO_CONTA` ficam bloqueados para a Diretoria.
