# Pytest Coverage Conflict — IA-1

**Data:** 2026-06-14  
**Modo:** READ ONLY (nenhum arquivo de config alterado)

---

## Fontes analisadas

| Arquivo | `addopts` relevantes |
|---------|----------------------|
| `pytest.ini` | `--strict-markers --tb=short --cov=src --cov-report=html --cov-report=term-missing` |
| `pyproject.toml` `[tool.pytest.ini_options]` | `--strict-markers --tb=short` (sem coverage) |
| `setup.cfg` | **Ausente** |

---

## Quem injeta o quê?

| Flag | Origem |
|------|--------|
| `--cov=src` | **`pytest.ini`** (linhas 14–16) |
| `--cov-report=html` | **`pytest.ini`** |
| `--cov-report=term-missing` | **`pytest.ini`** |
| `--no-cov` | **`scripts/audit_f08_4_financial_intelligence_center.py`** (subprocess, linha ~87) |
| `--no-cov` | **`scripts/audit_f08_3_financial_operations_center.py`** (idem) |

**Nota:** ao existir `pytest.ini`, o pytest emite:

```text
WARNING: ignoring pytest config in pyproject.toml!
```

Ou seja, **`pyproject.toml` não governa addopts** neste repo — apenas `pytest.ini`.

---

## Plugin envolvido

- **`pytest-cov`** (`pyproject.toml` → `[tool.poetry.group.dev.dependencies]` → `pytest-cov = "^4.1.0"`)
- Instalado no ambiente atual como **pytest-cov 7.1.0** (via coverage 7.13.5)
- Fornece `--cov`, `--cov-report` e **`--no-cov`** (override)

**Nenhum plugin faltando** no ambiente auditado.

---

## Reprodução (runtime atual)

| Comando | Resultado |
|---------|-----------|
| `pytest tests/unit/test_financial_intelligence_center.py -q` | **9 passed** + coverage HTML (~38s com cov) |
| `pytest … -q --no-cov` | **9 passed** (0.77s, sem coverage) |
| `pytest … test_financial_intelligence_center + test_financial_operations_center -q` | **17 passed** + coverage |
| `pytest … --no-cov` (audit-style) | **17 passed** |

**Conclusão:** no pytest **9.0.3** + pytest-cov **7.x**, `--no-cov` **sobrescreve** `--cov=src` sem erro. O conflito reportado é **de configuração/documentação**, não falha de código F08.4.

Possível falha em versões antigas de pytest-cov ou quando `--no-cov` não existia — aí `--cov` + `--no-cov` geraria `argparse` conflict.

---

## Causa raiz

1. **Duplicidade de config:** `pytest.ini` (com cov) vs `pyproject.toml` (sem cov) — só o primeiro vale.
2. **Audits passam `--no-cov`** enquanto `pytest.ini` força `--cov=src` — redundante; em versões atuais funciona; em outras pode falhar.
3. **Não é bug F08.4** — é política de teste do repositório.

---

## Correção mínima recomendada (fora deste audit READ ONLY)

Escolher **uma** opção:

| Opção | Ação | Impacto |
|-------|------|---------|
| **A (recomendada)** | Remover `--no-cov` dos scripts `audit_f08_3` e `audit_f08_4` | Audits usam mesma config que dev; pytest passa com coverage |
| **B** | Remover `--cov*` de `pytest.ini`; coverage só via CI (`pytest --cov=src`) | Dev mais rápido; CI explícito |
| **C** | Unificar em `pyproject.toml` e **deletar** `pytest.ini` | Elimina warning; single source of truth |
| **D** | Manter ambos; audits usam `pytest -o addopts="" --no-cov …` | Override explícito sem editar ini |

**Nenhuma alteração em código F08.4 necessária.**
