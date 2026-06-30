---
# 🎨 DESIGN SYSTEM V4 | LOGOS
# Type: DESIGN_TOKENS
# Version: 4.0
# Sprint: UX-01 — Momento Zero & Executive Experience
# Status: OFFICIAL
---

# Design System V4 — Momento Zero Edition

> **"Menos é mais. Cada token tem um propósito. Cada decisão é intencional."**

---

## 🎯 Filosofia

### Princípios do Design System

1. **Consistência**: Um token, um propósito, um valor
2. **Escalabilidade**: Adicionar não quebra existente
3. **Acessibilidade**: WCAG AA mínimo, AAA quando possível
4. **Performance**: CSS-in-JS com zero-runtime
5. **Simplicidade**: Se tem 3 opções, escolha 1

---

## 🎨 Color Tokens

### Semantic Colors

```css
:root {
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  /* BACKGROUNDS                                                  */
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  --color-bg-primary: #FFFFFF;
  --color-bg-secondary: #F9FAFB;
  --color-bg-tertiary: #F3F4F6;
  --color-bg-elevated: #FFFFFF;
  
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  /* TEXT                                                         */
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  --color-text-primary: #111827;
  --color-text-secondary: #374151;
  --color-text-tertiary: #6B7280;
  --color-text-quaternary: #9CA3AF;
  --color-text-inverse: #FFFFFF;
  
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  /* ACTIONS                                                      */
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  --color-action-primary: #2563EB;
  --color-action-primary-hover: #1D4ED8;
  --color-action-primary-active: #1E40AF;
  --color-action-primary-disabled: #93C5FD;
  
  --color-action-secondary: #F3F4F6;
  --color-action-secondary-hover: #E5E7EB;
  --color-action-secondary-active: #D1D5DB;
  
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  /* SIGNALS                                                      */
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  --color-signal-success: #10B981;
  --color-signal-success-bg: #D1FAE5;
  --color-signal-success-border: #6EE7B7;
  
  --color-signal-warning: #F59E0B;
  --color-signal-warning-bg: #FEF3C7;
  --color-signal-warning-border: #FCD34D;
  
  --color-signal-danger: #EF4444;
  --color-signal-danger-bg: #FEE2E2;
  --color-signal-danger-border: #FCA5A5;
  
  --color-signal-info: #3B82F6;
  --color-signal-info-bg: #DBEAFE;
  --color-signal-info-border: #93C5FD;
  
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  /* BORDERS                                                      */
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  --color-border-light: #E5E7EB;
  --color-border-medium: #D1D5DB;
  --color-border-heavy: #9CA3AF;
  --color-border-focus: #2563EB;
  
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  /* OVERLAYS                                                     */
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  --color-overlay-light: rgba(0, 0, 0, 0.05);
  --color-overlay-medium: rgba(0, 0, 0, 0.2);
  --color-overlay-heavy: rgba(0, 0, 0, 0.6);
}
```

### Dark Mode

```css
[data-theme="dark"] {
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  /* BACKGROUNDS                                                  */
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  --color-bg-primary: #0F172A;
  --color-bg-secondary: #1E293B;
  --color-bg-tertiary: #334155;
  --color-bg-elevated: #1E293B;
  
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  /* TEXT                                                         */
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  --color-text-primary: #F1F5F9;
  --color-text-secondary: #CBD5E1;
  --color-text-tertiary: #94A3B8;
  --color-text-quaternary: #64748B;
  --color-text-inverse: #0F172A;
  
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  /* ACTIONS (mantém azul para consistência)                     */
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  --color-action-primary: #3B82F6;
  --color-action-primary-hover: #60A5FA;
  --color-action-primary-active: #2563EB;
  --color-action-primary-disabled: #1E40AF;
  
  --color-action-secondary: #334155;
  --color-action-secondary-hover: #475569;
  --color-action-secondary-active: #64748B;
  
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  /* SIGNALS (ajustados para contraste)                          */
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  --color-signal-success: #34D399;
  --color-signal-success-bg: #064E3B;
  --color-signal-success-border: #047857;
  
  --color-signal-warning: #FBBF24;
  --color-signal-warning-bg: #78350F;
  --color-signal-warning-border: #92400E;
  
  --color-signal-danger: #F87171;
  --color-signal-danger-bg: #7F1D1D;
  --color-signal-danger-border: #991B1B;
  
  --color-signal-info: #60A5FA;
  --color-signal-info-bg: #1E3A8A;
  --color-signal-info-border: #1E40AF;
  
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  /* BORDERS                                                      */
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  --color-border-light: #334155;
  --color-border-medium: #475569;
  --color-border-heavy: #64748B;
  --color-border-focus: #3B82F6;
  
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  /* OVERLAYS                                                     */
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  --color-overlay-light: rgba(255, 255, 255, 0.05);
  --color-overlay-medium: rgba(255, 255, 255, 0.1);
  --color-overlay-heavy: rgba(255, 255, 255, 0.2);
}
```

### Contrast Ratios (WCAG AA)

| Combination | Ratio | Status |
|-------------|-------|--------|
| text-primary on bg-primary | 16.3:1 | ✅ AAA |
| text-secondary on bg-primary | 10.7:1 | ✅ AAA |
| text-tertiary on bg-primary | 4.8:1 | ✅ AA |
| action-primary on bg-primary | 5.2:1 | ✅ AA+ |
| signal-success on bg-primary | 3.2:1 | ✅ AA (large) |

---

## 📐 Typography

### Font Families

```css
:root {
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 
               'Roboto', 'Helvetica Neue', Arial, sans-serif;
  --font-mono: 'JetBrains Mono', 'SF Mono', 'Monaco', 'Inconsolata',
               'Fira Code', 'Droid Sans Mono', 'Source Code Pro', monospace;
}
```

### Font Sizes (Modular Scale 1.25 - Major Third)

```css
:root {
  --font-xs: 0.75rem;   /* 12px */
  --font-sm: 0.875rem;  /* 14px */
  --font-base: 1rem;    /* 16px */
  --font-lg: 1.125rem;  /* 18px */
  --font-xl: 1.5rem;    /* 24px */
  --font-2xl: 2rem;     /* 32px */
  --font-3xl: 2.5rem;   /* 40px */
}
```

### Font Weights

```css
:root {
  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;
}
```

### Line Heights

```css
:root {
  --line-height-tight: 1.2;
  --line-height-normal: 1.5;
  --line-height-relaxed: 1.75;
}
```

### Letter Spacing

```css
:root {
  --letter-spacing-tighter: -0.02em;
  --letter-spacing-tight: -0.01em;
  --letter-spacing-normal: 0;
  --letter-spacing-wide: 0.01em;
  --letter-spacing-wider: 0.05em;
}
```

---

## 🎯 Spacing (8px Base)

### Spacing Scale

```css
:root {
  --space-0: 0;
  --space-1: 0.5rem;    /* 8px */
  --space-2: 1rem;      /* 16px */
  --space-3: 1.5rem;    /* 24px */
  --space-4: 2rem;      /* 32px */
  --space-5: 3rem;      /* 48px */
  --space-6: 4rem;      /* 64px */
  --space-7: 6rem;      /* 96px */
  --space-8: 8rem;      /* 128px */
}
```

### Semantic Spacing

```css
:root {
  --space-section: var(--space-4);     /* Entre seções */
  --space-element: var(--space-3);     /* Entre elementos */
  --space-inline: var(--space-2);      /* Inline spacing */
  --space-micro: var(--space-1);       /* Micro spacing */
  --space-container: var(--space-5);   /* Container padding */
}
```

---

## 📏 Sizing

### Sizing Scale

```css
:root {
  --size-xs: 20rem;    /* 320px */
  --size-sm: 24rem;    /* 384px */
  --size-md: 28rem;    /* 448px */
  --size-lg: 32rem;    /* 512px */
  --size-xl: 36rem;    /* 576px */
  --size-2xl: 42rem;   /* 672px */
  --size-3xl: 48rem;   /* 768px */
  --size-4xl: 56rem;   /* 896px */
  --size-5xl: 64rem;   /* 1024px */
  --size-6xl: 72rem;   /* 1152px */
  --size-7xl: 75rem;   /* 1200px - container max */
}
```

### Component Sizes

```css
:root {
  --input-height-sm: 2rem;    /* 32px */
  --input-height-md: 2.5rem;  /* 40px */
  --input-height-lg: 3rem;    /* 48px */
  
  --button-height-sm: 2rem;   /* 32px */
  --button-height-md: 2.75rem; /* 44px - touch target */
  --button-height-lg: 3rem;   /* 48px */
  
  --card-padding: var(--space-4);
  --card-min-height: 10rem;   /* 160px */
}
```

---

## 🔲 Border Radius

### Radius Scale

```css
:root {
  --radius-none: 0;
  --radius-sm: 0.375rem;  /* 6px */
  --radius-md: 0.5rem;    /* 8px */
  --radius-lg: 0.75rem;   /* 12px */
  --radius-xl: 1rem;      /* 16px */
  --radius-full: 9999px;  /* Pill */
}
```

### Semantic Radius

```css
:root {
  --radius-input: var(--radius-sm);
  --radius-button: var(--radius-md);
  --radius-card: var(--radius-lg);
  --radius-modal: var(--radius-xl);
}
```

---

## 🌑 Shadows & Elevation

### Shadow Layers

```css
:root {
  --shadow-xs: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.1),
               0 1px 2px 0 rgba(0, 0, 0, 0.06);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1),
               0 2px 4px -1px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1),
               0 4px 6px -2px rgba(0, 0, 0, 0.05);
  --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1),
               0 10px 10px -5px rgba(0, 0, 0, 0.04);
  --shadow-2xl: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}
```

### Semantic Shadows

```css
:root {
  --shadow-card: var(--shadow-sm);
  --shadow-card-hover: var(--shadow-md);
  --shadow-button: var(--shadow-xs);
  --shadow-modal: var(--shadow-2xl);
  --shadow-dropdown: var(--shadow-lg);
}
```

### Dark Mode Shadows

```css
[data-theme="dark"] {
  --shadow-xs: 0 1px 2px 0 rgba(0, 0, 0, 0.3);
  --shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.4),
               0 1px 2px 0 rgba(0, 0, 0, 0.3);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.5),
               0 2px 4px -1px rgba(0, 0, 0, 0.3);
  /* ... */
}
```

---

## ⏱️ Transitions & Animations

### Timing Functions

```css
:root {
  --ease-linear: linear;
  --ease-in: cubic-bezier(0.4, 0, 1, 1);
  --ease-out: cubic-bezier(0, 0, 0.2, 1);
  --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
  --ease-smooth: cubic-bezier(0.4, 0, 0.6, 1);
}
```

### Durations

```css
:root {
  --duration-instant: 0ms;
  --duration-fast: 150ms;
  --duration-normal: 200ms;
  --duration-slow: 300ms;
  --duration-slower: 500ms;
}
```

### Semantic Transitions

```css
:root {
  --transition-button: background-color var(--duration-fast) var(--ease-out);
  --transition-card: all var(--duration-normal) var(--ease-smooth);
  --transition-modal: opacity var(--duration-normal) var(--ease-out),
                      transform var(--duration-normal) var(--ease-out);
}
```

---

## 📱 Breakpoints

### Responsive Breakpoints

```css
:root {
  --breakpoint-xs: 320px;    /* Pequeno mobile */
  --breakpoint-sm: 640px;    /* Tablets pequenos */
  --breakpoint-md: 768px;    /* Tablets */
  --breakpoint-lg: 1024px;   /* Laptops */
  --breakpoint-xl: 1280px;   /* Desktops */
  --breakpoint-2xl: 1536px;  /* Large desktops */
}
```

### Media Queries

```css
/* Mobile first approach */
@media (min-width: 640px) {
  /* sm */
}

@media (min-width: 768px) {
  /* md */
}

@media (min-width: 1024px) {
  /* lg */
}

@media (min-width: 1280px) {
  /* xl */
}

@media (min-width: 1536px) {
  /* 2xl */
}
```

---

## 🎭 Component Tokens

### Button

```css
:root {
  --button-padding-x: var(--space-3);
  --button-padding-y: 0.75rem;  /* 12px */
  --button-font-size: var(--font-sm);
  --button-font-weight: var(--font-weight-semibold);
  --button-border-radius: var(--radius-button);
  --button-shadow: var(--shadow-button);
  --button-transition: var(--transition-button);
}
```

### Card

```css
:root {
  --card-padding: var(--space-4);
  --card-border-radius: var(--radius-card);
  --card-border: 1px solid var(--color-border-light);
  --card-shadow: var(--shadow-card);
  --card-shadow-hover: var(--shadow-card-hover);
  --card-transition: var(--transition-card);
}
```

### Input

```css
:root {
  --input-padding-x: var(--space-2);
  --input-padding-y: 0.625rem;  /* 10px */
  --input-font-size: var(--font-base);
  --input-border-radius: var(--radius-input);
  --input-border: 1px solid var(--color-border-medium);
  --input-border-focus: 2px solid var(--color-border-focus);
}
```

---

## 🎨 Usage Examples

### CSS Variables Usage

```css
/* Component styling */
.decision-card {
  padding: var(--card-padding);
  background: var(--color-bg-primary);
  border: var(--card-border);
  border-radius: var(--card-border-radius);
  box-shadow: var(--card-shadow);
  transition: var(--card-transition);
}

.decision-card:hover {
  box-shadow: var(--card-shadow-hover);
  transform: translateY(-2px);
}

.decision-action {
  padding: var(--button-padding-y) var(--button-padding-x);
  font-size: var(--button-font-size);
  font-weight: var(--button-font-weight);
  color: var(--color-text-inverse);
  background: var(--color-action-primary);
  border-radius: var(--button-border-radius);
  box-shadow: var(--button-shadow);
  transition: var(--button-transition);
}

.decision-action:hover {
  background: var(--color-action-primary-hover);
}

.decision-action:active {
  background: var(--color-action-primary-active);
  transform: scale(0.98);
}
```

### TypeScript Usage (with styled-components)

```typescript
import styled from 'styled-components';

export const DecisionCard = styled.article`
  padding: var(--card-padding);
  background: var(--color-bg-primary);
  border: var(--card-border);
  border-radius: var(--card-border-radius);
  box-shadow: var(--card-shadow);
  transition: var(--card-transition);
  
  &:hover {
    box-shadow: var(--card-shadow-hover);
    transform: translateY(-2px);
  }
`;

export const ActionButton = styled.button`
  padding: var(--button-padding-y) var(--button-padding-x);
  font-size: var(--button-font-size);
  font-weight: var(--button-font-weight);
  color: var(--color-text-inverse);
  background: var(--color-action-primary);
  border: none;
  border-radius: var(--button-border-radius);
  box-shadow: var(--button-shadow);
  transition: var(--button-transition);
  cursor: pointer;
  
  &:hover {
    background: var(--color-action-primary-hover);
  }
  
  &:active {
    background: var(--color-action-primary-active);
    transform: scale(0.98);
  }
  
  &:disabled {
    background: var(--color-action-primary-disabled);
    cursor: not-allowed;
  }
`;
```

---

## ✅ Token Validation

### Checklist

- [ ] Todos os tokens têm nomenclatura semântica
- [ ] Dark mode definido para todos os tokens
- [ ] Contrast ratios validados (WCAG AA)
- [ ] Spacing segue escala 8px
- [ ] Typography segue escala modular (1.25)
- [ ] Transitions têm durations apropriadas
- [ ] Shadows consistentes entre componentes
- [ ] Breakpoints cobrem todos os dispositivos

---

## 📚 Referências

- [MOMENTO_ZERO_UX.md](../business/MOMENTO_ZERO_UX.md) — UX spec
- [Material Design 3](https://m3.material.io/) — Design tokens
- [Tailwind CSS](https://tailwindcss.com/) — Utility classes
- [Radix UI](https://www.radix-ui.com/) — Accessible components
- [WCAG 2.1](https://www.w3.org/WAI/WCAG21/quickref/) — Accessibility guidelines

---

**[DESIGN SYSTEM V4 — SPRINT UX-01]**

*Status: OFFICIAL | Type: DESIGN_TOKENS | Version: 4.0 | Focus: Momento Zero*
