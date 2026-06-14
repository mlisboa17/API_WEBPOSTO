# IA-3 — Auth & Token Policy

## Tokens suportados (ordem de resolução)

1. Parâmetro explícito `api_key`
2. `WEBPOSTO_API_KEY`
3. `WEBPOSTO_API_KEY_POSTO_VIP_RIO_DOCE`
4. `WEBPOSTO_API_KEY_POSTO_CASA_CAIADA`

## Política documentada

```text
Token NÃO isola filial automaticamente.
empresaCodigo é obrigatório para segregação lógica.
token ≠ filial
```

## Fingerprint

```python
sha256(api_key).hexdigest()[:12]
```

- Logado como `tokenFingerprint`
- **Nunca** logar token completo ou CHAVE em JSON de observabilidade

## Base URL

- `WEBPOSTO_BASE_URL` (.env) ou parâmetro explícito
- Default: `https://web.qualityautomacao.com.br`
