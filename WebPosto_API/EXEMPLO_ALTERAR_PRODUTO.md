# Exemplo: Alteração de Produto (PUT /INTEGRACAO/ALTERAR_PRODUTO)

## 📌 Resumo

A WebPosto API permite alterar produtos via `PUT /INTEGRACAO/ALTERAR_PRODUTO/{id}`.

**Importante:** Exige o payload **COMPLETO** (todos os campos), não suporta patch parcial.

## ✅ Endpoint

```
PUT https://web.qualityautomacao.com.br/INTEGRACAO/ALTERAR_PRODUTO/{id}
```

### Headers

```http
Authorization: Bearer <WEBPOSTO_API_TOKEN>
Content-Type: application/json
```

## 📋 Request Body (Exemplo Real)

```json
{
  "codigoBarras": "000004",
  "descricao": "GASOLINA COMUM.",
  "precoVenda": "7.5500",
  "precoCusto": "6.0209",
  "ativo": true,
  "estoqueAtual": "0.0000",
  "unidadeMedida": "L",
  "ncm": "27101259",
  "cest": "0600201",
  "cstIcms": null,
  "aliquotaIcms": null,
  "codigoGrupo": 24554,
  "nomeGrupo": null,
  "subGrupo1Codigo": null,
  "subGrupo2Codigo": null,
  "subGrupo3Codigo": null,
  "tipoProduto": "C",
  "tipoCombustivel": "GASOLINA",
  "combustivel": true
}
```

## 🎯 Casos de Uso

### 1. Alterar Preço de Venda

```bash
curl -X PUT https://web.qualityautomacao.com.br/INTEGRACAO/ALTERAR_PRODUTO/1257884 \
  -H "Authorization: Bearer <WEBPOSTO_API_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "codigoBarras": "000004",
    "descricao": "GASOLINA COMUM.",
    "precoVenda": "7.5500",
    "precoCusto": "6.0209",
    "ativo": true,
    "estoqueAtual": "0.0000",
    "unidadeMedida": "L",
    "ncm": "27101259",
    "cest": "0600201",
    "cstIcms": null,
    "aliquotaIcms": null,
    "codigoGrupo": 24554,
    "nomeGrupo": null,
    "subGrupo1Codigo": null,
    "subGrupo2Codigo": null,
    "subGrupo3Codigo": null,
    "tipoProduto": "C",
    "tipoCombustivel": "GASOLINA",
    "combustivel": true
  }'
```

### 2. Desativar um Produto

```bash
curl -X PUT https://web.qualityautomacao.com.br/INTEGRACAO/ALTERAR_PRODUTO/1257884 \
  -H "Authorization: Bearer <WEBPOSTO_API_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    ...MESMOS_CAMPOS_ACIMA...
    "ativo": false,
    "descricao": "GASOLINA COMUM. (DESCONTINUADO)"
  }'
```

### 3. Atualizar Classificação Fiscal (NCM/CEST)

```bash
curl -X PUT https://web.qualityautomacao.com.br/INTEGRACAO/ALTERAR_PRODUTO/1257884 \
  -H "Authorization: Bearer <WEBPOSTO_API_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    ...MESMOS_CAMPOS_ACIMA...
    "ncm": "27101100",
    "cest": "0600199",
    "cstIcms": "60",
    "aliquotaIcms": "18"
  }'
```

## 📚 Referência de Campos

| Campo | Tipo | Obrigatório | Exemplo | Notas |
|-------|------|------------|---------|-------|
| `codigoBarras` | string | ✅ | "000004" | Code de barras ou ID interno |
| `descricao` | string | ✅ | "GASOLINA COMUM." | Nome do produto |
| `precoVenda` | string/decimal | ✅ | "7.5500" | Preço de venda (pode conter decimais) |
| `precoCusto` | string/decimal | ✅ | "6.0209" | Preço de custo |
| `ativo` | boolean | ✅ | `true` | Produto ativo no sistema |
| `estoqueAtual` | string/decimal | ✅ | "0.0000" | Quantidade em estoque |
| `unidadeMedida` | string | ✅ | "L", "KG", "UN" | Unidade de medida |
| `ncm` | string | ✅ | "27101259" | Código NCM (8 dígitos) |
| `cest` | string | ✅ | "0600201" | Código CEST (7 dígitos) |
| `cstIcms` | string \| null | ❌ | "00", "60", "90" | CST ICMS (vide nota abaixo) |
| `aliquotaIcms` | string/number \| null | ❌ | "18" | Alíquota ICMS (0-100) |
| `codigoGrupo` | number | ✅ | 24554 | ID do grupo de produtos |
| `nomeGrupo` | string \| null | ❌ | null | Nome do grupo (leitura) |
| `subGrupo1Codigo` | number \| null | ❌ | null | Subgrupo nível 1 |
| `subGrupo2Codigo` | number \| null | ❌ | null | Subgrupo nível 2 |
| `subGrupo3Codigo` | number \| null | ❌ | null | Subgrupo nível 3 |
| `tipoProduto` | string | ✅ | "C" ou "P" | **C**: combustível, **P**: produto |
| `tipoCombustivel` | string | ✅ | "GASOLINA" | Tipo de combustível (se aplicável) |
| `combustivel` | boolean | ✅ | `true` | É combustível? |

### CST ICMS Válidos

```
00 - Tributação normal do ICMS
10 - Tributação com cobrança do ICMS por ST
20 - Tributação com suspensão do ICMS
30 - Imunidade do ICMS
40 - Isenção do ICMS
41 - Não incidência do ICMS
50 - Suspensão do ICMS
51 - Diferimento da tributação do ICMS
60 - ICMS cobrado anteriormente por ST ou por antecipação
70 - Com redução de base de cálculo
90 - Outras operações
```

## 🔄 Response

**Status 200 OK** — Atualização bem-sucedida:

```json
{
  "id": 1257884,
  "codigoBarras": "000004",
  "descricao": "GASOLINA COMUM.",
  "precoVenda": "7.5500",
  "precoCusto": "6.0209",
  "ativo": true,
  ...
}
```

**Status 4xx/5xx** — Erro:

```json
{
  "error": "Produto não encontrado",
  "status": 404
}
```

ou

```json
{
  "error": "Campo obrigatório ausente: precoVenda",
  "status": 400
}
```

## ⚠️ Cuidados

1. **Payload Completo**: Omitir um campo pode resultar em erro 400 ou reset do valor.
2. **Tipos de Dados**: Strings para preços/valores monetários; booleans para flags; números para IDs.
3. **NCM/CEST**: Devem ter 8 e 7 dígitos respectivamente (sem caracteres especiais).
4. **Códigos Fiscais**: O CST deve estar dentro da faixa 00-90.
5. **Impacto**: Uma alteração de preço afeta cálculos de margem em futuros abastecimentos.

## 🚀 Teste via Python

```bash
python scripts/exemplo_alterar_produto.py
```

Veja o script para exemplos prontos e como executá-los.

## 📞 Troubleshooting

| Erro | Causa | Solução |
|------|-------|---------|
| 404 Not Found | Produto ID inválido | Verificar ID do produto |
| 400 Bad Request | Campo obrigatório faltando | Enviar todos os campos |
| 401 Unauthorized | API Key inválida | Verificar `Authorization` header |
| 500 Internal Server Error | Erro no backend | Verificar logs da API / contatar Quality |

## 📖 Referências

- [Documentação WebPosto API](https://web.qualityautomacao.com.br/docs)
- [Script de Exemplo](./scripts/exemplo_alterar_produto.py)
- [Teste de Permissões](./scripts/check_produto_crud.py)
