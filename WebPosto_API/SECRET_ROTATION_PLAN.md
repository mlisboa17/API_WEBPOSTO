# SECRET ROTATION PLAN — Security P0

**Data:** 2026-06-08

> As chaves que estiveram no Git devem ser **consideradas comprometidas**, mesmo após purga do histórico.

---

## 1. Chaves a rotacionar

| Chave | Onde estava | Prioridade |
|-------|-------------|------------|
| `WEBPOSTO_API_KEY` (VIP Rio Doce) | `.env`, histórico Git | **P0** |
| `WEBPOSTO_API_KEY_POSTO_VIP_RIO_DOCE` | `WebPosto_API/.env` | **P0** |
| `WEBPOSTO_API_KEY_POSTO_CASA_CAIADA` | `WebPosto_API/.env` | **P0** |
| `WEBPOSTO_BEARER_TOKEN` | `.env` raiz | **P0** |
| `CONSUMER_TOKEN` / `ADMIN_TOKEN` | `WebPosto_API/.env` | P1 |
| `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY` | `.env` raiz | **P0** |
| `AES_KEY` | `.env` raiz | **P0** |
| `SECRET_KEY` | `.env` raiz | **P0** |
| `DB_PASSWORD` / `REDIS_PASSWORD` | `.env` raiz | P1 (se prod) |

---

## 2. Onde rotacionar

| Sistema | Ação | Contato |
|---------|------|---------|
| **Quality Automação / WebPosto** | Solicitar novas chaves REST por filial | Painel Quality / suporte integração |
| **Gateway LOGOS** | Regenerar CONSUMER_TOKEN, ADMIN_TOKEN | `.env` local |
| **JWT/AES/SECRET** | `openssl genrsa`, `secrets.token_urlsafe` | `.env` local |
| **PostgreSQL / Redis** | Alterar senhas se expostas em prod | DBA / infra |

---

## 3. Ordem recomendada

1. Rotacionar chaves WebPosto na Quality (**bloqueia integração até atualizar `.env`**)
2. Atualizar `.env` local com novas chaves (nunca commitar)
3. Testar `python -m src.main` + snapshot HIT
4. Regenerar JWT/AES/SECRET locais
5. Validar scripts de auditoria com novas chaves
6. Re-executar `SECURITY_REAUDIT_REPORT.md`
7. Autorizar push para LogosPostos

---

## 4. Impacto esperado

| Fase | Impacto |
|------|---------|
| Rotação WebPosto | Integração offline 15–60 min por filial |
| JWT local | Sessões/tokens dev invalidados |
| DB/Redis prod | Requer restart serviços se aplicável |
| Pós-rotação | Nenhum segredo antigo funcional |

---

## 5. Checklist pós-rotação

- [ ] Novas chaves WebPosto ativas na Quality
- [ ] `.env` local atualizado (não commitado)
- [ ] `git grep` sem UUID de API
- [ ] API 8040 responde snapshot
- [ ] Unit tests F01 PASS
- [ ] Equipe notificada que chaves antigas foram revogadas
- [ ] Push autorizado pelo CTO

**Nota:** Rotação **não** é automática — executar administrativamente na Quality/WebPosto.
