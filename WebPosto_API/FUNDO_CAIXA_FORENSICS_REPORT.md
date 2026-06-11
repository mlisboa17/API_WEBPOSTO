# FUNDO CAIXA FORENSICS — D02 · Agente 5

## Respostas

| # | Pergunta | Resposta |
|---|---|---|
| 1 | Existe campo fundoCaixa? | **Não** |
| 2 | Existe suprimento inicial? | **Não** |
| 3 | Existe saldo inicial? | **Não** |
| 4 | O fundo pode ser reconstruído? | **Sim** |

## CAIXA.abertura

Cobertura: **100.0%** · amostras:

```json
[
  {
    "empresaCodigo": 5555,
    "caixaCodigo": 4336819,
    "turnoCodigo": 1,
    "pdvCodigo": 15880,
    "funcionarioCodigo": 158924,
    "abertura": "2026-06-02T00:01:33.000-03:00"
  },
  {
    "empresaCodigo": 5555,
    "caixaCodigo": 4337788,
    "turnoCodigo": 1,
    "pdvCodigo": 15880,
    "funcionarioCodigo": 158924,
    "abertura": "2026-06-03T00:01:02.000-03:00"
  },
  {
    "empresaCodigo": 5555,
    "caixaCodigo": 4338775,
    "turnoCodigo": 1,
    "pdvCodigo": 15880,
    "funcionarioCodigo": 158924,
    "abertura": "2026-06-04T00:13:26.000-03:00"
  },
  {
    "empresaCodigo": 5555,
    "caixaCodigo": 4339720,
    "turnoCodigo": 1,
    "pdvCodigo": 15880,
    "funcionarioCodigo": 158924,
    "abertura": "2026-06-05T00:00:09.000-03:00"
  },
  {
    "empresaCodigo": 5555,
    "caixaCodigo": 4340665,
    "turnoCodigo": 1,
    "pdvCodigo": 15880,
    "funcionarioCodigo": 299151,
    "abertura": "2026-06-06T00:00:03.000-03:00"
  },
  {
    "empresaCodigo": 5555,
    "caixaCodigo": 4343023,
    "turnoCodigo": 1,
    "pdvCodigo": 15880,
    "funcionarioCodigo": 158924,
    "abertura": "2026-06-08T07:28:12.000-03:00"
  }
]
```

Origem provável: **CAIXA.abertura (+ MOVIMENTO_CONTA inferido)**

Gap vs Prestação: **rótulo fundoCaixa ≠ abertura numérica sem regra UI**
