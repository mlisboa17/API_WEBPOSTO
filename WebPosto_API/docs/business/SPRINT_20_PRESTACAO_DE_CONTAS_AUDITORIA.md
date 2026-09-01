# Sprint 20 — Auditoria Periódica de Prestação de Contas

## Objetivo

Automatizar a conferência periódica que Diretores realizam a partir do relatório
WebPosto **Prestação de Contas**, mantendo revisão humana somente para divergências,
destinações sem evidência e aprovações formais.

O ciclo pode ser semanal ou a cada X dias, por empresa licenciada e por centro de
custo operacional. Existem duas prestações de contas independentes: **PISTA** e
**CONVENIÊNCIA**. O escopo é sempre separado entre Combustíveis, Conveniência e
Lubrificantes; nenhum total financeiro mistura centros de custo ou departamentos para
fins de DRE.

## Escopo obrigatório por centro de custo

| Prestação de contas | Centro de custo | Foco principal | Regra de apresentação |
|---|---|---|---|
| Pista | `PISTA` | abastecimentos, dinheiro de frentistas, sangrias, TEF/POS da pista, despesas de pista, vales e perdas de caixa | Combustíveis separados de Lubrificantes; itens de loja não entram como venda de pista sem evidência |
| Conveniência | `CONVENIÊNCIA` / `LOJA` | vendas de loja, dinheiro de caixa, cartões, despesas de loja, produtos, vales e estoque de conveniência | Combustíveis não entram; Lubrificantes só aparecem em bloco próprio quando o centro de custo comprovar a venda |

Se um lançamento não trouxer centro de custo comprovado, ele permanece em
`CENTRO_DE_CUSTO_PENDENTE`; nunca é distribuído automaticamente entre Pista e
Conveniência.

## Fonte de referência analisada

Relatório `Prestação de Contas — AP CASA CAIADA`, 01/07/2026 a 15/07/2026.

Blocos identificados:

- fechamento de caixa por meio de pagamento: apresentado, sangria, apurado e diferença;
- funcionários: total apresentado, apurado e diferença;
- despesas de caixa por plano e descrição;
- POS, TEF, pré-pago, cheque e transferência de crédito;
- vales, faltas e sobras por funcionário;
- movimento de conta diário;
- produtividade por funcionário;
- vendas por produto, combustível e grupo;
- detalhamento das sangrias.

## Fluxo do produto

1. Administrador configura a regra: empresa, centro de custo (Pista ou Conveniência),
   periodicidade (semanal ou X dias), responsável e data de corte.
2. O sistema cria um ciclo de auditoria e coleta os fatos WebPosto do período.
3. Opcionalmente o diretor anexa o PDF exportado pelo WebPosto; ele é guardado como
   evidência e comparado com os totais coletados, mas não substitui a fonte original.
4. O motor calcula testes e abre somente as pendências que requerem decisão humana.
5. O responsável confirma, justifica ou vincula evidência (extrato, comprovante de
   depósito, documento de despesa ou observação).
6. Diretor aprova, devolve ou encerra o ciclo. Toda decisão fica auditável.

## Testes automáticos

### Caixa e dinheiro

- apurado × apresentado × diferença por turno, dia e funcionário, sempre no mesmo
  centro de custo;
- dinheiro apresentado menos sangrias, despesas de caixa, vales e fundo de caixa;
- destino do dinheiro: banco, cofre, tesouraria, fundo de caixa ou despesa comprovada;
- depósito esperado × extrato bancário quando houver OFX/movimento identificado;
- caixa consolidado, não consolidado ou não informado.

### Despesas e vales

- despesa de caixa com plano, descrição, beneficiário, departamento e documento;
- vale, falta e sobra por funcionário;
- pagamentos duplicados ou sem comprovante;
- despesa zerada comprovada distinta de fonte indisponível;
- rateio compartilhado somente com regra aprovada.

### Recebimentos

- TEF/POS por administradora, modalidade e taxa esperada;
- cartões esperados × liquidações bancárias;
- transferência de crédito/PIX separada de faturamento;
- pré-pago, cheque e prazo com status próprio.

### Vendas e departamentos

- vendas por funcionário, produto, grupo e combustível, sempre no mesmo centro de
  custo;
- Combustíveis, Conveniência e Lubrificantes apresentados em blocos independentes;
- grupos DIVERSOS, COMODATO e USO E CONSUMO permanecem fora da DRE até decisão;
- vendas, CMV e despesas não são consolidados genericamente.

## Experiência do Diretor

Página `Auditorias periódicas`:

- calendário dos ciclos e status: em preparação, aguardando conferência, divergente,
  aprovado ou devolvido, com selo visível `PISTA` ou `CONVENIÊNCIA`;
- resumo executivo: faturamento ERP, caixa apurado, dinheiro a destinar, depósitos
  identificados, diferença de caixa, despesas pendentes e cartões a liquidar;
- checklist por exceção, ordenado por impacto financeiro;
- tela analítica por dia, funcionário, meio de pagamento, despesa e departamento;
- botões: confirmar, solicitar comprovante, informar destino, classificar, ratear,
  justificar, devolver e aprovar;
- trilha de auditoria completa e exportação da prestação de contas conferida.

## Regras de publicação

- um item automático pode ser marcado como `VALORES_COINCIDEM`, mas só recebe
  `CONFERIDO_MANUALMENTE` após ação do responsável;
- ausência de dado nunca equivale a zero;
- cartão ou crédito bancário nunca é faturamento;
- resultado departamental só é publicado com faturamento, CMV, despesas e cobertura
  comprovados;
- o sistema não faz lançamento financeiro nem baixa automática.

## Entregas técnicas

- modelos Pydantic para ciclo, checklist, evidência, achado e aprovação;
- regras de agendamento por empresa e periodicidade;
- adaptador de fatos WebPosto e importação opcional do PDF como evidência;
- APIs para abrir, consultar, registrar decisões e aprovar ciclos;
- tela executiva e tela analítica;
- testes unitários, integração e evidência de execução.

## Critérios de aceite

- diretor consegue abrir uma auditoria semanal de Pista ou Conveniência sem montar
  planilha manual;
- cada divergência mostra empresa, período, departamento quando aplicável, valor,
  fonte, responsável e ação sugerida;
- valores do PDF e fatos coletados apresentam diferença explicitamente quando houver;
- dinheiro diário pode ser vinculado ao destino e ao depósito correspondente;
- aprovação do ciclo exige justificativa para toda divergência aberta;
- o relatório final preserva evidências e não mistura departamentos.

## Situação em 24/07/2026

🔄 Camada de ciclos, checklist, resolução, aprovação, segurança da persistência,
idempotência e execução automática entregue. Seis ciclos semanais estão programados
para 27/07/2026. A experiência inicial está disponível na aba **Auditorias** de
`/app/departmental`.

Permanecem pendentes: upload governado do PDF, conciliação PDF × API, vínculo
nominal com depósitos/OFX e exportação do dossiê final.
