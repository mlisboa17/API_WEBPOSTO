# NEXT EXECUTIVE VALUE — Data Audit

Período analisado: **2026-06-05 a 2026-07-04**  
Tenants: **5555** (AP CASA CAIADA), **11495** (POSTO VIP), **74014** (POSTO DOZE FILIAL II)

## Fontes já cobertas pelos detectores originais

| DATA_SOURCE | ENDPOINT | SERVICE_AVAILABLE | TENANTS_WITH_DATA | DATE_RANGE | RECORD_COUNT | FINANCIAL_FIELDS | DIMENSIONS | KNOWN_LIMITATIONS |
|---|---|---|---|---|---|---|---|---|
| Despesas ERP | `/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE` | YES | 5555, 11495, 74014 | 30d+30d baseline | 5555: ~300+, 11495: ~800+, 74014: ~400+ | valor, planoConta, data | categoria, tenant | Vale consolidação domina spike em 74014 |
| Títulos pagar | `/INTEGRACAO/TITULO_PAGAR` | YES | 11495, 74014 | 30d | variável | valor, fornecedor, vencimento | fornecedor | Poucos matches em 5555 |
| Recebíveis | `/INTEGRACAO/TITULO_RECEBER` | YES | 11495, 74014 | 30d | 11495: 50+ vencidos, 74014: 2 vencidos | valor, vencimento, pendente | cliente, aging | 5555 sem títulos no período |
| Vendas cartão | `/INTEGRACAO/VENDA_FORMA_PAGAMENTO` | YES | 11495, 74014 | 30d | variável | valor, formaPagamento | modalidade | Sem NSU/TEF — Level 1 |
| Combustível | `/api/v1/sales/fuel-summary` | YES | 3 tenants | 30d | 0 rows no período | receita, litros | produto | Dados vazios no período testado |

## Fontes auditadas mas NÃO exploradas por detectores (antes desta sprint)

| DATA_SOURCE | ENDPOINT | SERVICE_AVAILABLE | TENANTS_WITH_DATA | DATE_RANGE | RECORD_COUNT | FINANCIAL_FIELDS | DIMENSIONS | KNOWN_LIMITATIONS |
|---|---|---|---|---|---|---|---|---|
| NF fornecedor (planoConta REF NF) | `/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE` | YES | 11495, 74014 | 30d+30d | 11495: 8+ REF NF ≥R$1.5k | valor, planoConta (NF embutida) | fornecedor, NF | ExpenseDetector penaliza lançamento único (conf ~46%) |
| Mix não-combustível | `/INTEGRACAO/VENDA`, `/INTEGRACAO/VENDA_ITEM` | YES | 11495, 5555 | 2026-06-01–28 | 11495: R$1.104 conv., 5555: 0% mix | receita, participação% | filial, departamento | Oportunidade ~R$110 em 5555 — baixa exposição |
| Caixa/quebra | `CAIXA_REDE+CAIXA+CAIXA_APRESENTADO` | YES | rede | 2026-06-01–10 | diferencaTotalRede=0 | quebra, turno | operador, PDV | Sem sinal financeiro no período |
| Estoque / LMC / margem DRE | vários (cockpits F07/F08) | PARTIAL | rede ampla | períodos heterogêneos | incompleto para 3 tenants | margem, estoque | produto | Sem snapshot homogêneo 2026-06-05–07-04 para os 3 postos |
| Concentração recebíveis | `/INTEGRACAO/TITULO_RECEBER` | YES | 74014 | 30d | 2 títulos | valor pendente | cliente | 66% em F.J. SERVICOS — já em evidence CardReceivable, não em título executivo |

## Lacuna identificada (gap executivo)

**ExpenseDetector** trata REF NF como `CATEGORY_SPIKE` genérico e exige volume de lançamentos para confidence.  
NFs novas de alto valor (ex.: SOUZA CRUZ R$ 5.979) ficam **abaixo de 80% confidence** e **não aparecem** na Visão da Rede — embora sejam rastreáveis por número de NF.

**5555** permanece sem decisão: spikes locais (FARDAMENTOS R$ 1.777, ALELO R$ 1.584) abaixo do piso de R$ 5.000 para decisão.

## Conclusão da auditoria

A próxima classe de valor com dados reais suficientes e ação diretoria é **despesa de fornecedor via NF sem histórico no baseline** — distinta de vale de consolidação e de recebíveis vencidos já exibidos.
