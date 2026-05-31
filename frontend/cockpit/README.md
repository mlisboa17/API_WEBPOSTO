# Logos Cockpit — Next.js + shadcn/ui

Painel gerencial **estilo Omie ERP** para o Posto VIP (WebPosto Quality).

## Visual

Inspirado na interface do **Omie** (ERP brasileiro):

- Sidebar azul corporativa com menu por módulos
- Cards KPI com ícone circular e sombra suave
- Filtros de período em pills (Hoje · 7 dias · Mensal)
- Tipografia Inter · paleta azul `#0068FF` · dark premium
- Base: **shadcn/ui dashboard-01** (layout pronto)

## Subir

**Backend** (terminal 1):

```bash
cd WebPosto_API
python src/presentation/app.py
```

**Frontend** (terminal 2):

```bash
cd frontend/cockpit
cp .env.example .env.local
npm install
npm run dev
```

Abra **http://localhost:3000/dashboard**

## Rotas

| Rota | Status |
|------|--------|
| `/dashboard` | KPIs + galonagem (dados reais) |
| `/abastecimento` | Em desenvolvimento |
| `/vendas` | Em desenvolvimento |
| `/produtos` | Em desenvolvimento |
| `/auditoria` | Em desenvolvimento |
