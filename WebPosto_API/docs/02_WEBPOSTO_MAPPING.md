# WebPosto Mapping
## Mapeamento Oficial de Filiais - LOGOS SPACE

**Versão:** 1.0  
**Data:** 2026-06-28  
**Status:** Ativo  
**Fonte:** API WebPosto `/INTEGRACAO/EMPRESAS`

---

## 🎯 Regra de Ouro

> **NUNCA exibir `empresaCodigo` cru para o usuário final.**

Sempre resolver via este mapeamento antes de apresentar dados.

---

## 📋 Mapeamento Completo

| empresaCodigo | codWeb | Nome Fantasia | CNPJ | Base Local | Tipo |
|--------------|--------|---------------|------|------------|------|
| 5256 | 1 | POSTO BR SHOPPING | 07.018.760/0001-75 | 1 | Filial |
| 5333 | 2 | POSTO JANGA | 05.428.059/0002-80 | 2 | Filial |
| 5556 | 3 | POSTO CIDADE PATRIMONIO | 05.428.059/0001-07 | 3 | Filial |
| **5555** | **4** | **AP CASA CAIADA** | **04.284.939/0001-86** | **4** | **Matriz** |
| 5557 | 5 | POSTO ENSEADA DO NORTE | 00.338.804/0001-03 | 5 | Filial |
| 5560 | 6 | POSTO SERTÃ | 04.274.378/0001-34 | 6 | Filial |
| 7 | 7 | POSTO REAL | 24.156.978/0001-05 | 7 | Filial |
| 5559 | 8 | POSTO RJ | 08.726.064/0001-86 | 8 | Filial |
| 9 | 9 | AUTO POSTO GLOBO | 41.043.647/0001-88 | 9 | Filial |
| **11495** | **10** | **POSTO VIP** | **03.008.754/0001-86** | **10** | **Matriz** |
| 46433 | 11 | POSTO DOZE | 52.308.604/0001-01 | 11 | Filial |
| 74014 | 12 | POSTO DOZE FILIAL II | 52.308.604/0002-84 | 12 | Filial |

---

## 🔍 Notas sobre codWeb

A numeração de `codWeb` que varia de pequenos dígitos (ex: `7`, `9`) até ordens maiores é reflexo das limitações parciais de token antes da liberação do cadastro em rede.

---

## 💻 Uso no Código

### Backend (Python)

```python
# Sempre usar empresaCodigo em chamadas API
params = {
    "empresaCodigo": 11495,  # POSTO VIP
    "dataInicial": "2026-06-01",
    "dataFinal": "2026-06-28"
}

# Resolver nome para logs/mensagens
FILIAL_MAP = {
    5256: "POSTO BR SHOPPING",
    5333: "POSTO JANGA",
    5556: "POSTO CIDADE PATRIMONIO",
    5555: "AP CASA CAIADA",
    5557: "POSTO ENSEADA DO NORTE",
    5560: "POSTO SERTÃ",
    7: "POSTO REAL",
    5559: "POSTO RJ",
    9: "AUTO POSTO GLOBO",
    11495: "POSTO VIP",
    46433: "POSTO DOZE",
    74014: "POSTO DOZE FILIAL II",
}

nome_filial = FILIAL_MAP.get(11495, "Desconhecida")
```

### Frontend (JavaScript)

```javascript
// Mapeamento para exibição
const FILIAL_MAP = {
    5256: { nome: "POSTO BR SHOPPING", tipo: "Filial" },
    5333: { nome: "POSTO JANGA", tipo: "Filial" },
    5556: { nome: "POSTO CIDADE PATRIMONIO", tipo: "Filial" },
    5555: { nome: "AP CASA CAIADA", tipo: "Matriz" },
    5557: { nome: "POSTO ENSEADA DO NORTE", tipo: "Filial" },
    5560: { nome: "POSTO SERTÃ", tipo: "Filial" },
    7: { nome: "POSTO REAL", tipo: "Filial" },
    5559: { nome: "POSTO RJ", tipo: "Filial" },
    9: { nome: "AUTO POSTO GLOBO", tipo: "Filial" },
    11495: { nome: "POSTO VIP", tipo: "Matriz" },
    46433: { nome: "POSTO DOZE", tipo: "Filial" },
    74014: { nome: "POSTO DOZE FILIAL II", tipo: "Filial" },
};

// Exibir nome completo
function getFilialName(codigo) {
    return FILIAL_MAP[codigo]?.nome || `Filial ${codigo}`;
}

// SEMPRE mostrar nome, NUNCA apenas código
console.log(getFilialName(11495)); // "POSTO VIP"
```

---

## ✅ Validação

### Antes de adicionar nova filial:

- [ ] Verificar no endpoint `/INTEGRACAO/EMPRESAS`
- [ ] Confirmar CNPJ
- [ ] Definir Base Local
- [ ] Classificar como Matriz/Filial
- [ ] Atualizar este documento
- [ ] Atualizar `resolveFilialFromRow` no frontend
- [ ] Atualizar `mergeFiliais` se necessário

### Checklist de Tipagem:

- [ ] JSDoc atualizado em `frontend/types`
- [ ] OpenAPI schema atualizado
- [ ] Type hints Python atualizados
- [ ] Testes de integração atualizados

---

## 🔄 Atualização

**Quando:** Nova filial cadastrada no WebPosto

**Processo:**
1. Consultar endpoint oficial
2. Adicionar neste documento
3. Atualizar código frontend
4. Atualizar código backend
5. Executar testes de filiais
6. Atualizar `01_API_MANUAL_INDEX.md`

---

**[WEBPOSTO MAPPING — APROVADO]**

*Nunca permitir hardcodes - usar sempre este mapeamento*
