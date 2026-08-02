# Sprint 47 — Motor de Mapeamento de Despesas, Variação Térmica e Automação

## Objetivo

Resolver a volatilidade no cadastro de despesas oriundas da API do WebPosto, aplicar física de variação térmica nas perdas de combustível e implementar recomendações automatizadas de compra.

## Entregas

### 1. Fator de Correção Térmica (FuelLossService)

- Coeficientes de expansão por tipo de combustível:
  - Gasolina: 0.00120
  - Etanol: 0.00110
  - Diesel: 0.00095
- Cálculo de variação térmica esperada vs perda real
- Conversão para volume a 20ºC (padrão ANP)
- Novas classificações de alerta:
  - `PERDA_TERMICA`: variação explicada pela física
  - `DESVIO_SUSPEITO`: excede tolerância térmica
  - `VAZAMENTO`: perda crítica (> 3%)

### 2. Engine de Mapeamento de Despesas (ExpenseCategorizationService)

- Modelo `ExpenseMappingRule` com campos:
  - `webposto_pattern`: padrão de matching (ex: "ENERGIA%", "COMB%GERADOR")
  - `target_classification`: enum ExpenseClassification
  - `confidence_level`: EXACT, PATTERN, FUZZY, MANUAL
  - `priority`: ordenação de regras
  - `is_active`: ativação/desativação

- Funcionalidades:
  - Normalização de texto (remove acentos, caracteres especiais)
  - Matching por padrão com wildcards (%)
  - Fallback automático para `PENDENTE_CLASSIFICACAO`
  - Aprendizado via reclassificação manual

- Regras padrão inicializadas:
  - 30+ mapeamentos para categorias comuns (energia, pessoal, tributária, etc.)

### 3. Endpoints de Gerenciamento

Base: `/api/v1/financial/expense-mappings`

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/` | Lista regras ativas |
| GET | `/{rule_id}` | Obtém regra específica |
| POST | `/` | Cria nova regra |
| PUT | `/{rule_id}` | Atualiza regra |
| DELETE | `/{rule_id}` | Remove regra |
| POST | `/categorize` | Categoriza lote de despesas |
| POST | `/reclassify-pending` | Reprocessa pendentes |
| POST | `/learn` | Cria regra a partir de reclassificação |
| GET | `/stats/coverage` | Estatísticas de cobertura |

### 4. Serviço de Recomendação de Compras (PurchaseRecommendationService)

- Cálculo de ponto de pedido: `(venda_media × lead_time) + estoque_segurança`
- Níveis de urgência:
  - `IMEDIATO`: ruptura ou cobertura crítica em Curva A
  - `URGENTE`: cobertura abaixo do lead time
  - `NORMAL`: próximo do ponto de pedido
  - `PREVENTIVO`: reposição preventiva

- Score de prioridade baseado em:
  - Classificação ABC (A=100, B=60, C=30)
  - Urgência (IMEDIATO=100, URGENTE=75)
  - Margem unitária (bônus até 20%)
  - Cobertura crítica (penalidade)

### 5. Tech Debt Resolvido

- `cliente_dto.py`: migração de `@validator` → `@field_validator`
- `cliente_dto.py`: migração de `class Config` → `model_config = ConfigDict`

## Arquivos Criados/Modificados

### Novos arquivos

- `src/services/expense_categorization_service.py`
- `src/services/purchase_recommendation_service.py`
- `src/interfaces/http/routes/expense_mappings.py`
- `tests/unit/test_expense_categorization.py`
- `tests/unit/test_purchase_recommendation.py`

### Arquivos modificados

- `src/services/fuel_loss_service.py` (correção térmica)
- `src/interfaces/http/app.py` (novo router)
- `src/application/dto/cliente_dto.py` (Pydantic V2)
- `tests/unit/test_fuel_loss.py` (novos testes térmicos)

## Testes Unitários

36 testes passando:
- 13 testes de FuelLossService (incluindo térmicos)
- 12 testes de ExpenseCategorizationService
- 11 testes de PurchaseRecommendationService

## Validação

```powershell
python -m pytest tests/unit/test_fuel_loss.py tests/unit/test_expense_categorization.py tests/unit/test_purchase_recommendation.py -o addopts= --tb=short -v
```

## Próximos Passos (Sprint 48)

- Dashboard visual de perdas volumétricas
- Integração real-time de medição de tanques
- Alertas automatizados via webhook
- Exportação de relatórios DRE
