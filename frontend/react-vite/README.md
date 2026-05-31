# WebPosto Explorer (React + Vite)

Scaffold mínimo para conectar com a `FastAPI` do projeto.

Pré-requisitos:
- Node.js 18+ e npm/yarn

Instalação e execução:

```bash
cd frontend/react-vite
npm install
npm run dev
```

Configuração da API:
- Por padrão o `VITE_API_BASE` usa `http://localhost:8000`.
- Para alterar, crie um arquivo `.env` na pasta `react-vite` com:

```
VITE_API_BASE=http://localhost:8000
```

O `App.jsx` já contém exemplos de endpoints; substitua pela lista completa conforme `OPERACOES_COMPLETAS_COM_TOKEN.md`.

Próximos passos que posso fazer por você:
- Adicionar `axios` instance com interceptors e token armazenado.
- Gerar lista completa dos 51 endpoints no UI.
- Implementar testes e Storybook.

