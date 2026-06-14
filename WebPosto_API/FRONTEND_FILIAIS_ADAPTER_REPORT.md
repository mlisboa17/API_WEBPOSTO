# IA-4 — Frontend Adapter

- Novo: `frontend/filiais.js` (carrega manifest via `fetch`, fallback hardcoded)
- Adapter legado: `frontend/components/filiais.js` → reexport
- Contrato preservado: `FILIAIS`, `mergeFiliais`, `resolveFilialFromRow`, etc.
- Telas existentes: **sem alteração de imports**
