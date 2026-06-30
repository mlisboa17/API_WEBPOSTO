---
# ⏱️ TEN SECOND RULE | LOGOS
# Type: QUALITY_PROTOCOL
# Version: 1.0
# Sprint: UX-01 — Momento Zero & Executive Experience
# Status: OFFICIAL
---

# Ten Second Rule — Protocolo de 10 Segundos

> **"Se um proprietário não entende a tela em 10 segundos, a tela falhou."**

---

## 🎯 Objetivo

Criar um protocolo oficial de teste de usabilidade focado em **clareza imediata**.

###Regra de Ouro

> Qualquer pessoa, sem treinamento prévio, deve entender:
> 1. **O que fazer** — Qual ação tomar
> 2. **Por que fazer** — Qual o benefício
> 3. **Quanto envolve** — Qual o valor financeiro

Tudo isso em **menos de 10 segundos**.

---

## 📋 Protocolo Oficial

### Etapa 1: Recrutamento

#### Perfil do Teste

| Critério | Requisito |
|----------|-----------|
| **Função** | Proprietário de posto ou gestor |
| **Idade** | 30-60 anos |
| **Experiência** | 2+ anos no ramo |
| **Tech literacy** | Básico (usa WhatsApp, email) |
| **LOGOS** | Nunca usou (critical) |

#### Quantidade

- **Mínimo**: 5 pessoas
- **Ideal**: 10 pessoas
- **Perfil diverso**: Pequeno, médio, grande porte

### Etapa 2: Preparação

#### Ambiente

```
┌──────────────────────────────────────────────────────┐
│  AMBIENTE CONTROLADO                                 │
├──────────────────────────────────────────────────────┤
│  • Sala silenciosa                                   │
│  • Iluminação neutra                                 │
│  • Tela calibrada (100% brilho)                      │
│  • Resolução: 1920x1080 (desktop) ou device nativo  │
│  • Distância: 50-70cm da tela                        │
│  • Sem distrações (celular desligado)               │
└──────────────────────────────────────────────────────┘
```

#### Equipamento

- [ ] Cronômetro (precisão: 0.1s)
- [ ] Câmera para gravar (eye tracking opcional)
- [ ] Formulário de perguntas impresso
- [ ] Termo de consentimento

#### Protocolo de Teste

```
1. Briefing (2 min)
   "Você verá uma tela por 10 segundos.
    Após isso, farei 3 perguntas.
    Não há resposta certa ou errada.
    Estamos testando o sistema, não você."

2. Apresentação (10s exatos)
   → Mostrar Home do LOGOS
   → Cronômetro visível para testador (não para participante)
   → Sem interação (apenas visualizar)

3. Ocultação (imediata)
   → Tela fica preta
   → Participante não pode mais ver

4. Perguntas (30s máximo por pergunta)
   → Q1, Q2, Q3 (ver abaixo)

5. Debriefing (5 min)
   → Feedback qualitativo
```

### Etapa 3: Execução

#### Perguntas Obrigatórias

**Q1: O que você deve fazer hoje?**
- **Resposta esperada**: "Cobrar cliente / negociar fornecedor / investigar queda"
- **Pontos**: 0 (nenhuma ideia), 1 (vago), 2 (específico)

**Q2: Quanto dinheiro está envolvido?**
- **Resposta esperada**: Valor específico (R$ 8.500, R$ 26.000 total, etc.)
- **Pontos**: 0 (não sabe), 1 (aproximado), 2 (exato ou muito próximo)

**Q3: Qual é a decisão mais importante?**
- **Resposta esperada**: Decisão #1 (cobrar cliente, por exemplo)
- **Pontos**: 0 (não sabe), 1 (uma das 3), 2 (a correta)

#### Critérios de Hesitação

**Registro de tempo de resposta:**

| Tempo | Avaliação |
|-------|-----------|
| < 3s | Excelente — Clareza imediata |
| 3-5s | Bom — Precisou pensar um pouco |
| 5-8s | Aceitável — Precisou resgatar memória |
| > 8s | Falha — Não ficou claro |

**Red Flags:**

- "Hmmm... deixa eu pensar..."
- "Acho que era algo sobre..."
- "Tinha um número, mas..."
- "Não tenho certeza..."

### Etapa 4: Pontuação

#### Scoring System

```
PONTUAÇÃO MÁXIMA: 6 pontos

Q1 (O que fazer): 0-2 pontos
Q2 (Quanto envolve): 0-2 pontos
Q3 (Qual prioridade): 0-2 pontos

Tempo médio de resposta: Multiplicador
  < 3s: 1.2x
  3-5s: 1.0x
  5-8s: 0.8x
  > 8s: 0.5x

SCORE FINAL = (Pontos × Multiplicador) / 6 × 100
```

#### Classificação

| Score | Classificação | Ação |
|-------|---------------|------|
| **90-100%** | Excelente | Aprovar |
| **70-89%** | Bom | Revisar pequenos detalhes |
| **50-69%** | Regular | Redesign parcial necessário |
| **< 50%** | Falha | Redesign completo |

#### Exemplo

```
Participante #1:
- Q1: "Cobrar um cliente" (2 pontos, 2s)
- Q2: "Acho que era uns R$ 8 mil" (1 ponto, 4s)
- Q3: "A primeira, de cobrar" (2 pontos, 3s)

Total: 5 pontos
Tempo médio: 3s → Multiplicador 1.0x
Score: (5 × 1.0) / 6 × 100 = 83%

Classificação: BOM
```

---

## 📊 Métricas de Sucesso

### Por Pergunta

| Pergunta | Target | Como Medir |
|----------|--------|------------|
| **Q1 accuracy** | ≥ 80% (pontos 2/2) | Respostas específicas |
| **Q2 accuracy** | ≥ 70% (pontos ≥1/2) | Valor aproximado correto |
| **Q3 accuracy** | ≥ 80% (pontos 2/2) | Prioridade correta |

### Globais

| Métrica | Target | Como Medir |
|---------|--------|------------|
| **Overall Score** | ≥ 80% | Média de todos participantes |
| **Pass Rate** | ≥ 80% | % de participantes com score ≥70% |
| **Time to Answer** | < 5s | Média de tempo de resposta |
| **Confidence** | ≥ 4/5 | Auto-avaliação do participante |

---

## 🎬 Variações do Teste

### V1: Teste Básico (Home)

**O que testar**: Nova Home do LOGOS

**Duração**: 10 segundos

**Perguntas**: Q1, Q2, Q3 padrão

### V2: Teste de Comparação

**O que testar**: Home antiga vs Home nova

**Duração**: 10s cada (ordem aleatória)

**Perguntas**: Q1, Q2, Q3 + preferência

```
Q4: Qual tela você prefere?
Q5: Por quê?
```

### V3: Teste de Descoberta

**O que testar**: Navegação após 10s

**Duração**: 10s visualização + 60s interação livre

**Objetivo**: Ver se consegue executar decisão #1

### V4: Teste de Contextos

**O que testar**: Home em diferentes cenários

**Cenários**:
- 1 decisão apenas
- 3 decisões (padrão)
- 5 decisões (stress test)
- 0 decisões (empty state)

---

## 🧪 Casos de Teste Específicos

### Caso 1: Proprietário Experiente

**Perfil**: 15+ anos no ramo, múltiplos postos

**Expectativa**: Score ≥ 90% (entende negócio rapidamente)

### Caso 2: Proprietário Novo

**Perfil**: < 2 anos no ramo, primeiro posto

**Expectativa**: Score ≥ 75% (precisa mais contexto)

### Caso 3: Gerente Operacional

**Perfil**: Não é dono, gerencia para terceiro

**Expectativa**: Score ≥ 80% (focado em operação)

### Caso 4: Tech-Savvy

**Perfil**: Usa múltiplos apps, confortável com SaaS

**Expectativa**: Score ≥ 85% (familiarizado com padrões)

### Caso 5: Tech-Averse

**Perfil**: Usa apenas WhatsApp/email

**Expectativa**: Score ≥ 70% (interface deve ser muito clara)

---

## 📝 Formulário de Teste

### Dados do Participante

```
Nome: _______________________________
Idade: ____
Função: ○ Proprietário  ○ Gerente  ○ Outro: _______
Anos de experiência: ____
Número de postos: ____
Usa sistemas financeiros: ○ Sim  ○ Não
Quais: _______________________________
```

### Teste de 10 Segundos

```
Início: __:__:__
Fim: __:__:__
Duração: _____ segundos

Q1: O que você deve fazer hoje?
Resposta: _______________________________________
Tempo: _____ segundos
Pontos: ○ 0  ○ 1  ○ 2

Q2: Quanto dinheiro está envolvido?
Resposta: _______________________________________
Tempo: _____ segundos
Pontos: ○ 0  ○ 1  ○ 2

Q3: Qual é a decisão mais importante?
Resposta: _______________________________________
Tempo: _____ segundos
Pontos: ○ 0  ○ 1  ○ 2

Score Total: _____%
Classificação: ___________
```

### Perguntas Qualitativas

```
1. O que mais chamou sua atenção na tela?
   _________________________________________________

2. O que você mudaria?
   _________________________________________________

3. Você se sentiria confiante para usar isso?
   ○ Sim  ○ Não  ○ Talvez
   Por quê? _________________________________________

4. Quanto você pagaria por esse sistema? (mensal)
   ○ Até R$ 500
   ○ R$ 500-1.000
   ○ R$ 1.000-2.000
   ○ R$ 2.000-5.000
   ○ > R$ 5.000

5. Confiança na resposta (1-5):
   Pergunta 1: ○ 1  ○ 2  ○ 3  ○ 4  ○ 5
   Pergunta 2: ○ 1  ○ 2  ○ 3  ○ 4  ○ 5
   Pergunta 3: ○ 1  ○ 2  ○ 3  ○ 4  ○ 5
```

---

## 🎯 Critérios de Aprovação

### Para Aprovar uma Tela

| Critério | Target | Status |
|----------|--------|--------|
| **Overall Score** | ≥ 80% | ○ Pass  ○ Fail |
| **Pass Rate** | ≥ 80% dos participantes | ○ Pass  ○ Fail |
| **Q1 Accuracy** | ≥ 80% | ○ Pass  ○ Fail |
| **Q2 Accuracy** | ≥ 70% | ○ Pass  ○ Fail |
| **Q3 Accuracy** | ≥ 80% | ○ Pass  ○ Fail |
| **Avg Response Time** | < 5s | ○ Pass  ○ Fail |
| **Confidence** | ≥ 4/5 | ○ Pass  ○ Fail |

**Todos os critérios devem ser PASS.**

Se qualquer um for FAIL → Redesign necessário.

---

## 🔄 Processo de Iteração

### Loop de Melhoria

```
┌──────────────────────────────────────────┐
│  1. Criar Design                         │
│     → Protótipo high-fidelity            │
│                                          │
│  ↓                                       │
│                                          │
│  2. Executar Teste de 10 Segundos       │
│     → 10 participantes                   │
│     → Formulário completo                │
│                                          │
│  ↓                                       │
│                                          │
│  3. Analisar Resultados                  │
│     → Score < 80%? → Redesign            │
│     → Score ≥ 80%? → Aprovar             │
│                                          │
│  ↓                                       │
│                                          │
│  4. Implementar                          │
│     → Código production                  │
│     → Re-testar com 5 novos users        │
│                                          │
│  ↓                                       │
│                                          │
│  5. Monitorar em Produção                │
│     → Time to First Action               │
│     → Execution Rate                     │
│     → User Satisfaction                  │
│                                          │
└──────────────────────────────────────────┘
```

---

## 📊 Relatório de Teste

### Template

```markdown
# TEN SECOND RULE TEST REPORT

**Data**: 2026-XX-XX
**Tela**: Home — Momento Zero v1.0
**Testador**: [Nome]
**Participantes**: 10

---

## RESULTADOS GERAIS

| Métrica | Target | Resultado | Status |
|---------|--------|-----------|--------|
| Overall Score | ≥80% | 87% | ✅ PASS |
| Pass Rate | ≥80% | 90% | ✅ PASS |
| Q1 Accuracy | ≥80% | 85% | ✅ PASS |
| Q2 Accuracy | ≥70% | 78% | ✅ PASS |
| Q3 Accuracy | ≥80% | 82% | ✅ PASS |
| Avg Response Time | <5s | 4.2s | ✅ PASS |
| Confidence | ≥4/5 | 4.3/5 | ✅ PASS |

---

## BREAKDOWN POR PARTICIPANTE

| ID | Perfil | Q1 | Q2 | Q3 | Tempo | Score | Pass |
|----|--------|----|----|----|----|-------|------|
| 1 | Prop. 45a | 2 | 2 | 2 | 3.5s | 100% | ✅ |
| 2 | Prop. 38a | 2 | 1 | 2 | 4.2s | 83% | ✅ |
| 3 | Ger. 52a | 1 | 1 | 2 | 5.1s | 64% | ❌ |
| ... |

---

## INSIGHTS QUALITATIVOS

**Pontos Fortes**:
- "Muito claro, dá pra ver logo o que fazer"
- "Gostei que mostra o valor do dinheiro grande"
- "Achei fácil de entender"

**Pontos de Melhoria**:
- "Business Health não entendi muito bem"
- "Poderia ter uma explicação do que é Confidence"

---

## RECOMENDAÇÃO

○ APROVAR — Score ≥ 80%, todos critérios PASS
○ REVISAR — Score 70-79%, alguns critérios PASS
○ REDESIGN — Score < 70%, múltiplos critérios FAIL

**Ação**: APROVAR com revisão do Business Health label
```

---

## ✅ Checklist de Execução

### Antes do Teste

- [ ] Participantes recrutados (min. 5)
- [ ] Ambiente preparado
- [ ] Equipamento funcionando
- [ ] Formulários impressos
- [ ] Termo de consentimento assinado
- [ ] Cronômetro calibrado

### Durante o Teste

- [ ] Briefing completo (2 min)
- [ ] Apresentação exata 10s
- [ ] Perguntas em ordem
- [ ] Tempo de resposta registrado
- [ ] Observações anotadas
- [ ] Debriefing qualitativo

### Após o Teste

- [ ] Pontuação calculada
- [ ] Relatório gerado
- [ ] Insights documentados
- [ ] Decisão tomada (aprovar/revisar/redesign)
- [ ] Próximos passos definidos

---

## 🎯 Pergunta Final do Protocolo

> **"Se aplicássemos este teste hoje na Home atual, passaríamos?"**

**Resposta esperada**: **SIM** (score ≥ 80%)

**Se NÃO**: Redesign obrigatório antes de lançar.

---

## 📚 Referências

- [MOMENTO_ZERO_UX.md](MOMENTO_ZERO_UX.md) — Especificação UX
- [EXECUTIVE_EXPERIENCE.md](EXECUTIVE_EXPERIENCE.md) — Experiência premium
- **Don't Make Me Think** (Steve Krug) — Usability testing
- **Rocket Surgery Made Easy** (Steve Krug) — DIY usability testing
- **Nielsen Norman Group** — Usability heuristics

---

**[TEN SECOND RULE — SPRINT UX-01]**

*Status: OFFICIAL | Type: QUALITY_PROTOCOL | Version: 1.0 | Threshold: 80%*
