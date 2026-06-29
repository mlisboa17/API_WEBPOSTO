# API Manual Index
## Índice Mestre de Documentação - LOGOS SPACE

**Versão:** 1.0  
**Data:** 2026-06-28  
**Status:** Ativo  
**Sprint:** DOCS-02  

---

## 📋 Índice de Documentos

| # | Documento | Descrição | Status | Versão | Sprint | Última Atualização | Dependências |
|---|-----------|-----------|--------|--------|--------|-------------------|--------------|
| 00 | [LOGOS_CONTEXT_PACK.md](./00_LOGOS_CONTEXT_PACK.md) | Fonte única da verdade | ✅ Ativo | 1.0 | DOCS-01 | 2026-06-28 | Nenhuma |
| 01 | [API_MANUAL_INDEX.md](./01_API_MANUAL_INDEX.md) | Este documento - índice mestre | ✅ Ativo | 1.0 | DOCS-02 | 2026-06-28 | 00 |
| 02 | [WEBPOSTO_MAPPING.md](./02_WEBPOSTO_MAPPING.md) | Mapeamento de filiais | ✅ Ativo | 1.0 | DOCS-02 | 2026-06-28 | 00 |
| 03 | [API_CATALOG.md](./03_API_CATALOG.md) | Catálogo de endpoints | ✅ Ativo | 1.0 | DOCS-02 | 2026-06-28 | 00, 02 |
| 04 | [ARCHITECTURE.md](./04_ARCHITECTURE.md) | Arquitetura do sistema | ✅ Ativo | 1.0 | DOCS-02 | 2026-06-28 | 00, 03 |
| 05 | [ROADMAP.md](./05_ROADMAP.md) | Roadmap oficial | ✅ Ativo | 1.0 | DOCS-02 | 2026-06-28 | 04 |
| 06 | [SPRINT_HISTORY.md](./06_SPRINT_HISTORY.md) | Histórico de sprints | ✅ Ativo | 1.0 | DOCS-02 | 2026-06-28 | 05 |
| 07 | [RELEASE_NOTES.md](./07_RELEASE_NOTES.md) | Changelog oficial | ✅ Ativo | 1.0 | DOCS-02 | 2026-06-28 | 06 |
| 08 | [DESIGN_SYSTEM.md](./08_DESIGN_SYSTEM.md) | Sistema de design | ✅ Ativo | 1.0 | DOCS-02 | 2026-06-28 | 00 |
| 09 | [BUSINESS_RULES.md](./09_BUSINESS_RULES.md) | Regras de negócio | ✅ Ativo | 1.0 | DOCS-02 | 2026-06-28 | 04 |
| 10 | [DATABASE_MAPPING.md](./10_DATABASE_MAPPING.md) | Mapeamento de banco | ✅ Ativo | 1.0 | DOCS-02 | 2026-06-28 | 04 |
| 11 | [CURRENT_STATE.md](./11_CURRENT_STATE.md) | Estado atual do sistema | ✅ Ativo | 1.0 | DOCS-02 | 2026-06-28 | Todos |
| 12 | [BUSINESS_VISION.md](./12_BUSINESS_VISION.md) | Visão de negócio | ✅ Ativo | 1.0 | DOCS-02 | 2026-06-28 | 00 |

---

## 🗂️ Documentos Legados (Referência)

### Arquitetura e Decisões
| Documento | Propósito | Status |
|-----------|-----------|--------|
| `LOGOS_ARCHITECTURE_REAL_CONSOLIDATED.md` | Arquitetura consolidada | 📁 Arquivo |
| `LOGOS_RUNBOOK_OFFICIAL_APP.md` | Guia operacional | 📁 Arquivo |
| `LOGOS_CIRCUIT_BREAKER_AUDIT.md` | Auditoria Circuit Breaker | 📁 Arquivo |
| `LOGOS_WEBPOSTO_DATE_PARAMS_FIX.md` | Correção de datas | 📁 Arquivo |

### Governance (Sprint 25A)
| Documento | Propósito | Status |
|-----------|-----------|--------|
| `LOGOS_GOVERNANCE_ARCHITECTURE.md` | Arquitetura de governança | 📁 Arquivo |
| `LOGOS_MIGRATION_REVIEW_010.md` | Review de migration | 📁 Arquivo |
| `LOGOS_DATABASE_RISK_ASSESSMENT.md` | Avaliação de riscos | 📁 Arquivo |

### Reports e Análises
| Prefixo | Quantidade | Descrição |
|---------|------------|-----------|
| `RT*` | 40+ | Runtime Test Reports |
| `F*` | 10+ | Financial Reports |
| `UX*` | 8+ | UX Validation Reports |
| `*_REPORT.md` | 100+ | Relatórios diversos |

---

## 🔄 Processo de Atualização

### Toda Sprint Deve Atualizar:

1. **05_ROADMAP.md** - Atualizar progresso e próximos passos
2. **06_SPRINT_HISTORY.md** - Registrar nova sprint
3. **07_RELEASE_NOTES.md** - Adicionar changelog
4. **11_CURRENT_STATE.md** - Atualizar estado atual
5. **01_API_MANUAL_INDEX.md** - Atualizar versões se necessário

### Checklist Pós-Sprint:

- [ ] Roadmap atualizado
- [ ] Sprint registrada no histórico
- [ ] Release notes atualizadas
- [ ] Current State refletindo realidade
- [ ] Novos endpoints documentados no API Catalog
- [ ] Novas regras de negócio no Business Rules
- [ ] Migrations registradas no Database Mapping

---

## 📖 Como Usar Esta Documentação

### Para Novos Desenvolvedores:

1. **Comece por:** `00_LOGOS_CONTEXT_PACK.md`
2. **Entenda o sistema:** `04_ARCHITECTURE.md`
3. **Conheça as regras:** `09_BUSINESS_RULES.md`
4. **Veja o estado atual:** `11_CURRENT_STATE.md`
5. **Entenda a visão:** `12_BUSINESS_VISION.md`

### Para Desenvolvimento:

1. **APIs:** `03_API_CATALOG.md`
2. **Mapeamento:** `02_WEBPOSTO_MAPPING.md`
3. **Banco:** `10_DATABASE_MAPPING.md`
4. **Design:** `08_DESIGN_SYSTEM.md`

### Para Gestão:

1. **Roadmap:** `05_ROADMAP.md`
2. **Histórico:** `06_SPRINT_HISTORY.md`
3. **Releases:** `07_RELEASE_NOTES.md`
4. **Visão:** `12_BUSINESS_VISION.md`

---

## 🔍 Convenções

### Versionamento

- **MAJOR** - Mudanças arquiteturais significativas
- **MINOR** - Novas funcionalidades/documentos
- **PATCH** - Correções e atualizações menores

### Status

- ✅ **Ativo** - Documento em uso e atualizado
- ⚠️ **Deprecated** - Sendo substituído
- 📝 **Draft** - Em elaboração
- 📁 **Arquivo** - Legado, apenas referência

### Formato de Datas

Todas as datas usam formato: `YYYY-MM-DD`

---

## 📊 Métricas da Documentação

| Métrica | Valor |
|---------|-------|
| Documentos Oficiais | 12 |
| Documentos Legados | 100+ |
| Total de Páginas | ~500+ |
| Última Atualização | 2026-06-28 |
| Readiness Score | 95% |

---

**[API MANUAL INDEX — APROVADO]**

*Atualizar ao final de cada sprint*
