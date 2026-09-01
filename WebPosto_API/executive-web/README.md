# LOGOS Executive Finance

Dashboard executivo de tesouraria construído com Next.js 16, React 19, TypeScript, Tailwind CSS 4, componentes no padrão shadcn/ui, Recharts, Lucide e Motion.

## Arquitetura

- `src/app`: composição da página e renderização no servidor.
- `src/components/executive`: sidebar, navegação móvel, KPIs, gráficos, alertas e tabela.
- `src/components/ui`: componentes visuais reutilizáveis.
- `src/lib/treasury.ts`: contrato tipado e adaptador da API WebPosto.
- `src/lib/utils.ts`: formatação e utilitários de estilo.

## Dados

Defina `WEBPOSTO_API_URL` com a URL do backend. O padrão local é `http://127.0.0.1:8000`. O dashboard usa apenas as três empresas licenciadas e não inventa valores quando uma fonte está indisponível.

## Execução

```bash
npm install
npm run dev
```

Validação de produção:

```bash
npm run lint
npm run build
```
