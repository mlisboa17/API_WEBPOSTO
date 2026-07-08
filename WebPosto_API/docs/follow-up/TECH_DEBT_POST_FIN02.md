# Follow-up — Post FIN-02 Technical Cleanup

**Status:** OPEN (não bloqueia merge FIN-02)  
**Prioridade:** Média  
**Escopo:** Cleanup técnico pós-merge — **não** expandir FIN-02  
**Merge gate:** warnings **intencionalmente deferidos**; nenhum item abaixo deve entrar no merge FIN-02

---

## Contexto

Suite FIN-01 + FIN-02: `25 passed, 18 warnings` (ver `docs/validation/FIN_02_TEST_RUN.txt`).

Warnings são **pré-existentes** ou **amplificados por import de `create_app()`** nos testes — não introduzidos pela lógica de assignment.

---

## Itens

### 1. FastAPI `on_event` deprecation (prioridade alta)

**Origem:** `src/interfaces/http/app.py` linhas 174–185

```
@app.on_event("startup")
@app.on_event("shutdown")
```

**Ação:** Migrar para `lifespan` context manager ([FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)).

**Arquivos prováveis:** `src/interfaces/http/app.py`, possivelmente `src/main.py` se duplicado.

**Critério de done:** pytest FIN suite sem `DeprecationWarning: on_event is deprecated`.

---

### 2. Pydantic v2 — Settings `class Config` (prioridade média)

**Origem:** `src/infrastructure/config/settings.py`

**Ação:** Substituir por `model_config = ConfigDict(...)`.

---

### 3. Pydantic v2 — `@validator` legacy (prioridade média)

**Origem:** `src/application/dto/cliente_dto.py` (5 warnings)

**Ação:** Migrar para `@field_validator`.

---

### 4. python-dotenv parse warning (prioridade baixa)

**Origem:** `.env` linha 89 — statement não parseável

**Ação:** Corrigir sintaxe da linha ou comentar/documentar; não versionar segredos.

---

## Comando de verificação pós-cleanup

```bash
python -m pytest tests/unit/test_financial_review_assignment.py tests/unit/test_financial_review_inbox.py -q --no-cov -W error::DeprecationWarning
```

*(Ajustar `-W` gradualmente conforme cada item for resolvido.)*

---

## Explicitamente fora deste follow-up

- Migração frontend NewWebLogos
- RBAC / autenticação real
- FIN-03 conferência operacional
- Redesign ExecutiveReviewStore
