# Validacao Local - Aba Combustiveis

## 1. Comando usado para subir backend

```powershell
.\.venv\Scripts\activate; uvicorn src.main:app --host 0.0.0.0 --port 8040 --reload
```

Status: backend iniciado com sucesso em http://127.0.0.1:8040.

## 2. Comando usado para subir frontend

Nao existe processo frontend separado neste projeto para a tela financeira.
O frontend foi servido pelo proprio backend FastAPI via rota:

- `/app/financial`
- assets em `/frontend/*`

## 3. URL acessada

- URL validada: `http://localhost:8040/app/financial?view=fuel&dataInicial=2026-06-01&dataFinal=2026-06-07`
- A URL foi normalizada para `view=fuels` internamente.

## 4. Status do endpoint

Endpoint validado:

- `GET /api/v1/fuel/executive?dataInicial=2026-06-01&dataFinal=2026-06-07` -> HTTP 200
- `GET /api/v1/fuel/executive?dataInicial=2026-05-09&dataFinal=2026-06-08` -> HTTP 200

## 5. Resumo dos dados retornados

### Periodo 2026-06-01 a 2026-06-07

- litrosTotal: `24889.66`
- filiais: `2`
- combustiveis: `8`
- ranking: `2 entradas`
- kpis: presentes (litrosVendidos, combustivelLider, filialLider, participacaoDiesel, participacaoGasolina, participacaoEtanol)

### Periodo de referencia Sprint (2026-05-09 a 2026-06-08)

- litrosTotal: `283372.988`
- filiais: `2`
- combustiveis: `8`
- cobertura codigos: `11495,5555`

## 6. Validacao visual dos componentes

Validado em navegador integrado (snapshot da pagina):

- Aba `Operacional > Combustiveis` visivel no menu.
- 6 cards KPI visiveis.
- Grafico volume por combustivel visivel.
- Grafico volume por filial visivel.
- Grafico participacao % visivel.
- Tabela `Filial x Combustivel x Litros x Participacao x Data` visivel.
- Filtros funcionando:
  - busca rapida `AP CASA CAIADA` reduziu de `28 registros exibidos` para `4 registros exibidos`.
- Autosoma funcionando:
  - rodape exibiu `Total filtrado` e `Total da pagina` com `Litros: 6.410,52`.
- Exportacao visivel e acionavel:
  - botoes `Exportar CSV` e `Exportar PDF` presentes e clicaveis.

Aviso de cobertura parcial visivel na tela:

- `Cobertura parcial: dados disponiveis apenas para AP CASA CAIADA e POSTO VIP.`

## 7. Erros encontrados

1. `ModuleNotFoundError: No module named 'jwt'` na subida da API principal.
2. UI bloqueada por tentativa de carregar snapshot de auditoria inexistente (`/snapshots/snapshot_20260601_20260607.json`).

## 8. Correçoes feitas

1. Dependencia JWT:
   - instalacao local: `pip install PyJWT`
   - adicao em `requirements.txt`
   - adicao em `pyproject.toml`
2. Frontend:
   - suporte a URL `view=fuel` (alias para `view=fuels`)
   - aviso de cobertura parcial adicionado na pagina de combustiveis
   - modo live forcado em `frontend/services/api.js` para validacao local sem snapshot de auditoria

## 9. Status final

- Backend principal: **OK**
- Endpoint `/api/v1/fuel/executive`: **OK (HTTP 200)**
- Aba `Operacional > Combustiveis`: **OK e visivel**
- Validacao visual e funcional (cards, graficos, filtros, autosoma, export): **OK**
- Cobertura parcial explicitamente exibida (5555 e 11495): **OK**
