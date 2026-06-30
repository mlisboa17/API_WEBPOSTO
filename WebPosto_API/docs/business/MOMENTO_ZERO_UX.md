---
# ⏱️ MOMENTO ZERO UX | LOGOS
# Type: UX_SPECIFICATION
# Version: 1.0
# Sprint: UX-01 — Momento Zero & Executive Experience
# Status: OFFICIAL
---

# Momento Zero — UX Specification

> **"Clareza em 10 segundos. Ação em 30 segundos."**

---

## 🎯 Objetivo

Transformar o LOGOS de um sistema que **mostra dados** em um sistema que **provoca decisões imediatas**.

### Regra de Ouro

> Em 10 segundos, o proprietário deve saber:
> 1. O que precisa fazer hoje
> 2. Quanto dinheiro está envolvido  
> 3. Qual decisão executar primeiro

---

## 📐 Estrutura da Nova Home

### Layout Geral

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  [SAUDAÇÃO]                                                 │
│  Bom dia, João.                                             │
│  Hoje existem apenas 3 decisões importantes.                │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [BUSINESS HEALTH]                                          │
│  ████████░░ 78/100 — Atenção                               │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [LOGOS IMPACT]                                             │
│  Desde que você começou a usar o LOGOS                     │
│  R$ 170.700 gerados | ROI: 14.8x                          │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [TOP 3 DECISÕES]                                           │
│                                                             │
│  🔴 Cobrar Cliente XPTO                                    │
│     Recuperação estimada: R$ 8.500                         │
│     Tempo: 5 minutos | Confidence: 92%                     │
│     [Executar Agora →]                                      │
│                                                             │
│  🟡 Queda no Diesel                                        │
│     Impacto: R$ 14.200                                     │
│     Tempo: 8 minutos | Confidence: 88%                     │
│     [Investigar →]                                          │
│                                                             │
│  🟢 Negociar Fornecedor                                     │
│     Economia: R$ 2.900                                     │
│     Tempo: 3 minutos | Confidence: 96%                     │
│     [Negociar →]                                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Total viewport: 100vh (sem scroll)
```

---

## 🎨 Design System V4

### Tipografia

#### Família
- **Primary**: Inter (system fallback: -apple-system, BlinkMacSystemFont, "Segoe UI")
- **Monospace**: JetBrains Mono (números financeiros)

#### Escala

| Elemento | Size | Weight | Line Height |
|----------|------|--------|-------------|
| Saudação | 18px | 400 | 1.5 |
| Contagem decisões | 24px | 700 | 1.2 |
| Business Health | 16px | 500 | 1.4 |
| Impact Score | 32px | 700 | 1.2 |
| Decisão Título | 18px | 600 | 1.3 |
| Valor Financeiro | 24px | 700 | 1.2 |
| Botão | 14px | 600 | 1 |

### Cores

#### Paleta Principal

```css
/* Neutros */
--bg-primary: #FFFFFF;
--bg-secondary: #F9FAFB;
--text-primary: #111827;
--text-secondary: #6B7280;
--text-tertiary: #9CA3AF;

/* Ações */
--action-primary: #2563EB;
--action-hover: #1D4ED8;
--action-active: #1E40AF;

/* Sinais */
--signal-success: #10B981;
--signal-warning: #F59E0B;
--signal-danger: #EF4444;

/* Bordas */
--border-light: #E5E7EB;
--border-medium: #D1D5DB;
```

### Espaçamento

#### Sistema 8px Base

```css
--space-1: 8px;   /* Micro */
--space-2: 16px;  /* Small */
--space-3: 24px;  /* Medium */
--space-4: 32px;  /* Large */
--space-5: 48px;  /* XL */
--space-6: 64px;  /* 2XL */
```

#### Aplicação

- **Container padding**: 40px (space-5)
- **Seções verticais**: 32px (space-4)
- **Cards gap**: 24px (space-3)
- **Inline elements**: 16px (space-2)
- **Buttons padding**: 12px 24px

### Elevação (Shadows)

```css
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
--shadow-md: 0 4px 6px rgba(0, 0, 0, 0.07);
--shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.10);
```

### Bordas

```css
--radius-sm: 6px;   /* Inputs, small cards */
--radius-md: 8px;   /* Cards, buttons */
--radius-lg: 12px;  /* Major sections */
--radius-xl: 16px;  /* Hero elements */
```

---

## 🧩 Componentes

### 1. Saudação (Greeting)

**Objetivo**: Criar conexão pessoal imediata.

```tsx
interface GreetingProps {
  ownerName: string;
  decisionCount: number;
}

// Visual
<div className="greeting">
  <p>Bom dia, {ownerName}.</p>
  <h2>Hoje existem apenas {decisionCount} decisões importantes.</h2>
</div>

// Estilo
.greeting {
  padding: var(--space-5) 0;
  border-bottom: 1px solid var(--border-light);
}

.greeting p {
  font-size: 18px;
  color: var(--text-secondary);
  margin-bottom: var(--space-1);
}

.greeting h2 {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
}
```

### 2. Business Health (Discreto)

**Objetivo**: Contexto geral sem protagonismo.

```tsx
interface BusinessHealthProps {
  score: number;  // 0-100
  status: 'excellent' | 'good' | 'attention' | 'critical';
  riskCount: number;
}

// Visual
<div className="business-health">
  <div className="health-bar">
    <div className="health-fill" style={{width: `${score}%`}} />
  </div>
  <p>{score}/100 — {statusLabel}</p>
  <span>{riskCount} riscos identificados</span>
</div>

// Estilo
.business-health {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--border-light);
}

.health-bar {
  width: 120px;
  height: 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
  overflow: hidden;
}

.health-fill {
  height: 100%;
  background: linear-gradient(90deg, #EF4444, #F59E0B, #10B981);
  transition: width 0.3s ease;
}
```

### 3. LOGOS Impact

**Objetivo**: Provar valor gerado.

```tsx
interface ImpactScoreProps {
  totalImpact: number;       // R$
  recoveredMoney: number;    // R$
  savedMoney: number;        // R$
  preventedLoss: number;     // R$
  additionalRevenue: number; // R$
  timeSaved: number;         // horas
  roi: number;               // multiplicador
}

// Visual
<div className="logos-impact">
  <h3>Desde que você começou a usar o LOGOS</h3>
  <div className="impact-value">
    R$ {formatMoney(totalImpact)} gerados
  </div>
  <div className="impact-meta">
    <span>{timeSaved} horas economizadas</span>
    <span>ROI: {roi}x</span>
  </div>
</div>

// Estilo
.logos-impact {
  padding: var(--space-4) 0;
  border-bottom: 1px solid var(--border-light);
  text-align: center;
}

.impact-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--signal-success);
  font-family: 'JetBrains Mono', monospace;
  margin: var(--space-2) 0;
}

.impact-meta {
  display: flex;
  gap: var(--space-3);
  justify-content: center;
  font-size: 14px;
  color: var(--text-secondary);
}
```

### 4. Decision Card

**Objetivo**: Comunicar decisão de forma extremamente clara.

```tsx
interface DecisionCardProps {
  id: string;
  priority: 1 | 2 | 3;
  icon: '🔴' | '🟡' | '🟢';
  title: string;
  impactType: 'recovery' | 'prevention' | 'savings' | 'growth';
  impactValue: number;  // R$
  timeEstimate: number; // minutos
  confidence: number;   // 0-100
  actionLabel: string;
  onExecute: () => void;
}

// Visual
<div className="decision-card" data-priority={priority}>
  <div className="decision-header">
    <span className="decision-icon">{icon}</span>
    <h4 className="decision-title">{title}</h4>
  </div>
  
  <div className="decision-meta">
    <div className="decision-impact">
      <span className="impact-label">{impactLabel}</span>
      <span className="impact-value">R$ {formatMoney(impactValue)}</span>
    </div>
    <div className="decision-specs">
      <span>{timeEstimate} minutos</span>
      <span>Confidence: {confidence}%</span>
    </div>
  </div>
  
  <button className="decision-action" onClick={onExecute}>
    {actionLabel} →
  </button>
</div>

// Estilo
.decision-card {
  padding: var(--space-4);
  background: var(--bg-primary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition: all 0.2s ease;
}

.decision-card:hover {
  border-color: var(--action-primary);
  box-shadow: var(--shadow-md);
}

.decision-card[data-priority="1"] {
  border-left: 4px solid var(--signal-danger);
}

.decision-card[data-priority="2"] {
  border-left: 4px solid var(--signal-warning);
}

.decision-card[data-priority="3"] {
  border-left: 4px solid var(--signal-success);
}

.decision-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.decision-icon {
  font-size: 24px;
}

.decision-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.decision-impact {
  margin-bottom: var(--space-2);
}

.impact-label {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: var(--space-1);
}

.impact-value {
  display: block;
  font-size: 24px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  color: var(--text-primary);
}

.decision-specs {
  display: flex;
  gap: var(--space-3);
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: var(--space-3);
}

.decision-action {
  width: 100%;
  padding: 12px 24px;
  background: var(--action-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease;
}

.decision-action:hover {
  background: var(--action-hover);
}

.decision-action:active {
  background: var(--action-active);
}
```

---

## 🎭 Estados

### Loading

```tsx
<div className="home-loading">
  <div className="loading-spinner" />
  <p>Analisando suas decisões...</p>
  <div className="loading-bar">
    <div className="loading-progress" />
  </div>
</div>
```

### Empty (Sem Decisões)

```tsx
<div className="home-empty">
  <div className="empty-icon">✅</div>
  <h2>Excelente notícia!</h2>
  <p>Nenhuma decisão urgente hoje.</p>
  <p>Seu negócio está sob controle.</p>
  <button className="empty-action">
    Ver relatório completo →
  </button>
</div>
```

### Error

```tsx
<div className="home-error">
  <div className="error-icon">⚠️</div>
  <h2>Não foi possível carregar suas decisões</h2>
  <p>Verifique sua conexão e tente novamente.</p>
  <button className="error-retry">
    Tentar novamente
  </button>
</div>
```

---

## ⚡ Performance

### Métricas Target

| Métrica | Target | Como Medir |
|---------|--------|------------|
| **First Contentful Paint** | < 500ms | Lighthouse |
| **Time to Interactive** | < 1s | Lighthouse |
| **Decision List Visible** | < 2s | Custom timing |
| **State Change** | < 150ms | React DevTools |
| **Bundle Size** | < 200KB | Webpack Bundle Analyzer |

### Otimizações

1. **Prioridade de Carregamento**
   - 0-100ms: Saudação + skeleton
   - 100-300ms: Business Health + Impact
   - 300-500ms: Top 3 decisões
   - 500ms+: Dados secundários

2. **Code Splitting**
   ```tsx
   // Lazy load componentes não-críticos
   const DecisionDetail = lazy(() => import('./DecisionDetail'));
   const HistoryView = lazy(() => import('./HistoryView'));
   ```

3. **Memoization**
   ```tsx
   const DecisionCard = memo(({ decision }) => {
     // ...
   }, (prev, next) => prev.decision.id === next.decision.id);
   ```

4. **Imagens Otimizadas**
   - Usar `next/image` com lazy loading
   - WebP format
   - Responsive images

---

## ♿ Acessibilidade

### WCAG 2.1 AA Compliance

#### Contraste

- **Texto normal**: Mínimo 4.5:1
- **Texto grande (≥18px)**: Mínimo 3:1
- **Elementos interativos**: Mínimo 3:1

#### Navegação por Teclado

```tsx
// Tab order lógico
<button tabIndex={1}>Decisão #1</button>
<button tabIndex={2}>Decisão #2</button>
<button tabIndex={3}>Decisão #3</button>

// Focus visible
.decision-action:focus-visible {
  outline: 2px solid var(--action-primary);
  outline-offset: 2px;
}
```

#### ARIA Labels

```tsx
<div 
  role="region" 
  aria-label="Decisões do dia"
  aria-describedby="decision-count"
>
  <p id="decision-count">
    Hoje existem {count} decisões importantes
  </p>
  {/* ... */}
</div>

<button 
  aria-label={`Executar decisão: ${title}`}
  onClick={onExecute}
>
  Executar Agora →
</button>
```

#### Screen Reader

```tsx
// Anúncio de mudanças
<div aria-live="polite" aria-atomic="true">
  {successMessage}
</div>

// Contador visível para SR
<span className="sr-only">
  {count} decisões pendentes
</span>
```

---

## 📱 Responsividade

### Breakpoints

```css
/* Mobile First */
--bp-sm: 640px;   /* Small tablets */
--bp-md: 768px;   /* Tablets */
--bp-lg: 1024px;  /* Desktop */
--bp-xl: 1280px;  /* Large desktop */
```

### Layout Adaptativo

#### Mobile (< 640px)

- Stack vertical completo
- Decisões ocupam 100% largura
- Scroll vertical permitido (max 2x viewport)
- Font sizes reduzidos 10-15%

#### Tablet (640px - 1024px)

- Container com max-width: 720px
- Decisões ainda 100% largura
- Sem scroll no estado inicial
- Font sizes normais

#### Desktop (> 1024px)

- Container com max-width: 1200px
- Decisões podem ter 2 colunas (se necessário no futuro)
- Sem scroll garantido
- Font sizes normais

---

## 🎬 Microinterações

### Princípio

> **"Animar apenas para comunicar mudança de estado. Nunca por estética."**

### Animations

#### Fade In (Loading → Ready)

```css
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.decision-card {
  animation: fadeIn 0.3s ease;
}

/* Stagger effect */
.decision-card:nth-child(1) { animation-delay: 0ms; }
.decision-card:nth-child(2) { animation-delay: 100ms; }
.decision-card:nth-child(3) { animation-delay: 200ms; }
```

#### Slide Out (Executado)

```css
@keyframes slideOut {
  to {
    opacity: 0;
    transform: translateX(100%);
  }
}

.decision-card[data-status="completed"] {
  animation: slideOut 0.4s ease forwards;
}
```

#### Success Pulse (Confirmação)

```css
@keyframes successPulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(16, 185, 129, 0.3);
  }
}

.decision-card[data-status="success"] {
  animation: successPulse 0.6s ease;
}
```

---

## 🧪 Teste de 10 Segundos

### Protocolo

1. **Recrutamento**
   - Proprietário de posto (não usuário atual)
   - Sem contexto prévio sobre LOGOS
   - Idade: 30-60 anos

2. **Execução**
   - Mostrar Home por 10 segundos
   - Ocultar tela
   - Fazer 3 perguntas

3. **Perguntas**
   ```
   Q1: O que você deve fazer hoje?
   Q2: Quanto dinheiro está envolvido?
   Q3: Qual é a decisão mais importante?
   ```

4. **Critério de Sucesso**
   - ≥ 80% das respostas corretas
   - Sem hesitação > 3 segundos por pergunta
   - Nenhuma confusão ou dúvida expressa

5. **Métricas**
   - Time to Understand: < 10s
   - Confidence Score: ≥ 4/5
   - Execution Intent: "Sim, executaria agora"

---

## ✅ Checklist de Validação

### Design

- [ ] Paleta de cores definida
- [ ] Tipografia especificada
- [ ] Espaçamento consistente (8px base)
- [ ] Componentes documentados
- [ ] Estados visuais especificados
- [ ] Animações definidas

### UX

- [ ] Cabe em 100vh sem scroll (desktop)
- [ ] Cabe em 200vh max (mobile)
- [ ] Carregamento < 2s
- [ ] Interações < 150ms
- [ ] Feedback visual imediato

### Acessibilidade

- [ ] Contraste WCAG AA
- [ ] Navegação por teclado
- [ ] ARIA labels corretos
- [ ] Screen reader friendly
- [ ] Focus visible

### Responsividade

- [ ] Mobile (< 640px)
- [ ] Tablet (640-1024px)
- [ ] Desktop (> 1024px)
- [ ] Touch targets ≥ 44px

### Performance

- [ ] FCP < 500ms
- [ ] TTI < 1s
- [ ] Bundle < 200KB
- [ ] Code splitting
- [ ] Lazy loading

---

## 📚 Referências

- [MOMENTO_ZERO.md](MOMENTO_ZERO.md) — Conceito original
- [LOGOS_IMPACT_SYSTEM.md](LOGOS_IMPACT_SYSTEM.md) — Sistema de impacto
- [PRODUCT_CONSTITUTION.md](PRODUCT_CONSTITUTION.md) — Princípios
- [Figma Design System](https://figma.com/logos-design-system) — Design tokens

---

**[MOMENTO ZERO UX — SPRINT UX-01]**

*Status: OFFICIAL | Type: UX_SPEC | Version: 1.0 | Focus: Clarity in 10 seconds*
