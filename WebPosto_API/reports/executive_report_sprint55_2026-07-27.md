# Relatório Executivo Consolidado — Sprint 55
**Grupo Lisboa / LOGOS WebPosto**  
**Período:** 2026-07-01 a 2026-07-24  
**Gerado em:** 2026-07-27  
**Filiais monitoradas:** AP CASA CAIADA, POSTO VIP, POSTO REAL, POSTO DOZE FILIAL II

> **Regra de Ouro:** Apenas dados reais da base. Valores indisponíveis estão declarados explicitamente.

## 1. Análise Consolidada e Comparativa de Combustíveis (Pista)
**Status:** DISPONÍVEL
**Período:** 2026-07-01 a 2026-07-24
**Total litros:** 3.630,74 L
**Total valor:** R$ 22.421,52
**Total transações:** 400
**Observação:** Dados extraídos de /INTEGRACAO/ABASTECIMENTO para 400 abastecimentos. A API WebPosto retorna amostra limitada (até 400 registros por consulta de rede).

### Volume por produto
| Produto | Litros | Valor (R$) | Transações | % da Rede |
|---------|--------|------------|------------|-----------|
| GASOLINA | 1.697,46 | 11.776,15 | 234 | 52.52% |
| ETANOL ADITIVADO | 869,94 | 4.480,00 | 85 | 19.98% |
| NÃO CLASSIFICADO | 382,95 | 2.600,17 | 9 | 11.60% |
| GNV | 520,07 | 2.442,63 | 59 | 10.89% |
| DIESEL S10 | 80,84 | 565,05 | 4 | 2.52% |
| GASOLINA ADITIVADA | 79,49 | 557,52 | 9 | 2.49% |

### Volume por filial
| Filial | Litros | Valor (R$) | Transações | % da Rede |
|--------|--------|------------|------------|-----------|
| POSTO DOZE FILIAL II | 2.109,22 | 12.558,65 | 200 | 56.01% |
| POSTO VIP | 1.206,75 | 7.771,30 | 174 | 34.66% |
| AP CASA CAIADA | 314,78 | 2.091,57 | 26 | 9.33% |

### Ranking de filiais por volume
| Posição | Filial | Litros | Valor (R$) |
|---------|--------|--------|------------|
| 1 | POSTO DOZE FILIAL II | 2.109,22 | 12.558,65 |
| 2 | POSTO VIP | 1.206,75 | 7.771,30 |
| 3 | AP CASA CAIADA | 314,78 | 2.091,57 |

## 2. Movimentação e Transferências entre Filiais
**Status:** PARCIAL
| Tipo | Valor (R$) |
|------|------------|
| creditos | 5.808,66 |
| debitos | 41,04 |
| tarifas | 41,04 |
| transferencias | 5.808,66 |
| liquido | 5.767,62 |
**Observação:** Transferências bancárias detectadas no movimento de conta, mas não é possível determinar se são entre filiais da holding ou operações bancárias externas.

## 3. Margens por Filial e por Litro (R$/L)
**Status:** DISPONÍVEL
**Período:** 2026-07-01 a 2026-07-24
**Observação:** Faturamento por litro (receita/litro) calculado a partir de abastecimentos reais via /INTEGRACAO/ABASTECIMENTO. CMV/custo de reposição por litro não está disponível na base, impedindo margem bruta/operacional e EBITDA por litro.

### Faturamento por litro (R$/L)
| Filial | Litros | Valor (R$) | Receita/L | CMV/L | Margem Bruta/L |
|--------|--------|------------|-----------|-------|----------------|
| POSTO DOZE FILIAL II | 2.109,22 | 12.558,65 | 5,95 | Custo de reposição/CMV não disponível na API WebPosto | CMV não disponível |
| POSTO VIP | 1.206,75 | 7.771,30 | 6,44 | Custo de reposição/CMV não disponível na API WebPosto | CMV não disponível |
| AP CASA CAIADA | 314,78 | 2.091,57 | 6,64 | Custo de reposição/CMV não disponível na API WebPosto | CMV não disponível |

## 4. Conveniência (Loja - Foco em Todas as Filiais)
**Status:** DISPONÍVEL
**Período:** 2026-07-17 a 2026-07-23
**Receita total:** R$ 1.167,02
**Ticket médio:** R$ 11,01
**Itens / Unidades / Produtos distintos:** 106 / 147.0 / 67
**Observação:** Dados extraídos de /INTEGRACAO/VENDA_ITEM para todas as filiais licenciadas. Amostra da API para 2026-07-17 a 2026-07-23 retornou 1 filial com itens não-combustível após filtro de combustível. Casa Caiada e Doze tiveram apenas produtos combustíveis no retorno da API.

### Vendas por filial
| Filial | Receita (R$) | Itens | Unidades |
|--------|--------------|-------|----------|
| POSTO VIP | 1.167,02 | 106 | 147,00 |

### Top departamentos
| Departamento | Valor (R$) | Quantidade |
|--------------|------------|------------|
| NAO_CLASSIFICADO | 1.105,02 | 146,00 |
| 24555 | 62,00 | 1,00 |

### Top produtos
| Produto | Quantidade | Valor (R$) |
|---------|------------|------------|
| 1803621 | 16,00 | 104,00 |
| 1803739 | 10,00 | 91,10 |
| 1862860 | 10,00 | 87,50 |
| TOP AUTO 5W30 SQ SINT 1LT | 1,00 | 62,00 |
| 1803530 | 7,00 | 61,25 |

## 5. DRE Consolidada: Receita x Lucro x Despesas por Filial
**Status:** DISPONÍVEL
**Período:** 2026-07-01 a 2026-07-24
| Filial | Departamento | Confirmado (R$) | Matches | Não Match |
|--------|--------------|------------------|---------|-----------|
| AP CASA CAIADA | combustiveis | 3.265,00 | 3 | 115 |
| AP CASA CAIADA | conveniencia | 1.727,49 | 5 | 8 |
| AP CASA CAIADA | lubrificantes | 0,00 | 0 | 0 |
| AP CASA CAIADA | nao_classificado | 928,50 | 1 | 0 |
| POSTO VIP | combustiveis | 52.836,97 | 29 | 137 |
| POSTO VIP | conveniencia | 914,20 | 5 | 16 |
| POSTO VIP | lubrificantes | 0,00 | 0 | 0 |
| POSTO VIP | nao_classificado | 5.427,75 | 4 | 0 |
| POSTO DOZE FILIAL II | combustiveis | 7.995,00 | 2 | 66 |
| POSTO DOZE FILIAL II | conveniencia | 0,00 | 0 | 8 |
| POSTO DOZE FILIAL II | lubrificantes | 0,00 | 0 | 4 |
| POSTO DOZE FILIAL II | nao_classificado | 8.250,00 | 2 | 0 |
**Auto-classificação:** 130 despesas classificadas; 0 pendentes de revisão.
### Valor por categoria (auto-classificado)
| Categoria | Valor (R$) |
|-----------|------------|
| INSUMOS OPERACIONAIS | 26.890,95 |
| MANUTENÇÃO | 4.171,63 |
| PESSOAL/FOLHA | 2.900,00 |
| IMPOSTOS/TAXAS | 1.500,00 |
| LIMPEZA/HIGIENE | 230,00 |
| EQUIPAMENTOS/INFRAESTRUTURA | 129,78 |
| MATERIAIS/ESCRITÓRIO | 123,20 |
| MARKETING/PUBLICIDADE | 78,00 |
| ÁGUA/ESGOTO | 42,00 |
| COMBUSTÍVEL | 36,00 |
**Observação:** Valores 'confirmedDreAmount' são parcelas com evidência de departamento. A DRE completa está bloqueada por falta de CLASSIFICACAO_DESPESAS e FATURAMENTO/CUSTO em vários departamentos.

## 6. Análise Detalhada e Estruturada de Despesas
**Status:** DISPONÍVEL
**Período:** 2026-07-01 a 2026-07-24
**Total despesas gerenciais:** R$ 163.706,62

### Por categoria
| Categoria | Valor (R$) | % do Total |
|-----------|------------|------------|
| ADMINISTRATIVA | 200,00 | 0.12% |
| COMPRAS | 47.495,85 | 29.01% |
| OPERACIONAL | 15.413,28 | 9.42% |
| OUTROS | 15.493,97 | 9.46% |
| PESSOAL | 85.103,52 | 51.99% |

### Por filial
| Filial | Valor (R$) |
|--------|------------|
| AP CASA CAIADA | 25.032,90 |
| POSTO VIP | 83.877,64 |
| POSTO DOZE FILIAL II | 54.796,08 |

### Despesas auto-classificadas por palavra-chave
| Categoria | Valor (R$) |
|-----------|------------|
| INSUMOS OPERACIONAIS | 26.890,95 |
| MANUTENÇÃO | 4.171,63 |
| PESSOAL/FOLHA | 2.900,00 |
| IMPOSTOS/TAXAS | 1.500,00 |
| LIMPEZA/HIGIENE | 230,00 |
| EQUIPAMENTOS/INFRAESTRUTURA | 129,78 |
| MATERIAIS/ESCRITÓRIO | 123,20 |
| MARKETING/PUBLICIDADE | 78,00 |
| ÁGUA/ESGOTO | 42,00 |
| COMBUSTÍVEL | 36,00 |

### Contas a pagar
| Situação | Quantidade | Valor (R$) |
|----------|------------|------------|
| emAberto | 255 | 837.150,14 |
| vencido | 127 | 307.951,80 |
| pago | 99 | 1.554.361,82 |
| aVencer | 128 | 529.198,34 |

### Contas a receber
| Situação | Quantidade | Valor (R$) |
|----------|------------|------------|
| pendente | 23 | 3.180,65 |
| recebido | 0 | 0,00 |
| vencido | 16 | 2.068,96 |
| aVencer | 7 | 1.111,69 |

## 7. Relação de Eficiência: Vendas x Lucro x Despesas
**Status:** PARCIAL
**Período:** 2026-07-01 a 2026-07-24
**Observação:** Cálculos R$/L de custo de folha, despesa operacional e % lucro bruto consumido dependem de CMV e lucro bruto por litro, ainda indisponíveis.

| Filial | Receita/L | Custo Folha/L | Desp. Operacional/L |
|--------|-----------|---------------|---------------------|
| POSTO DOZE FILIAL II | 5,95 | Headcount e folha por litro indisponíveis | Despesas operacionais por litro indisponíveis |
| POSTO VIP | 6,44 | Headcount e folha por litro indisponíveis | Despesas operacionais por litro indisponíveis |
| AP CASA CAIADA | 6,64 | Headcount e folha por litro indisponíveis | Despesas operacionais por litro indisponíveis |

## 8. Indicadores Executivos de Eficiência Operacional
**Status:** PARCIAL
**Período:** 2026-07-01 a 2026-07-24
**Turnos analisados:** 96
**Despesa de caixa:** R$ 40.816,50
**Vale funcionário:** R$ 81.237,49
**Empréstimos:** R$ 0,00
**Observação:** Litros por frentista calculado a partir de abastecimentos reais. Headcount completo e faturamento por colaborador dependem de dados de pessoal.

### Top frentistas por litros abastecidos
| Funcionário | Litros | Transações |
|-------------|--------|------------|
| 299244 | 479,70 | 45 |
| 299252 | 339,67 | 19 |
| 251934 | 328,98 | 40 |
| 252430 | 299,21 | 39 |
| 299243 | 293,43 | 36 |
| 299254 | 279,29 | 30 |
| 299239 | 265,96 | 26 |
| 299249 | 250,02 | 27 |
| 294273 | 229,84 | 38 |
| 163694 | 202,81 | 40 |

## 9. Matriz de Anomalias e Desvios (Filiais Fora do Padrão)
**Status:** DISPONÍVEL
**Apurado:** R$ 724.369,54  **Apresentado:** R$ 724.097,07
**Conferido:** R$ 568.119,72  **Divergente:** R$ 11.792,47  **Pendente:** R$ 156.249,82

### Divergências por natureza de pagamento
| Natureza | Apurado (R$) | Apresentado (R$) | Diferença (R$) | Status |
|----------|--------------|------------------|----------------|--------|
| Dinheiro | 156.249,82 | 150.217,35 | -6.032,47 | DIVERGENT |
| Cheque à Vista | 0,00 | 5.760,00 | 5.760,00 | DIVERGENT |
| Cartão | 351.288,34 | 351.288,34 | 0,00 | AUTO_MATCHED |
| Despesa | 13.497,47 | 13.497,47 | 0,00 | AUTO_MATCHED |
| Vale Funcionário | 21.776,04 | 21.776,04 | 0,00 | AUTO_MATCHED |
| Transferência Crédito | 179.055,86 | 179.055,86 | 0,00 | AUTO_MATCHED |
| Notas | 2.152,01 | 2.152,01 | 0,00 | AUTO_MATCHED |
| Pré-pago | 200,00 | 200,00 | 0,00 | AUTO_MATCHED |
| Cheque Pré | 150,00 | 150,00 | 0,00 | AUTO_MATCHED |

### Detalhamento de pagamentos (VENDA_FORMA_PAGAMENTO)
| Natureza | Valor (R$) | Transações |
|----------|------------|------------|
| CARTÃO | 8.176,38 | 155 |
| DINHEIRO | 4.503,71 | 100 |
| PIX | 4.384,21 | 125 |
| TEF | 472,12 | 17 |

### Rombo de caixa por operador/turno (DINHEIRO + CHEQUE + PIX + CARTÃO)
| Funcionário | Turno | Dinheiro (R$) | Cheque (R$) | PIX (R$) | Cartão (R$) | Transações |
|-------------|-------|---------------|-------------|----------|-------------|------------|
| 299242 — NÃO INFORMADO | 1º TURNO | 3.046,58 | 0,00 | 2.330,77 | 6.081,47 | 197 |
| 276288 — NÃO INFORMADO | 1º TURNO | 1.288,60 | 0,00 | 1.647,89 | 1.863,44 | 179 |
| 158924 — NÃO INFORMADO | 1º TURNO | 168,53 | 0,00 | 405,55 | 231,47 | 21 |

### Alertas executivos recentes
| Severidade | Categoria | Mensagem |
|------------|-----------|----------|
| CRITICO | FILIAL | Filial crítica: FILIAL 5333 |
| CRITICO | ROI | Financial Score abaixo do limiar executivo |
| ALTO | PDV | PDV crítico: 54193 |
| ALTO | TURNO | Turno crítico: 1º Turno |
| ATENCAO | OPERADOR | Operador crítico: 299151 |

## 10. Rankings Gerenciais Consolidados
**Status:** PARCIAL
### Ranking por despesa gerencial (maior → menor)
| Posição | Filial | Valor (R$) |
|---------|--------|------------|
| 1 | POSTO VIP | 83.877,64 |
| 2 | POSTO DOZE FILIAL II | 54.796,08 |
| 3 | AP CASA CAIADA | 25.032,90 |

### Ranking por volume de combustível (maior → menor)
| Posição | Filial | Litros | Valor (R$) |
|---------|--------|--------|------------|
| 1 | POSTO DOZE FILIAL II | 2.109,22 | 12.558,65 |
| 2 | POSTO VIP | 1.206,75 | 7.771,30 |
| 3 | AP CASA CAIADA | 314,78 | 2.091,57 |
**Observação:** Rankings de receita total, lucro líquido, custo operacional/litro e faturamento/folha dependem de dados ainda indisponíveis (CMV, lucro bruto).

## 11. Conclusão Executiva para Tomada de Decisão (30 segundos)
**Status:** BASEADA_EM_DADOS_REAIS
**Filial com menor pressão de custos:** AP CASA CAIADA (menor despesa gerencial: R$ 25.032,90)
**Filial com maior pressão de custos:** POSTO VIP (maior despesa gerencial: R$ 83.877,64)
### Custos operacionais críticos
- Despesas gerenciais de PESSOAL representam 51,99% do total (R$ 85.103,52 / R$ 163.706,62)
- Divergências de caixa não justificadas: R$ 12111.69 em 21 itens
- Score financeiro executivo: 30.0 — diagnóstico: PERDENDO
- Volume de combustível real: 3.630,74 L / R$ 22.421,52 — POSTO DOZE FILIAL II lidera
- Auto-classificação de despesas: 130 itens classificados (R$ 36.101,56); 0 ainda pendentes de revisão manual
### Ações urgentes
- Habilitar carga contínua de abastecimentos via /INTEGRACAO/ABASTECIMENTO para cobertura completa do período (API limita a ~400 registros/consulta).
- Revisar as 0 despesas ainda pendentes após aplicação das regras de palavras-chave.
- Revisar divergências de caixa em dinheiro e cheque sem justificativa, cruzando VENDA_FORMA_PAGAMENTO com CAIXA.
- Validar movimentação bancária: transferências precisam de contra-partida entre filiais.

## 12. Levantamento do que JÁ ESTÁ PRONTO na Base de Dados
**Status:** DISPONÍVEL
| Indicador / Relatório | Fonte dos Dados | Cobertura de Período | Nível de Confiabilidade | Valor para a Diretoria |
|-----------------------|-----------------|----------------------|-------------------------|------------------------|
| Volume de combustível por produto e filial | /INTEGRACAO/ABASTECIMENTO (API WebPosto) | 2026-07-01 a 2026-07-24 | ALTA — dados reais da pista | 3.630,74 L / R$ 22.421,52 em 400 abastecimentos |
| Vendas de conveniência por filial | /INTEGRACAO/VENDA_ITEM + /INTEGRACAO/PRODUTO (API WebPosto) | 2026-07-17 a 2026-07-23 | ALTA — itens vendidos reais, todas as filiais | R$ 1.167,02; 106 itens; 1 filial ativa |
| Detalhamento de rombo de caixa por operador/turno | /INTEGRACAO/VENDA_FORMA_PAGAMENTO + /INTEGRACAO/CAIXA (API WebPosto) | 2026-07-17 a 2026-07-23 | ALTA — cruzamento de formas de pagamento com caixa | 3 operadores/turnos com divergência em dinheiro/cheque; total divergente R$ 11.792,47 |
| Despesas gerenciais por categoria e filial | finance_center.summary + expenses (snapshot) | 2026-07-01 a 2026-07-24 | ALTA — homologado, 526 registros | R$ 163.706,62 total; PESSOAL 51,99% (85.103,52) |
| Contas a pagar / receber | finance_center.summary (TITULO_PAGAR / TITULO_RECEBER) | 2026-07-01 a 2026-07-24 | ALTA — 354 pagáveis, 23 recebíveis | Pagar em aberto R$ 837.150,14; Receber pendente R$ 3.180,65 |
| Reconciliação de caixa por natureza de pagamento | cash_reconciliation.recon_summary (snapshot) | 2026-07-17 a 2026-07-23 | ALTA — 139 itens analisados, 109 auto-matched | Apurado R$ 724.369,54 vs Apresentado R$ 724.097,07; divergente R$ 11.792,47 |
| DRE departamental confirmada + auto-classificação | director_financial_reconciliation (snapshot) + regras de palavras-chave | 2026-07-01 a 2026-07-24 | MÉDIA — classificação automática aplicada, requer revisão manual | 130 despesas classificadas; 0 pendentes; top confirmados: POSTO VIP combustiveis R$ 52.836,97; POSTO DOZE FILIAL II nao_classificado R$ 8.250,00; POSTO DOZE FILIAL II combustiveis R$ 7.995,00 |
| CMV / custo de reposição por litro | COMPRAS + ESTOQUE + abastecimento | INDISPONÍVEL | NULA | INDISPONÍVEL NA BASE — impossibilita margem bruta/operacional e EBITDA por litro |
| Folha de pagamento / headcount por filial | PESSOAL (despesas classificadas) + /INTEGRACAO/FUNCIONARIO | PARCIAL | MÉDIA — despesas de pessoal consolidadas, mas sem headcount operacional | R$ 85.103,52 em despesas gerenciais de PESSOAL |
| Transferências entre filiais | MOVIMENTO_CONTA + TRANSFERENCIA_BANCARIA | PARCIAL | BAIXA — MOVIMENTO_CONTA indisponível no director reconciliation | R$ 5.808,66 em transferências bancárias não alocadas por filial |
| Eficiência operacional de caixa | finance_center.summary.caixa | 2026-07-01 a 2026-07-24 | ALTA — 96 turnos com dados de caixa | Despesa caixa R$ 40.816,50; vale funcionário R$ 81.237,49; empréstimos R$ 0,00 |
| Alertas e anomalias executivas | executive_scorecard + cash_reconciliation | 2026-07-01 a 2026-07-24 | ALTA — alertas gerados a partir de dados reais | 5 alertas recentes; divergências não justificadas R$ 11.792,47 |

---
*Relatório gerado automaticamente pelo LOGOS Executive Consolidated Report Service.*