---
# 🏗️ HOME INFORMATION ARCHITECTURE | LOGOS
# Type: ARCHITECTURE_SPEC
# Version: 1.0
# Sprint: UX-01 — Momento Zero & Executive Experience
# Status: OFFICIAL
---

# Home Information Architecture

> **"Arquitetura da informação não é sobre onde colocar elementos. É sobre criar um caminho mental óbvio."**

---

## 🎯 Objetivo

Definir a **estrutura lógica** da Home do LOGOS que permite compreensão imediata em 10 segundos.

---

## 📐 Hierarquia Visual

### Pirâmide de Prioridades

```
      [DECISÕES]           ← 60% atenção
      ──────────
         /    \
    [IMPACTO] [HEALTH]     ← 30% atenção
    ────────────────
         /        \
    [SAUDAÇÃO]  [META]     ← 10% atenção
```

**Lei de Fitts**: Elementos mais importantes ocupam mais espaço e estão mais próximos do centro de visão.

---

## 🎨 Layout Estrutural

### Grid System

```
Desktop (1920×1080):
┌─────────────────────────────────────────────────────────────┐
│  Container: 1200px                                          │
│  Padding: 40px                                              │
│  Gap: 32px                                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [SAUDAÇÃO] ← 100% width, height: auto                     │
│  padding-bottom: 32px                                       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [BUSINESS HEALTH] ← 100% width, height: 80px              │
│  padding-bottom: 32px                                       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [LOGOS IMPACT] ← 100% width, height: 120px                │
│  padding-bottom: 48px                                       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [DECISÃO #1] ← 100% width, height: 180px                  │
│  margin-bottom: 24px                                        │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [DECISÃO #2] ← 100% width, height: 180px                  │
│  margin-bottom: 24px                                        │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [DECISÃO #3] ← 100% width, height: 180px                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Total height: ~1040px (fits 100vh)
```

### Responsivo (Mobile <640px)

```
┌──────────────────────────┐
│  Padding: 24px           │
│  Gap: 24px               │
├──────────────────────────┤
│  [SAUDAÇÃO]              │
│  height: auto            │
├──────────────────────────┤
│  [HEALTH]                │
│  height: 60px            │
├──────────────────────────┤
│  [IMPACT]                │
│  height: 100px           │
├──────────────────────────┤
│  [DECISÃO #1]            │
│  height: 200px           │
├──────────────────────────┤
│  [DECISÃO #2]            │
│  height: 200px           │
├──────────────────────────┤
│  [DECISÃO #3]            │
│  height: 200px           │
└──────────────────────────┘

Total: ~900px
Scroll: Permitido (max 2× viewport)
```

---

## 🔍 F-Pattern Reading

### Mapa de Calor Esperado

```
Heatmap:
████████░░░░░░  ← Saudação (100% leitura)
████████████░░  ← Contagem decisões (95% leitura)
██████░░░░░░░░  ← Health (60% leitura)
████████░░░░░░  ← Impact Score (80% leitura)
████████████░░  ← Decisão #1 (90% leitura)
████████░░░░░░  ← Decisão #2 (70% leitura)
██████░░░░░░░░  ← Decisão #3 (50% leitura)
```

**Otimização**: Colocar informação mais importante no topo (decisões), não no rodapé.

---

## 📏 Proporções Ópticas

### Golden Ratio Application

```css
/* Proporção áurea: ~1.618 */
--ratio-large: 1.618;
--ratio-medium: 1.333;
--ratio-small: 1.125;

/* Espaços */
--space-xs: 8px;
--space-sm: calc(var(--space-xs) * var(--ratio-small));  /* 9px */
--space-md: calc(var(--space-sm) * var(--ratio-medium)); /* 12px */
--space-lg: calc(var(--space-md) * var(--ratio-large));  /* 19px ≈ 20px */
--space-xl: calc(var(--space-lg) * var(--ratio-large));  /* 32px */
```

### Font Size Harmony

```css
/* Scale modular (1.25 - Major Third) */
--font-xs: 12px;
--font-sm: 14px;    /* 12 × 1.167 */
--font-base: 16px;  /* 14 × 1.143 */
--font-lg: 18px;    /* 16 × 1.125 */
--font-xl: 24px;    /* 18 × 1.333 */
--font-2xl: 32px;   /* 24 × 1.333 */
```

---

## 🎯 Zonas de Atenção

### Modelo de 3 Zonas

```
┌─────────────────────────────────────────┐
│  ZONA PRIMÁRIA (0-400px do topo)        │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  • Saudação                             │
│  • Contagem de decisões                 │
│  • Business Health                      │
│                                         │
│  Leitura: 100% dos usuários             │
│  Tempo de atenção: 3-5 segundos         │
│                                         │
├─────────────────────────────────────────┤
│  ZONA SECUNDÁRIA (400-700px do topo)    │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  • LOGOS Impact                         │
│  • Decisão #1                           │
│                                         │
│  Leitura: 90% dos usuários              │
│  Tempo de atenção: 3-4 segundos         │
│                                         │
├─────────────────────────────────────────┤
│  ZONA TERCIÁRIA (700px+ do topo)        │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  • Decisão #2                           │
│  • Decisão #3                           │
│                                         │
│  Leitura: 60-70% dos usuários           │
│  Tempo de atenção: 2-3 segundos         │
│                                         │
└─────────────────────────────────────────┘
```

**Implicação**: Decisões #2 e #3 devem ser auto-explicativas (menos contexto necessário).

---

## 🧭 Fluxo de Navegação

### Entry Points

```
┌──────────────────────────────────────────┐
│  HOME (Momento Zero)                     │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                          │
│  [Saudação] → (Passivo, apenas leitura) │
│     ↓                                    │
│  [Health] → Clique → /health/details     │
│     ↓                                    │
│  [Impact] → Clique → /impact/history     │
│     ↓                                    │
│  [Decisão #1]                            │
│     ↓                                    │
│  [Executar] → Action Flow → Confirmação  │
│     ↓                                    │
│  [Decisão #2] ...                        │
│     ↓                                    │
│  [Decisão #3] ...                        │
│                                          │
└──────────────────────────────────────────┘
```

### Navigation Depth

```
Home (depth: 0)
│
├─→ Decisão Detail (depth: 1)
│   │
│   ├─→ Execution Flow (depth: 2)
│   │   │
│   │   └─→ Confirmation (depth: 3) → Back to Home
│   │
│   └─→ History (depth: 2)
│
├─→ Impact History (depth: 1)
│   │
│   └─→ Decision Detail (depth: 2)
│
└─→ Health Details (depth: 1)
```

**Regra**: Máximo 3 níveis de profundidade. Sempre com "Back to Home" visível.

---

## 📊 Information Density

### Densidade por Seção

| Seção | Densidade | Justificativa |
|-------|-----------|---------------|
| **Saudação** | Baixa (10%) | Respiração, contexto pessoal |
| **Health** | Média (30%) | Contexto geral, não protagonista |
| **Impact** | Média (40%) | Prova de valor, importante mas não urgente |
| **Decisões** | Alta (60%) | Core action, máxima densidade permitida |

### Cálculo de Densidade

```
Densidade = (Caracteres de texto + Elementos interativos) / Área em px²

Exemplo - Decisão Card:
- Texto: "Cobrar Cliente XPTO" (18 chars) + "R$ 8.500" (8 chars) + "5 minutos" (10 chars) = 36 chars
- Elementos: 1 botão, 1 ícone = 2
- Área: 1200px × 180px = 216.000px²

Densidade = (36 + 2) / 216.000 = 0.000176 (baixa densidade)

Target: 0.0001 - 0.0003 (confortável)
```

---

## 🎨 Visual Hierarchy Techniques

### 1. Tamanho

```
H1 (Saudação): 24px
H2 (Impacto): 32px  ← Maior = mais importante
H3 (Decisão): 18px
Body: 16px
Small: 14px
```

### 2. Peso

```
Bold (700): Valores financeiros, CTAs
Semibold (600): Títulos de decisões
Medium (500): Labels, subtítulos
Regular (400): Texto corrido
```

### 3. Cor

```
Primária (#111827): Ação imediata
Secundária (#374151): Contexto importante
Terciária (#6B7280): Informação de suporte
Quaternária (#9CA3AF): Meta-informação
```

### 4. Espaçamento

```
48px: Separação de contextos (Impact → Decisões)
32px: Separação de seções (Health → Impact)
24px: Separação de cards (Decisão #1 → #2)
16px: Elementos internos de card
```

### 5. Alinhamento

```
Centro: Saudação, Impact (cria foco)
Esquerda: Decisões, Health (facilita scan)
Direita: CTAs secundários (convenção)
```

---

## 🧩 Component Relationships

### Dependency Graph

```
Home
├── GlobalNav (persistent)
│   └── UserMenu
├── Greeting (context-aware)
│   └── DecisionCount
├── BusinessHealth (collapsible)
│   └── HealthBar
├── LogosImpact (expandable)
│   ├── TotalImpact
│   ├── Breakdown (hidden by default)
│   └── ROI
└── DecisionList
    ├── DecisionCard (priority: 1)
    │   ├── DecisionHeader
    │   ├── DecisionMeta
    │   └── DecisionAction → ExecutionFlow
    ├── DecisionCard (priority: 2)
    └── DecisionCard (priority: 3)
```

### State Management

```typescript
interface HomeState {
  user: User;
  greeting: string;
  decisionCount: number;
  businessHealth: {
    score: number;
    status: 'excellent' | 'good' | 'attention' | 'critical';
    riskCount: number;
  };
  logosImpact: {
    total: number;
    recovered: number;
    saved: number;
    prevented: number;
    additional: number;
    timeSaved: number;
    roi: number;
  };
  decisions: Decision[];
  loading: boolean;
  error: Error | null;
}
```

---

## ⚡ Performance Budget

### Load Priority

```
Priority 1 (0-500ms):
- Layout structure (skeleton)
- Greeting text
- Decision count

Priority 2 (500-1000ms):
- Business Health
- LOGOS Impact
- Decision #1

Priority 3 (1000-1500ms):
- Decision #2
- Decision #3

Priority 4 (1500ms+):
- Micro-animations
- Non-critical data
```

### Bundle Sizes

| Resource | Size | Budget |
|----------|------|--------|
| **HTML** | ~5KB | < 10KB |
| **CSS** | ~30KB | < 50KB |
| **JS (initial)** | ~80KB | < 150KB |
| **JS (total)** | ~200KB | < 300KB |
| **Images** | ~50KB | < 100KB |
| **Fonts** | ~80KB | < 150KB |
| **TOTAL** | ~445KB | < 700KB |

---

## 🎯 Accessibility Mapping

### ARIA Landmarks

```html
<main role="main" aria-label="Home">
  
  <section role="region" aria-label="Saudação">
    <!-- Greeting -->
  </section>
  
  <section role="region" aria-label="Saúde do negócio">
    <!-- Business Health -->
  </section>
  
  <section role="region" aria-label="Impacto do LOGOS">
    <!-- LOGOS Impact -->
  </section>
  
  <section 
    role="region" 
    aria-label="Decisões do dia"
    aria-describedby="decision-count"
  >
    <h2 id="decision-count">3 decisões importantes</h2>
    
    <article role="article" aria-label="Decisão 1: Cobrar cliente">
      <!-- Decision #1 -->
    </article>
    
    <article role="article" aria-label="Decisão 2: Negociar fornecedor">
      <!-- Decision #2 -->
    </article>
    
    <article role="article" aria-label="Decisão 3: Investigar vendas">
      <!-- Decision #3 -->
    </article>
  </section>
  
</main>
```

### Focus Order

```
Tab 1: Skip to main content (hidden)
Tab 2: Global nav / User menu
Tab 3: Health (expandable)
Tab 4: Impact (expandable)
Tab 5: Decisão #1 - Executar button
Tab 6: Decisão #2 - Executar button
Tab 7: Decisão #3 - Executar button
Tab 8: Footer navigation (if visible)
```

---

## 📱 Responsive Breakpoints

### Layouts por Dispositivo

#### Mobile (< 640px)

- Single column
- Stack vertical
- Font sizes: -10%
- Padding: 24px
- Gap: 24px
- Scroll: Permitido (max 2× viewport)

#### Tablet (640px - 1024px)

- Single column
- Container: 720px
- Font sizes: Normal
- Padding: 32px
- Gap: 32px
- Scroll: Mínimo (idealmente sem)

#### Desktop (1024px - 1440px)

- Single column
- Container: 1200px
- Font sizes: Normal
- Padding: 40px
- Gap: 32px
- Scroll: Proibido (100vh fit)

#### Large Desktop (> 1440px)

- Single column
- Container: 1200px (max)
- Font sizes: Normal
- Padding: 40px
- Gap: 32px
- Centered horizontally

---

## ✅ Validation Checklist

### Information Architecture

- [ ] Hierarquia clara (3 níveis máximo)
- [ ] F-pattern respeitado
- [ ] Golden ratio aplicado
- [ ] Proporções ópticas harmônicas

### Layout

- [ ] Grid system definido
- [ ] Responsividade para 4 breakpoints
- [ ] Fits 100vh (desktop)
- [ ] Performance budget respeitado

### Navigation

- [ ] Entry points claros
- [ ] Depth máximo: 3 níveis
- [ ] Back to Home sempre visível
- [ ] Breadcrumbs (se necessário)

### Accessibility

- [ ] ARIA landmarks corretos
- [ ] Focus order lógico
- [ ] Skip links implementados
- [ ] Screen reader friendly

### Performance

- [ ] Critical CSS inline
- [ ] Code splitting
- [ ] Lazy loading
- [ ] Skeleton states

---

## 📚 Referências

- [MOMENTO_ZERO_UX.md](../business/MOMENTO_ZERO_UX.md) — UX spec
- [DESIGN_SYSTEM_V4.md](DESIGN_SYSTEM_V4.md) — Design tokens
- **Information Architecture** (Louis Rosenfeld) — IA principles
- **Don't Make Me Think** (Steve Krug) — Usability
- **The Elements of User Experience** (Jesse James Garrett) — UX layers

---

**[HOME INFORMATION ARCHITECTURE — SPRINT UX-01]**

*Status: OFFICIAL | Type: ARCHITECTURE | Version: 1.0 | Focus: Mental Model*
