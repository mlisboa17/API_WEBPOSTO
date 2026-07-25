# Sprint 46 — Operacional Avançado: Perdas, Curva ABC e Ruptura

## Objetivo

Implementar módulos operacionais avançados para gestão de perdas volumétricas de combustíveis,
análise de Curva ABC de conveniência, detecção de rupturas de estoque e identificação de
capital parado.

---

## 1. Módulo de Perdas Volumétricas de Combustíveis

### Serviço: `FuelLossService`

Concilia medições de tanque para identificar perdas e sobras volumétricas.

**Fórmula de conciliação:**
```
Estoque Esperado = Estoque Inicial + Entradas NF - Saídas Vendas
Variação = Estoque Medido - Estoque Esperado
Variação % = |Variação| / max(Saídas, Estoque Inicial) * 100
```

**Classificação:**

| Variação % | Classificação | Alert Level |
|------------|---------------|-------------|
| ≤ 0.6% | NORMAL | OK |
| 0.6% - 1.5% (perda) | ATENCAO | WARNING |
| 0.6% - 1.5% (sobra) | SOBRA_SUSPEITA | WARNING |
| > 1.5% | CRITICO | CRITICAL |

### Exemplo de uso

```python
from src.services.fuel_loss_service import FuelLossService

service = FuelLossService(tolerance_pct=0.6)
result = service.reconcile_tank(
    tanque_codigo=1,
    empresa_codigo=11495,
    estoque_inicial=10000.0,
    entradas_nf=5000.0,
    saidas_vendas=8000.0,
    estoque_medido=6990.0,
    preco_medio=5.89,
)
# result.variacao_litros = -10.0, classificacao = NORMAL
```

### Cálculo de variação térmica

```python
result = service.calculate_thermal_variance(
    volume_litros=10000.0,
    temp_inicial=20.0,
    temp_final=35.0,
)
# Corrige volume por expansão térmica
```

---

## 2. Módulo de Analytics de Conveniência

### Serviço: `ConvenienceAnalyticsService`

#### 2.1 Curva ABC

Classifica produtos por faturamento acumulado:

| Faixa Acumulada | Classificação |
|-----------------|---------------|
| 0% - 80% | A (alto giro) |
| 80% - 95% | B (médio giro) |
| 95% - 100% | C (baixo giro) |

#### 2.2 Detecção de Ruptura

```
Dias de Cobertura = Estoque Atual / Venda Média Diária
```

| Condição | Status |
|----------|--------|
| Estoque = 0 | RUPTURA |
| Dias Cobertura < Lead Time * 0.5 | CRITICO |
| Dias Cobertura < Lead Time | BAIXO |
| Dias Cobertura ≥ Lead Time | NORMAL |

#### 2.3 Estoque Parado (Capital de Giro)

| Dias sem Venda | Prioridade | Ação |
|----------------|------------|------|
| 30-59 dias | MEDIA | Promoção |
| ≥ 60 dias | ALTA | Devolução/Queima |

---

## 3. Endpoints da API

### Perdas de Combustíveis

```
GET /api/v1/operational/fuel-losses
  ?dataInicial=2026-07-01
  &dataFinal=2026-07-25
  &empresaCodigo=11495
  &toleranciaPct=0.6

GET /api/v1/operational/fuel-losses/tank/{tanqueCodigo}
  ?dataInicial=...
  &dataFinal=...
  &empresaCodigo=...
```

### Conveniência

```
GET /api/v1/operational/convenience/abc-curve
  ?dataInicial=2026-07-01
  &dataFinal=2026-07-25
  &empresaCodigo=11495
  &limiteA=80.0
  &limiteB=95.0

GET /api/v1/operational/convenience/stock-break
  ?dataInicial=...
  &dataFinal=...
  &empresaCodigo=...
  &apenasUrgentes=true

GET /api/v1/operational/convenience/idle-stock
  ?data=2026-07-25
  &empresaCodigo=11495
  &diasMinimo=30

GET /api/v1/operational/summary
  ?dataInicial=...
  &dataFinal=...
  &empresaCodigo=...
```

---

## 4. Arquivos Criados

| Arquivo | Propósito |
|---------|-----------|
| `src/services/fuel_loss_service.py` | Conciliação volumétrica |
| `src/services/convenience_analytics_service.py` | Curva ABC, ruptura, capital parado |
| `src/interfaces/http/routes/operational_advanced.py` | Endpoints S46 |
| `tests/unit/test_fuel_loss.py` | 9 testes |
| `tests/unit/test_convenience_analytics.py` | 10 testes |

## 5. Arquivos Alterados

| Arquivo | Mudança |
|---------|---------|
| `src/interfaces/http/app.py` | Router `operational_advanced` adicionado |

---

## 6. Validação

```powershell
python -m pytest tests/unit/test_fuel_loss.py tests/unit/test_convenience_analytics.py -v
```

**Resultado:** 19/19 passed

---

## 7. Próximos Passos

1. Integrar dados reais de medição de tanque do WebPosto
2. Automatizar alertas de ruptura para Curva A
3. Implementar recomendações de compra baseadas em dias de cobertura
4. Dashboard visual para monitoramento de perdas
