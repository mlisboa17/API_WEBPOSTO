# Design System
## Sistema de Design - LOGOS SPACE

**Versão:** 1.0
**Data:** 2026-06-28
**Status:** Ativo
**Sprint:** DOCS-02

---

## 🎨 Paleta de Cores

### Cores Primárias

| Nome | Hex | RGB | Uso |
|------|-----|-----|-----|
| **Dark Background** | `#0a0a0a` | 10, 10, 10 | Fundo principal |
| **Card Background** | `#1a1a1a` | 26, 26, 26 | Cards, containers |
| **Border Color** | `#2a2a2a` | 42, 42, 42 | Bordas, divisores |
| **Text Primary** | `#ffffff` | 255, 255, 255 | Títulos, textos principais |
| **Text Secondary** | `#e0e0e0` | 224, 224, 224 | Textos secundários |
| **Text Muted** | `#888888` | 136, 136, 136 | Labels, placeholders |

### Cores de Status

| Nome | Hex | Uso |
|------|-----|-----|
| **Success** | `#10b981` | Sucesso, positivo, crescimento |
| **Warning** | `#f59e0b` | Atenção, alerta |
| **Error** | `#ef4444` | Erro, perda, crítico |
| **Info** | `#3b82f6` | Informação, neutro |
| **Purple** | `#8b5cf6` | Destaque, IA, premium |

### Cores de Dados

| Nome | Hex | Uso |
|------|-----|-----|
| **Chart Blue** | `#3b82f6` | Séries primárias |
| **Chart Green** | `#10b981` | Crescimento, positivo |
| **Chart Orange** | `#f97316` | Média, alerta |
| **Chart Red** | `#ef4444` | Negativo, perda |
| **Chart Purple** | `#8b5cf6` | Meta, projeção |

---

## 🔤 Tipografia

### Font Family

**Stack:** `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif`

**Princípio:** Sistema font (usa a fonte nativa do OS)

### Hierarquia

| Elemento | Tamanho | Peso | Altura | Uso |
|----------|---------|------|--------|-----|
| **H1** | 32px | 700 (Bold) | 1.2 | Títulos de página |
| **H2** | 24px | 600 (Semibold) | 1.3 | Seções principais |
| **H3** | 20px | 600 (Semibold) | 1.4 | Subseções |
| **H4** | 16px | 600 (Semibold) | 1.4 | Cards, headers |
| **Body** | 14px | 400 (Regular) | 1.6 | Texto corrido |
| **Small** | 12px | 400 (Regular) | 1.5 | Labels, metadata |
| **Tiny** | 10px | 400 (Regular) | 1.4 | Tags, badges |

### Estilos

```css
/* Título de Página */
.page-title {
  font-size: 32px;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 8px;
}

/* Subtítulo */
.page-subtitle {
  font-size: 14px;
  color: #888888;
}

/* Label */
.label {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #888888;
}

/* Card Value */
.card-value {
  font-size: 36px;
  font-weight: 700;
  color: #ffffff;
}

/* Table Header */
.table-header {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  color: #888888;
}

/* Table Cell */
.table-cell {
  font-size: 14px;
  color: #e0e0e0;
}
```

---

## 📦 Cards

### Card Padrão

```css
.card {
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 12px;
  padding: 24px;
}
```

### Card com Hover

```css
.card-hover {
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 12px;
  padding: 24px;
  transition: border-color 0.2s, transform 0.2s;
}

.card-hover:hover {
  border-color: #3b82f6;
  transform: translateY(-2px);
}
```

### KPI Card

```css
.kpi-card {
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 12px;
  padding: 24px;
}

.kpi-card .label {
  font-size: 14px;
  font-weight: 600;
  color: #888888;
  text-transform: uppercase;
  margin-bottom: 12px;
}

.kpi-card .value {
  font-size: 36px;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 8px;
}

.kpi-card .change {
  font-size: 13px;
}

.kpi-card .change.positive {
  color: #10b981;
}

.kpi-card .change.negative {
  color: #ef4444;
}
```

---

## 🧭 Sidebar

### Layout

```css
.sidebar {
  width: 260px;
  height: 100vh;
  background: #0a0a0a;
  border-right: 1px solid #2a2a2a;
  padding: 20px 0;
  position: fixed;
  left: 0;
  top: 0;
}
```

### Item de Menu

```css
.sidebar-item {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  color: #e0e0e0;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}

.sidebar-item:hover {
  background: #1a1a1a;
  color: #ffffff;
}

.sidebar-item.active {
  background: #1a1a1a;
  color: #3b82f6;
  border-left: 3px solid #3b82f6;
}

.sidebar-item .icon {
  width: 20px;
  height: 20px;
  margin-right: 12px;
}

.sidebar-item .label {
  font-size: 14px;
  font-weight: 500;
}
```

---

## 📊 Gráficos

### Cores para Gráficos

```javascript
const CHART_COLORS = {
  primary: '#3b82f6',    // Blue
  secondary: '#10b981',  // Green
  tertiary: '#f97316',   // Orange
  quaternary: '#8b5cf6', // Purple
  negative: '#ef4444',   // Red
};
```

### Estilo de Linha

```css
.chart-line {
  stroke-width: 2;
  fill: none;
}

.chart-area {
  fill-opacity: 0.1;
}

.chart-grid {
  stroke: #2a2a2a;
  stroke-dasharray: 4, 4;
}
```

### Tooltip de Gráfico

```css
.chart-tooltip {
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 14px;
  color: #e0e0e0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
}
```

---

## 📐 Spacing

### Escala

| Token | Valor | Uso |
|-------|-------|-----|
| **xs** | 4px | Ícones pequenos, gaps mínimos |
| **sm** | 8px | Labels, badges |
| **md** | 12px | Inputs pequenos |
| **base** | 16px | Padrão para textos |
| **lg** | 20px | Cards, containers |
| **xl** | 24px | Cards grandes, sections |
| **2xl** | 32px | Headers, grandes áreas |
| **3xl** | 48px | Page margins |

### Grid

```css
/* Container */
.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

/* Grid de Cards */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

/* Grid 4 colunas */
.grid-4 {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}
```

---

## 🔷 Iconografia

### Princípios

- Usar SVG inline (não font icons)
- Tamanho padrão: 20x20px
- Stroke-width: 2
- Cores herdadas do pai

### Ícones Comuns

| Ícone | Código | Uso |
|-------|--------|-----|
| **Dashboard** | `<svg>...</svg>` | Home, overview |
| **TrendingUp** | `<svg>...</svg>` | Crescimento, positivo |
| **TrendingDown** | `<svg>...</svg>` | Decrescimento, negativo |
| **Dollar** | `<svg>...</svg>` | Financeiro |
| **Fuel** | `<svg>...</svg>` | Combustível |
| **Box** | `<svg>...</svg>` | Estoque |
| **Users** | `<svg>...</svg>` | Clientes |
| **Alert** | `<svg>...</svg>` | Alertas |
| **Settings** | `<svg>...</svg>` | Configurações |

---

## ✨ Motion

### Durações

| Token | Valor | Uso |
|-------|-------|-----|
| **fast** | 100ms | Hover states |
| **normal** | 200ms | Transições padrão |
| **slow** | 300ms | Modais, drawers |

### Curvas

```css
/* Padrão */
--ease-default: cubic-bezier(0.4, 0, 0.2, 1);

/* Entrada */
--ease-in: cubic-bezier(0.4, 0, 1, 1);

/* Saída */
--ease-out: cubic-bezier(0, 0, 0.2, 1);
```

### Animações

```css
/* Hover Scale */
.hover-scale {
  transition: transform 200ms var(--ease-default);
}

.hover-scale:hover {
  transform: scale(1.02);
}

/* Fade In */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.fade-in {
  animation: fadeIn 300ms var(--ease-out) forwards;
}

/* Skeleton Shimmer */
@keyframes shimmer {
  0% {
    background-position: -200px 0;
  }
  100% {
    background-position: calc(200px + 100%) 0;
  }
}

.skeleton {
  background: linear-gradient(
    90deg,
    #1a1a1a 25%,
    #2a2a2a 50%,
    #1a1a1a 75%
  );
  background-size: 200px 100%;
  animation: shimmer 1.5s infinite;
}
```

---

## 🌙 Dark Theme (Padrão)

O LOGOS usa **dark theme como padrão**.

### Por quê?

- Reduz fadiga visual em dashboards longos
- Destaca dados coloridos
- Estética premium/moderna
- Consistência com ferramentas de analytics

### Implementação

```css
/* Base */
:root {
  --bg-primary: #0a0a0a;
  --bg-secondary: #1a1a1a;
  --bg-tertiary: #2a2a2a;
  
  --text-primary: #ffffff;
  --text-secondary: #e0e0e0;
  --text-muted: #888888;
  
  --border-color: #2a2a2a;
  
  --success: #10b981;
  --warning: #f59e0b;
  --error: #ef4444;
  --info: #3b82f6;
  --accent: #8b5cf6;
}

/* Uso */
body {
  background: var(--bg-primary);
  color: var(--text-primary);
}
```

---

## 📱 Responsividade

### Breakpoints

| Breakpoint | Largura | Ajustes |
|------------|---------|---------|
| **Mobile** | < 768px | Sidebar colapsada, cards 1 coluna |
| **Tablet** | 768px - 1024px | Sidebar colapsada, cards 2 colunas |
| **Desktop** | 1024px - 1440px | Sidebar expandida, cards 3 colunas |
| **Large** | > 1440px | Sidebar expandida, cards 4 colunas |

### Mobile

```css
@media (max-width: 768px) {
  .sidebar {
    transform: translateX(-100%);
    transition: transform 300ms ease;
  }
  
  .sidebar.open {
    transform: translateX(0);
  }
  
  .main-content {
    margin-left: 0;
  }
  
  .grid {
    grid-template-columns: 1fr;
  }
}
```

---

## 🎯 Componentes

### Botões

```css
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 200ms ease;
  border: none;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover {
  background: #2563eb;
}

.btn-secondary {
  background: #1a1a1a;
  color: #e0e0e0;
  border: 1px solid #2a2a2a;
}

.btn-secondary:hover {
  background: #2a2a2a;
}
```

### Inputs

```css
.input {
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  padding: 10px 14px;
  color: #e0e0e0;
  font-size: 14px;
  transition: border-color 200ms ease;
}

.input:focus {
  outline: none;
  border-color: #3b82f6;
}

.input::placeholder {
  color: #666666;
}
```

### Badges

```css
.badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}

.badge-success {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
}

.badge-warning {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

.badge-error {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}
```

---

## 📚 Uso

### Implementação

1. **Importar CSS base**
   ```html
   <link rel="stylesheet" href="styles.css">
   ```

2. **Usar variáveis CSS**
   ```css
   .my-component {
     background: var(--bg-secondary);
     color: var(--text-primary);
   }
   ```

3. **Seguir hierarquia tipográfica**
   - Não inventar novos tamanhos
   - Usar tokens existentes

4. **Respeitar espaçamento**
   - Usar escala definida
   - Manter consistência

---

**[DESIGN SYSTEM — APROVADO]**

*Manter atualizado ao adicionar novos componentes*
