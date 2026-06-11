# OPERATOR IDENTITY TRACE — D02 · Agente 2

## Casos obrigatórios

| Código | Vendas | Turnos | Nome (FUNCIONARIO) | CPF | Empresas | PDVs | Nominalizável? |
|---|---|---|---|---|---|---|---|
| 276288 | 53 | 6 | JOÃO RYVISON DE ANDRADE SOUZA | 703.923.894-28 | [11495] | [56764] | **Sim** |
| 294273 | 0 | 4 | RICART ABEL DE PAIVA RIBEIRO | 715.050.154-05 | [11495] | [54193] | **Sim** |
| 213391 | 0 | 0 | JEFFERSON NASCIMENTO. | None | [] | [] | **Sim** |

## Resposta central

**O código pode ser transformado em identidade real?** **Sim** — via join **`/INTEGRACAO/FUNCIONARIO`** (`nome`, `cpf`, `funcionarioReferencia`, `ativo`) por `funcionarioCodigo`. Os três operadores críticos foram nominalizados na janela **7d**.

Detalhes por operador:

```json
{
  "276288": {
    "funcionarioCodigo": 276288,
    "vendasCount": 53,
    "caixaTurnosCount": 6,
    "abastecimentosCount": 0,
    "vendaItensCount": 88,
    "empresas": [
      11495
    ],
    "pdvs": [
      56764
    ],
    "turnos": [
      "1"
    ],
    "volumeVendas": 697.64,
    "cadastroFuncionario": {
      "encontrado": true,
      "nome": "JOÃO RYVISON DE ANDRADE SOUZA",
      "cpf": "703.923.894-28",
      "referencia": "00040",
      "ativo": true,
      "empresaCodigo": 11495
    },
    "nomeFieldsFound": [
      {
        "clienteCpfCnpj": "00.000.000/0000-00"
      },
      {
        "clienteCpfCnpj": "00.000.000/0000-00"
      },
      {
        "clienteCpfCnpj": "00.000.000/0000-00"
      },
      {
        "clienteCpfCnpj": "00.000.000/0000-00"
      },
      {
        "clienteCpfCnpj": "00.000.000/0000-00"
      },
      {
        "clienteCpfCnpj": "00.000.000/0000-00"
      },
      {
        "clienteCpfCnpj": "00.000.000/0000-00"
      },
      {
        "clienteCpfCnpj": "00.000.000/0000-00"
      },
      {
        "clienteCpfCnpj": "00.000.000/0000-00"
      },
      {
        "clienteCpfCnpj": "00.000.000/0000-00"
      }
    ],
    "nominalizavel": true,
    "identidadeReal": "funcionario_api"
  },
  "294273": {
    "funcionarioCodigo": 294273,
    "vendasCount": 0,
    "caixaTurnosCount": 4,
    "abastecimentosCount": 0,
    "vendaItensCount": 0,
    "empresas": [
      11495
    ],
    "pdvs": [
      54193
    ],
    "turnos": [
      "1"
    ],
    "volumeVendas": 0,
    "cadastroFuncionario": {
      "encontrado": true,
      "nome": "RICART ABEL DE PAIVA RIBEIRO",
      "cpf": "715.050.154-05",
      "referencia": "00044",
      "ativo": true,
      "empresaCodigo": 11495
    },
    "nomeFieldsFound": [
      {
        "funcionario.nome": "RICART ABEL DE PAIVA RIBEIRO"
      },
      {
        "funcionario.cpf": "715.050.154-05"
      },
      {
        "funcionario.referencia": "00044"
      }
    ],
    "nominalizavel": true,
    "identidadeReal": "funcionario_api"
  },
  "213391": {
    "funcionarioCodigo": 213391,
    "vendasCount": 0,
    "caixaTurnosCount": 0,
    "abastecimentosCount": 0,
    "vendaItensCount": 0,
    "empresas": [],
    "pdvs": [],
    "turnos": [],
    "volumeVendas": 0,
    "cadastroFuncionario": {
      "encontrado": true,
      "nome": "JEFFERSON NASCIMENTO.",
      "cpf": null,
      "referencia": "00028",
      "ativo": true,
      "empresaCodigo": 11495
    },
    "nomeFieldsFound": [
      {
        "funcionario.nome": "JEFFERSON NASCIMENTO."
      },
      {
        "funcionario.referencia": "00028"
      }
    ],
    "nominalizavel": true,
    "identidadeReal": "funcionario_api"
  }
}
```
