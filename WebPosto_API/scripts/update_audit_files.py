import json

# Carregar os resultados da auditoria
with open('webposto_endpoint_audit.json', 'r', encoding='utf-8') as f:
    audit_results = json.load(f)

# Mapeamento de endpoints para os arquivos do frontend que os utilizam
# Baseado na análise manual de api.js e outros arquivos.
frontend_usage = {
    # V1 financial endpoints
    "/v1/financial/overview": ["executiveDashboard.js", "app.js"],
    "/v1/financial/expenses": ["expenses.js", "app.js"],
    "/v1/financial/accounts-payable": ["accountsPayable.js", "app.js"],
    "/v1/sales": ["sales.js", "app.js"],
    "/v1/stock": ["stock.js", "app.js"],
    "/v1/financial/companies": ["filiais.js", "app.js"],

    # API V1 analytics endpoints
    "/api/v1/kpis": ["executiveDashboard.js", "analyticsEngine.js"],
    "/api/v1/dre": ["executiveDashboard.js", "analyticsEngine.js"],
    "/api/v1/data-quality": ["executiveDashboard.js"],
    "/api/v1/network/coverage": ["executiveDashboard.js"],
    "/api/v1/filiais": ["filiais.js", "app.js"],
    "/api/v1/sync/control": ["admin.js"], # Suposição
    "/api/v1/sync/logs": ["admin.js"], # Suposição

    # Legacy endpoints (mapeados em api.js)
    "/INTEGRACAO/EMPRESAS": ["api.js (via fetchWebPosto)"],
    "/INTEGRACAO/CONSULTAR_DESPESAS_FINANCEIRO_REDE": ["api.js (via fetchWebPosto)"],
    "/INTEGRACAO/VENDA": ["api.js (via fetchWebPosto)"],
    "/INTEGRACAO/VENDA_ITEM": ["api.js (via fetchWebPosto)"],
    "/INTEGRACAO/VENDA_FORMA_PAGAMENTO": ["api.js (via fetchWebPosto)"],
    "/INTEGRACAO/CONTA": ["api.js (via fetchWebPosto)"],
    "/INTEGRACAO/PRODUTO_ESTOQUE": ["api.js (via fetchWebPosto)"],
    "/INTEGRACAO/PRODUTO_EMPRESA": ["api.js (via fetchWebPosto)"],
    
    # Auth
    "/auth/login": ["auth.js"], # Suposição

    # Health
    "/health": ["N/A (Infra)"],
    "/ready": ["N/A (Infra)"],

    # Outros
    "/metrics/executive": ["executiveDashboard.js"],
}

# Atualizar os resultados da auditoria com a informação de uso
for item in audit_results:
    endpoint = item['endpoint']
    if endpoint in frontend_usage:
        item['utilizadoPor'] = frontend_usage[endpoint]
    
    # O endpoint /v1/financial/accounts-receivable não foi encontrado em uso explícito
    if endpoint == "/v1/financial/accounts-receivable":
        item['categoria'] = 'EXPERIMENTAL'


# Salvar o JSON atualizado
with open('webposto_endpoint_audit.json', 'w', encoding='utf-8') as f:
    json.dump(audit_results, f, indent=2, ensure_ascii=False)

print("webposto_endpoint_audit.json atualizado com informações de uso do frontend.")

# Gerar o catálogo final em Markdown
with open("webposto_endpoint_catalog.md", "w", encoding="utf-8") as f:
    f.write("# Catálogo de Endpoints WebPosto - SPRINT 21.3\n\n")
    f.write("Este documento cataloga os endpoints auditados, sua classificação e onde são utilizados no sistema.\n\n")

    for categoria in ["PRODUCAO", "EXPERIMENTAL", "OBSOLETO"]:
        f.write(f"## {categoria}\n\n")
        f.write("| Endpoint | Status | Tempo (ms) | Utilizado Por |\n")
        f.write("|----------|--------|------------|---------------|\n")
        
        endpoints_na_categoria = [r for r in audit_results if r['categoria'] == categoria]
        
        if not endpoints_na_categoria:
            f.write("| *Nenhum endpoint nesta categoria* | | |\n")
        else:
            for r in endpoints_na_categoria:
                usage = ", ".join(r.get('utilizadoPor', [])) or "N/A"
                f.write(f"| `{r['endpoint']}` | {r['status']} | {r['tempoRespostaMs']} | {usage} |\n")
        f.write("\n")

print("Catálogo final gerado em webposto_endpoint_catalog.md")
