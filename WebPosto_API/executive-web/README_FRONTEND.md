# LOGOS Executive Frontend — Sprint 51

Este é o cockpit executivo desenvolvido em React, Next.js, Tailwind CSS e TypeScript, focado na gestão estratégica do Grupo Lisboa.

## 🚀 Tecnologias
- **Framework:** Next.js 16+ (App Router)
- **Estilização:** Tailwind CSS v4
- **Gráficos:** Recharts
- **Componentes:** Radix UI + Lucide Icons
- **Animações:** Motion (Framer Motion)
- **Gestão de Tema:** Next Themes (Dark/Light Mode)

## 📁 Estrutura de Rotas
- `/dashboard/executive`: Cockpit 30s com KPIs, Vácuo de Caixa e Alertas.
- `/executive/alerts`: Central de Gestão de Alertas e Exceções.
- `/executive/simulator`: Simulador de Impacto Financeiro (Preço vs Volume vs Antecipação).
- `/operational/tanks`: Monitoramento de perdas físicas vs térmicas nos tanques.

## 🛠️ Como Executar

### 1. Requisitos
- Node.js 20+
- Backend Logos API rodando em `http://localhost:8040` (ou configurar `.env`)

### 2. Instalação
```bash
cd executive-web
npm install
```

### 3. Desenvolvimento
```bash
npm run dev
```
O servidor iniciará em `http://localhost:3006` (conforme logs anteriores).

### 4. Build
```bash
npm run build
npm start
```

## 🧠 Inteligência do Cockpit
O dashboard consome o endpoint consolidado `GET /api/v1/executive/dashboard/bundle`, garantindo carregamento ultrarrápido (< 1s) através de execução paralela no backend.

Os alertas proativos permitem a resolução direta pela diretoria, impactando o fluxo de auditoria em tempo real.
