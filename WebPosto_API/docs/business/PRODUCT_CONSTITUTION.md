---
# 📜 PRODUCT_CONSTITUTION.md | LOGOS
# Type: PRODUCT_PRINCIPLES
# Version: 2.0
# Updated: 2026-06-29
# Status: OFFICIAL
---

# Constituição do Produto LOGOS

> **Documento Oficial de Princípios do Produto**
>
> *Atualizado para Owner Operating System (PRODUCT-04)*

Esta constituição estabelece os princípios fundamentais que orientam todas as decisões de arquitetura, produto, UX e desenvolvimento do LOGOS.

**Prioridade:** Estes princípios têm precedência sobre novas funcionalidades.

---

## 📋 Índice dos Princípios

1. [O Dono do Posto é o Centro](#princípio-1--o-dono-do-posto-é-o-centro)
2. [O LOGOS Encontra os Problemas](#princípio-2--o-logos-encontra-os-problemas)
3. [Menos é Mais](#princípio-3--menos-é-mais)
4. [Dados Reais Sempre](#princípio-4--dados-reais-sempre)
5. [Honestidade Técnica Absoluta](#princípio-5--honestidade-técnica-absoluta)
6. [Qualidade Acima de Quantidade](#princípio-6--qualidade-acima-de-quantidade)
7. [Experiência Premium](#princípio-7--experiência-premium)
8. [Evolução Gradual](#princípio-8--evolução-gradual)
9. [Documentação Obrigatória](#princípio-9--documentação-obrigatória)
10. [GitHub como Fonte Oficial](#princípio-10--github-como-fonte-oficial)
11. [Filtro de Valor](#princípio-11--filtro-de-valor)
12. [Visão de Longo Prazo](#princípio-12--visão-de-longo-prazo)
13. [LOGOS Entrega Decisões, Não Dados](#princípio-13--logos-entrega-decisões-não-dados) *(PRODUCT-03)*
14. [Toda Tela Termina em uma Decisão](#princípio-14--toda-tela-termina-em-uma-decisão) *(PRODUCT-04)*
15. [LOGOS Investiga Automaticamente](#princípio-15--logos-investiga-automaticamente) *(PRODUCT-04)*

---

## PRINCÍPIO 1 — O DONO DO POSTO É O CENTRO

### Declaração
Toda funcionalidade deve responder claramente a uma destas perguntas:

> **Como isso ajuda o proprietário a ganhar mais dinheiro?**

> **Como isso evita que ele perca dinheiro?**

> **Como isso economiza tempo?**

### Aplicação
Se uma funcionalidade não responder nenhuma dessas perguntas, ela deve ser **adiada**.

### Checklist de Validação
- [ ] Esta feature aumenta receita?
- [ ] Esta feature reduz custos?
- [ ] Esta feature previne perdas?
- [ ] Esta feature economiza tempo do gestor?

---

## PRINCÍPIO 2 — O LOGOS ENCONTRA OS PROBLEMAS

### Declaração
O proprietário não deve procurar informações. O LOGOS deve identificar automaticamente:

- **Riscos** — ameaças à operação
- **Oportunidades** — chances de melhoria
- **Anomalias** — comportamentos fora do padrão
- **Perdas** — vazamentos de dinheiro
- **Prioridades** — o que exige atenção imediata

### Aplicação
O objetivo do produto **não é mostrar dados**.

O objetivo é **destacar aquilo que exige decisão**.

### Exemplos Válidos
- ✅ "Despesas de caixa 40% acima da média — verificar vales"
- ✅ "Queda de 25% nas vendas de combustível — verificar estoque"
- ✅ "3 contas vencidas ontem — total R$ 12.450,00"

### Exemplos Inválidos
- ❌ "Dashboard financeiro disponível"
- ❌ "Gráfico de vendas carregado"
- ❌ "Tabela de transações exibida"

---

## PRINCÍPIO 3 — MENOS É MAIS

### Declaração
Cada componente exibido deve justificar sua existência.

Se um card não gera uma **decisão prática**, ele deve ser **removido**.

### Regra dos 10 Segundos
A Home deve responder em menos de 10 segundos:

1. **Como foi ontem?**
2. **Onde estou perdendo dinheiro?**
3. **O que preciso fazer hoje?**

### Aplicação
Se uma informação não leva a uma ação, ela é **desnecessária**.

---

## PRINCÍPIO 4 — DADOS REAIS SEMPRE

### Declaração
**É proibido usar dados mockados, simulados ou inventados.**

### Regras
- ✅ Apenas dados do WebPosto
- ✅ Apenas dados de APIs certificadas
- ✅ Cache apenas para performance, nunca para mascarar indisponibilidade
- ✅ Se dados não existem, mostrar "Dados indisponíveis"

### Exemplos Válidos
- ✅ Dados do WebPosto API
- ✅ Dados de serviços certificados
- ✅ Cache TTL < 5 minutos

### Exemplos Proibidos
- ❌ JSON fixo no código
- ❌ Valores hardcoded
- ❌ Dados "placeholder"
- ❌ "Simulações" apresentadas como reais

---

## PRINCÍPIO 5 — HONESTIDADE TÉCNICA ABSOLUTA

### Declaração
**É proibido declarar qualidade sem evidência.**

### Regras
- ✅ Toda declaração de qualidade deve ter evidência objetiva
- ✅ Toda limitação deve ser documentada
- ✅ Toda incerteza deve ser quantificada (Confidence Score)
- ✅ Bugs conhecidos devem ser listados

### Exemplos Válidos
- ✅ "Testado em 3 tenants reais: VIP (11495), Casa Caiada (5555), Doze (74014)"
- ✅ "Confidence Score: 85% (High)"
- ⚠️ "Funcionalidade experimental — Confidence Score < 60%"

### Exemplos Proibidos
- ❌ "Funciona perfeitamente" (sem testes)
- ❌ "100% testado" (sem evidência)
- ❌ "Sem bugs" (impossível)
- ❌ "Excelente performance" (sem métricas)

---

## PRINCÍPIO 6 — QUALIDADE ACIMA DE QUANTIDADE

### Declaração
Uma feature que economize R$ 10.000 vale mais que 20 dashboards.

### Aplicação
Valor real > Quantidade de features.

### Checklist
- [ ] Qual o valor financeiro desta feature?
- [ ] Qual o ROI estimado?
- [ ] Vale mais que alternativas?

---

## PRINCÍPIO 7 — EXPERIÊNCIA PREMIUM

### Referências
- Apple (simplicidade)
- Stripe (confiança)
- Linear (performance)
- Raycast (foco)
- Arc Browser (organização)
- Vercel (design)

### Regras
- Muito espaço em branco
- Tipografia forte
- Poucos elementos
- Poucas cores
- Poucos gráficos
- Poucos cards
- Mostrar apenas aquilo que gera decisão

---

## PRINCÍPIO 8 — EVOLUÇÃO GRADUAL

### Fases (atualizadas PRODUCT-04)

| Fase | Nome | Descrição | Status |
|------|------|-----------|--------|
| 1 | **VER** | O LOGOS enxerga | ✅ COMPLETE |
| 2 | **ENTENDER** | O LOGOS explica | ✅ COMPLETE |
| 3 | **DECIDIR** | O LOGOS prioriza | 🔄 CURRENT |
| 4 | **EXECUTAR** | Proprietário confirma execução | ⏳ NEXT |
| 5 | **APRENDER** | O LOGOS aprende comportamento | 🔮 FUTURE |
| 6 | **ANTECIPAR** | O LOGOS prevê problemas | 🔮 FUTURE |
| 7 | **AUTONOMOUS EXECUTIVE** | LOGOS prepara trabalho antes de abrir | 🔮 VISION |

### Regra
Nunca pular etapas. Cada fase deve estar sólida antes de avançar.

---

## PRINCÍPIO 9 — DOCUMENTAÇÃO OBRIGATÓRIA

### Declaração
Toda sprint deve atualizar a documentação.

### Documentos Obrigatórios
- [ ] `CURRENT_STATE.md`
- [ ] `ROADMAP.md`
- [ ] `SPRINT_HISTORY.md`
- [ ] `DECISION_LOG.md`
- [ ] `RELEASE_NOTES.md`

### Regra
Sprint sem documentação atualizada = Sprint incompleta.

---

## PRINCÍPIO 10 — GITHUB COMO FONTE OFICIAL

### Declaração
O código no GitHub é a única fonte da verdade.

### Regras
- ✅ Todo código versionado no GitHub
- ✅ Commits descritivos e incrementais
- ✅ Nada de "só local"
- ✅ Branch por sprint
- ✅ PRs revisados

### Repositório Oficial
https://github.com/mlisboa17/NewWebLogos

---

## PRINCÍPIO 11 — FILTRO DE VALOR

### As 5 Perguntas

Antes de qualquer sprint, responder:

1. **Faz o cliente ganhar dinheiro?**
2. **Evita perdas?**
3. **Economiza tempo?**
4. **Valor percebido imediatamente?**
5. **Pagaria mensalmente por isso?**

### Regra
Se 3 respostas forem "não", reavaliar antes de desenvolver.

---

## PRINCÍPIO 12 — VISÃO DE LONGO PRAZO

### Declaração
Ser o melhor **Gerente Digital** para postos de combustível.

### Visão 2027
LOGOS como verdadeiro **Assistente Executivo Autônomo** para proprietários de postos.

### Estratégia
- Foco absoluto em valor para o proprietário
- Qualidade sobre quantidade
- Evolução gradual (Fases 1-7)
- Tecnologia a serviço do negócio

---

## PRINCÍPIO 13 — LOGOS ENTREGA DECISÕES, NÃO DADOS *(PRODUCT-03)*

### Declaração
O LOGOS deixa de responder "Quanto vendi?" e passa a responder "O que devo fazer agora?"

### Aplicação
- ❌ Não mostrar dashboards de KPIs
- ✅ Mostrar decisões priorizadas
- ❌ Não exibir tabelas de dados
- ✅ Exibir ações acionáveis
- ❌ Não gerar gráficos estéticos
- ✅ Gerar recomendações com impacto financeiro

### Checklist
- [ ] Cada tela leva a uma decisão?
- [ ] Cada informação tem uma ação associada?
- [ ] O proprietário sabe o que fazer após ver a tela?

---

## PRINCÍPIO 14 — TODA TELA TERMINA EM UMA DECISÃO *(PRODUCT-04)*

### Declaração
**Toda informação apresentada ao proprietário deve terminar em uma decisão.**

Se uma tela termina apenas mostrando números, ela está **incompleta**.

### Regra de Ouro
> **Toda tela → Uma decisão**

### Aplicação

```
❌ INCOMPLETO:
   "Vendas caíram 11,8%"
   [Gráfico de vendas]
   
   Proprietário pensa: "E agora?"

✅ COMPLETO:
   "Vendas caíram 11,8%
   87% no Diesel S10, 18h-22h
   R$ 14.280 em risco
   
   [Ver análise completa →]
   [Executar ação recomendada →]"
   
   Proprietário sabe: O que aconteceu, onde, quanto,
   e qual ação tomar.
```

### Checklist por Tela
- [ ] Qual decisão esta tela apresenta?
- [ ] Qual ação o proprietário deve tomar?
- [ ] Qual o impacto financeiro?
- [ ] Como executar a ação?
- [ ] Se não houver ação, a tela é necessária?

---

## PRINCÍPIO 15 — LOGOS INVESTIGA AUTOMATICAMENTE *(PRODUCT-04)*

### Declaração
**O LOGOS nunca informa apenas o problema. Ele investiga automaticamente a causa provável utilizando dados reais e apresenta uma recomendação acionável.**

### Proibido

```
❌ "As vendas caíram 11,8%."
```

### Obrigatório

```
✅ "As vendas caíram 11,8%.

87% da perda ocorreu no Diesel S10 
entre 18h e 22h no POSTO VIP.

Causa provável:
• Preço 3% acima da concorrência
• Estoque em nível crítico (12% abaixo)
• 2 funcionários a menos no turno da noite

Impacto estimado: R$ 14.280.

Recomendação:
1. Verificar preço vs concorrência
2. Repor estoque imediatamente
3. Revisar escala do turno da noite

[Executar ações →]"
```

### Dimensoes de Investigação

O Sales Investigation Engine deve investigar automaticamente:

| Dimensão | O que investigar |
|----------|----------------|
| **PRODUTO** | Qual combustível caiu (Gasolina, Etanol, Diesel, GNV, etc) |
| **LOCAL** | Em qual posto/filial |
| **TEMPO** | Em qual turno, dia, horário |
| **METRICA** | Litros, margem, ticket, clientes |
| **CAUSAS** | Preço, estoque, funcionários, mix, despesas, cartões, PIX |
| **IMPACTO** | Receita perdida, lucro perdido, potencial de recuperação |

### Regra
**Jamais informar apenas o problema. Sempre investigar e recomendar.**

### Checklist
- [ ] O problema foi identificado?
- [ ] A causa raiz foi investigada?
- [ ] O impacto financeiro foi calculado?
- [ ] Uma recomendação acionável foi gerada?
- [ ] O Confidence Score foi calculado?

---

## 🏛️ Product Constitution Gate

### Aplicação
Toda sprint deve passar pelo Product Constitution Gate.

### Score Mínimo
- **Padrão:** 70/100
- **Sprint de definição (PRODUCT-04):** 95/100

### Documento
Ver `PRODUCT_CONSTITUTION_GATE_[SPRINT].md` em cada sprint.

---

## 📜 Histórico de Revisões

| Versão | Data | Sprint | Mudanças |
|--------|------|--------|----------|
| 1.0 | 2026-06-28 | GOVERNANCE-01 | 12 princípios originais |
| 2.0 | 2026-06-29 | PRODUCT-04 | + Princípios 14 e 15 (Owner Operating System) |

---

## ✅ Validação

Para adicionar um novo princípio:

1. Criar proposta com justificativa
2. Demonstrar alinhamento com visão de longo prazo
3. Passar por review
4. Atualizar este documento
5. Versionar (incrementar versão)
6. Atualizar índice

---

**[PRODUCT CONSTITUTION — LOGOS Owner Operating System]**

*Version: 2.0 | Principles: 15 | Status: OFFICIAL*
