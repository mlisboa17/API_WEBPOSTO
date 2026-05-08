# WebPosto API Client — Grupo Lisboa

Cliente Python para integração com a API REST do **webPosto** (Quality Automação).

**Base URL:** `http://web.qualityautomacao.com.br`
**Auth:** Query param `?CHAVE=<chave_de_integração>`
**Swagger:** https://web.qualityautomacao.com.br/webjars/swagger-ui/index.html?configUrl=/v3/api-docs/swagger-config
**154 endpoints disponíveis**

---

## Pré-requisitos

### 1. Liberar contrato de API
Entre em contato com o **setor comercial da Quality Automação** para ativar o contrato de API Integração.

### 2. Gerar a Chave de Integração
No sistema webPosto:
```
Administração > Integrações > Integração > [Incluir]
Tipo: API Integração
Defina um usuário do sistema → Salvar
Copie a chave gerada
```

---

## Instalação

```bash
pip install -r requirements.txt
```

## Configuração

```bash
cp .env.example .env
# Edite .env e preencha WEBPOSTO_CHAVE=sua_chave
```

---

## Uso

```python
from webposto import WebPostoClient, WebPostoConfig
from datetime import date

# Via .env (recomendado)
client = WebPostoClient.from_env()

# Ou explícito
client = WebPostoClient(WebPostoConfig(
    chave="sua_chave_aqui",
    empresa_codigo=1,  # opcional
))
```

### Exemplos por domínio

#### Abastecimento
```python
from datetime import date

abastecimentos = client.abastecimento.listar(
    data_inicial=date(2025, 4, 1),
    data_final=date(2025, 4, 6),
)

encerrantes = client.abastecimento.listar_encerrante(
    data_inicial=date(2025, 4, 1),
    data_final=date(2025, 4, 6),
)
```

#### Financeiro
```python
# Títulos a receber em aberto
titulos = client.financeiro.listar_titulos_receber(
    data_inicial=date(2025, 1, 1),
    data_final=date(2025, 12, 31),
    situacao="ABERTO",  # AMBOS | ABERTO | RECEBIDO
)

# Fechamento de caixa
caixa = client.financeiro.listar_fechamento_caixa(
    data_inicial=date(2025, 4, 5),
    data_final=date(2025, 4, 5),
)

# Receber título
client.financeiro.receber_titulo({"tituloCodigo": 1234, "valorRecebido": 500.00})
```

#### Combustível / LMC
```python
# Livro de Movimentação de Combustíveis
lmc = client.combustivel.listar_lmc(
    data_inicial=date(2025, 4, 1),
    data_final=date(2025, 4, 6),
    filial=[1, 2],
)

# Trocar preço de combustível
client.produtos.trocar_preco_combustivel({
    "produtoCodigo": 1,
    "precoVenda": 5.89,
    "filialCodigo": 1,
})
```

#### Clientes
```python
# Listar clientes
clientes = client.clientes.listar(nome="João")

# Criar cliente
novo = client.clientes.criar({
    "nome": "João Silva",
    "cpfCnpj": "123.456.789-00",
    "email": "joao@email.com",
})
```

#### Vendas / NF
```python
vendas = client.integracoes.listar_vendas(
    data_inicial=date(2025, 4, 1),
    data_final=date(2025, 4, 6),
    filial=[1],
)

nf_entrada = client.integracoes.listar_nf_entrada(
    data_inicial=date(2025, 4, 1),
    data_final=date(2025, 4, 6),
)
```

---

## Estrutura do Projeto

```
WebPosto_API/
├── src/webposto/
│   ├── __init__.py          # exports principais
│   ├── client.py            # WebPostoClient — ponto de entrada
│   ├── config.py            # WebPostoConfig
│   ├── http.py              # HTTPClient com retry e tratamento de erros
│   ├── exceptions.py        # Exceções customizadas
│   └── endpoints/
│       ├── abastecimento.py # Abastecimentos e encerrantes
│       ├── clientes.py      # Clientes, frota, grupos
│       ├── produtos.py      # Produtos, preços, estoque
│       ├── financeiro.py    # Títulos, caixa, transferências
│       ├── combustivel.py   # Pedidos de combustível, LMC
│       ├── relatorios.py    # Relatórios gerenciais
│       └── integracoes.py   # Vendas, NF, pedidos de compra, etc.
├── scripts/
│   └── sync.py              # Script de sincronização diária
├── tests/
│   └── unit/
│       └── test_client.py   # Testes unitários
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── requirements.txt
```

---

## Docker

```bash
# Build + run
cp .env.example .env
# Edite .env com sua WEBPOSTO_CHAVE

docker compose up -d

# Apenas o sync (sem banco)
docker compose up webposto-sync
```

---

## Testes

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

---

## Tratamento de Erros

```python
from webposto.exceptions import AuthError, NotFoundError, ServerError, TimeoutError

try:
    result = client.abastecimento.listar(...)
except AuthError:
    print("Chave inválida — verifique WEBPOSTO_CHAVE e o contrato com a Quality")
except ServerError:
    print("Erro no servidor WebPosto — tente novamente")
except TimeoutError:
    print("Timeout — verifique conexão de rede")
```

---

## Endpoints Disponíveis (154 total)

### Integrações (140)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | /INTEGRACAO/ABASTECIMENTO | Listar abastecimentos |
| GET | /INTEGRACAO/ABASTECIMENTO_ENCERRANTE | Listar encerrantes |
| GET | /INTEGRACAO/ABASTECIMENTO_DIVERGENCIA | Divergências de abastecimento |
| GET | /INTEGRACAO/LMC | Livro de Movimentação de Combustíveis |
| GET | /INTEGRACAO/APRIX_CUSTO | APRIX de custo |
| GET | /INTEGRACAO/TITULO_RECEBER | Títulos a receber |
| POST | /INTEGRACAO/TITULO_RECEBER | Criar título a receber |
| PUT | /INTEGRACAO/RECEBER_TITULO | Receber título |
| GET | /INTEGRACAO/TITULO_PAGAR | Títulos a pagar |
| POST | /INTEGRACAO/TITULO_PAGAR | Criar título a pagar |
| GET | /INTEGRACAO/FECHAMENTO_CAIXA | Fechamento de caixa |
| GET | /INTEGRACAO/MOVIMENTO_CONTA | Movimentos de conta |
| GET | /INTEGRACAO/TRANSFERENCIA_BANCARIA | Transferências bancárias |
| POST | /INTEGRACAO/TRANSFERENCIA_BANCARIA | Criar transferência |
| GET | /INTEGRACAO/FINANCEIRO_EXCLUSAO | Exclusões financeiras |
| GET | /INTEGRACAO/VENDA | Listar vendas |
| GET | /INTEGRACAO/VENDA_REDE | Vendas em rede |
| GET | /INTEGRACAO/NOTA_FISCAL_ENTRADA | NF de entrada |
| GET | /INTEGRACAO/NOTA_FISCAL_SAIDA | NF de saída |
| GET | /INTEGRACAO/CLIENTE | Listar clientes |
| POST | /INTEGRACAO/CLIENTE | Criar cliente |
| PUT | /INTEGRACAO/CLIENTE/{id} | Atualizar cliente |
| GET | /INTEGRACAO/PRODUTO | Listar produtos |
| POST | /INTEGRACAO/PRODUTO | Criar produto |
| PUT | /INTEGRACAO/ALTERAR_PRODUTO/{id} | Atualizar produto |
| POST | /INTEGRACAO/TROCA_PRECO_COMBUSTIVEL | Trocar preço combustível |
| POST | /INTEGRACAO/TROCA_PRECO_PRODUTO | Trocar preço produto |
| GET | /INTEGRACAO/FILIAL | Listar filiais |
| GET | /INTEGRACAO/USUARIO | Listar usuários |
| GET | /INTEGRACAO/ADMINISTRADORA | Administradoras de cartão |
| GET | /INTEGRACAO/DISTRIBUIDORA | Distribuidoras |
| ... | ... | + 110 endpoints adicionais no Swagger |

### Integração Pedido Combustível
| Método | Endpoint |
|--------|----------|
| POST | /INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO |
| GET | /INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO |
| POST | /INTEGRACAO/PEDIDO_COMBUSTIVEL/PEDIDO/{id}/FATURAR |

---

## Links

- **Swagger UI:** https://web.qualityautomacao.com.br/webjars/swagger-ui/index.html?configUrl=/v3/api-docs/swagger-config
- **OpenAPI JSON:** https://web.qualityautomacao.com.br/v3/api-docs/integracao
- **Manual Confluence:** https://qualityautomacao.atlassian.net/wiki/spaces/webPosto/pages/923402268
