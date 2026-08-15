# Motor de cadastro de produtos WebPosto

Fachada permanente do cadastro comprovado na empresa 118508. Um POST no endpoint legado é irreversível: não há PUT, PATCH, DELETE nem rollback.

## Arquitetura

```
ProductRegistrationRequest
        │
        ▼
ProductRegistrationService
   ├─ ProductPreflightService
   ├─ políticas versionadas
   ├─ RegistrationBodyBuilder
   ├─ WebPostoRegistrationGateway   (só com --execute)
   ├─ ProductPostVerifier           (GET independente)
   ├─ RegistrationCheckpointStore
   └─ RegistrationLockStore
```

O orquestrador antigo das FASES 3-10 permanece em `service.py` (`LegacyProductRegistrationService`). Scripts das ondas 1-5 continuam válidos.

## Componentes

- **Roteamento:** empresa exata, sem fallback, `CHAVE_ONLY`.
- **GTIN:** valida; nunca corrige.
- **Duplicidade:** EAN + descrição; variante legítima não é o mesmo produto.
- **Custo:** NF-e autorizada, EAN exato, mais recente.
- **Fiscal:** evidência de entrada; vazio ≠ zero; prefixo de NCM não elege CST.

## Fluxo

1. `preflight` valida e monta `body_hash`.
2. Escrita só com `--execute` e autorizações explícitas.
3. GET independente confirma empresa, ativo, EAN, NCM, CEST, preço e custo.
4. Checkpoint atômico por EAN. Lock só quando há POST.

## Comandos seguros

```bash
python scripts/product_registration.py --empresa 118508 audit-checkpoint
python scripts/product_registration.py --empresa 118508 status --batch-id wave_05
python scripts/product_registration.py --empresa 118508 --ean ... --descricao ... --ncm ... --preco-venda 1 --accept-fiscal-risk preflight
```

Não use `--execute` sem autorização operacional nova. Esta consolidação não executa escrita.
