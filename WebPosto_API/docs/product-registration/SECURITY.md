# Segurança do motor de cadastro

## Credenciais

A empresa resolve só pelos aliases oficiais. A chave nunca vai para log, checkpoint, trilha ou CLI. Use `fingerprint` (SHA-256 truncado). Endpoint legado: `CHAVE` na query, sem `empresaCodigo`.

## Certificado e cofre

Certificados A1, senhas e XMLs de NF-e ficam fora do Git. O resolvedor de custo mascara a chave de acesso.

## Logs

Permitido: empresa, EAN, `produtoCodigo`, HTTP status, RET, `body_hash`, fingerprint. Proibido: valor da CHAVE, certificado, XML, chave de acesso completa.

## Dados fiscais

Tabelas locais e DF-e são evidência operacional. Relatórios versionados não levam segredo. Testes usam fixtures fictícios.

## Arquivos proibidos no Git

- `.env` real
- certificados e cofre
- XML de NF-e
- `data/product_registration/` de execução (checkpoints, locks, relatórios)
- qualquer arquivo com CHAVE ou chave de acesso de 44 dígitos
