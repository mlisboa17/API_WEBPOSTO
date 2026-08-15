# Políticas versionadas

Cada decisão grava `policy_name`, `policy_version`, `inputs`, `decision`, `confidence`, `reasons`, `evidence_refs`, `owner_risk_accepted` e `requires_review`.

## Custo (`cost_policy` 1.0.0)

Origem exclusiva: NF-e autorizada, não cancelada, destinatário correto, EAN exato, mais recente. Rateia frete, seguro, outras e desconto. Inclui IPI não recuperável e ICMS-ST cobrado. Embalagem sem fator no documento → custo 0 com `PENDING` e flag explícita. Custo DF-e acima da venda não é zerado.

## Duplicidade (`duplicate_policy` 1.0.0)

Mesma marca, família, sabor, medida, modelo e conector → SAME_PRODUCT, sem POST. Diferença comercial → variante. Medida essencial ausente no cadastro existente → UNRESOLVED, skip.

## Fiscal (`fiscal_policy` 1.0.0)

CST 00 não vira 060 por analogia de NCM. Campo vazio não é zero. Inferência exige `--accept-fiscal-risk` e revisão contábil.

## Roteamento (`routing_policy` 1.0.0)

Profile exato. Sem fallback genérico. Sem `empresaCodigo` no body ou na query.

## Execução (`execution_policy` 1.0.0)

Skip pré-POST continua. Timeout resolve por GET. Lock só com POST previsto. COMPLETED/PARTIAL travam reexecução.

## Risco assumido

Autorização é sempre explícita e por processo. Não grava flag no `.env`.
