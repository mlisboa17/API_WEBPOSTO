# Pacote de Integracao - Logos Gateway API

Este pacote foi criado para ajudar outro sistema (em outra pasta/projeto) a consumir a API do gateway com rapidez.

## Conteudo

- `.env.example`: variaveis de conexao
- `http/gateway_requests.http`: chamadas prontas para teste manual
- `python/gateway_client.py`: cliente Python reutilizavel
- `python/example.py`: exemplo de uso do cliente
- `python/requirements.txt`: dependencias Python

## Contrato de integracao

Base URL local padrao:
- `http://127.0.0.1:8050`

Headers obrigatorios em endpoints de negocio:
- `X-Consumer-Token`
- `X-Posto-ID`

Endpoints principais:
- `GET /ready`
- `GET /health`
- `GET /v1/expenses`
- `GET /v1/products`

## Como usar (Python)

1. Copie `.env.example` para `.env` no projeto consumidor.
2. Ajuste os valores conforme seu ambiente.
3. Instale dependencias e execute o exemplo:

```powershell
Set-Location .\python
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python .\example.py
```

## Como usar (HTTP manual no VS Code)

1. Abra `http/gateway_requests.http`.
2. Substitua os placeholders se necessario.
3. Execute as requests com a extensao REST Client.

## Erros esperados

- `401`: token do consumidor invalido/ausente
- `404`: posto nao configurado
- `403`: posto inativo
- `502/503`: erro temporario no upstream WebPosto

## Dica para outro sistema em outra pasta

Esse pacote pode ser copiado para qualquer repositorio. O sistema consumidor so precisa de:
- URL da API
- token de consumidor
- posto ID

Nada no cliente depende da estrutura interna do gateway.
