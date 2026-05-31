Relatórios exportados pelo script `scripts/export_reports.py`.

Como usar:

```bash
# Exportar resumo de vendas em JSON
python scripts/export_reports.py --report resumo_vendas --start 2026-04-01 --end 2026-04-30 --format json --out ./scripts/reports

# Exportar relatório de venda combustível e converter para CSV
python scripts/export_reports.py --report venda_combustivel --start 2026-04-01 --end 2026-04-30 --format csv --out ./scripts/reports

# Exportar títulos a pagar por vencimento
python scripts/export_reports.py --report titulo_pagar --start 2026-04-01 --end 2026-04-30 --format json --out ./scripts/reports

# Buscar um título específico (por ID)
python scripts/export_reports.py --report titulo --id TIT_ABC123XYZ --format json --out ./scripts/reports

# Exportar despesas no caixa (padrão: ontem a ontem)
python scripts/export_reports.py --report despesas_caixa --format csv --out ./scripts/reports

# Filtrar por centro de custo, filial ou plano de contas
python scripts/export_reports.py --report despesas_caixa --format csv --out ./scripts/reports --centro CC123 --filial POSTO_VIP --plano P_CONTA_01
```

Onde obter o token:
- Defina a variável de ambiente `WEBPOSTO_BEARER_TOKEN` antes de rodar, ou cole quando solicitado.

Observações:
- O script usa `requests` com retry/backoff para tratar rate-limits e erros temporários.
- Se a resposta não for JSON, será salva como `.txt`.
- Para ajustar endpoints, edite o dicionário `report_map` dentro de `scripts/export_reports.py`.
