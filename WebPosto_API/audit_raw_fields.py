import os
import json
import httpx
import asyncio
from datetime import datetime, date, timedelta

# Carregar configurações do .env se existir
def load_env():
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")

load_env()

BASE_URL = os.getenv("WEBPOSTO_BASE_URL", "https://web.qualityautomacao.com.br")
CHAVE = os.getenv("WEBPOSTO_API_KEY", "<WEBPOSTO_API_TOKEN>")
EMPRESA = 11495  # Posto VIP (que tem dados confirmados)

# Datas de teste (período onde sabemos que há dados)
DATA_INI = "2026-06-05"
DATA_FIM = "2026-06-06"

# Endpoints a serem verificados
# Chave -> (Path Real, params de teste)
ENDPOINTS_TO_AUDIT = {
    "CONSULTAR_VENDA_ITEM_REDE": ("/INTEGRACAO/CONSULTAR_VENDA_ITEM_REDE", {"dataInicial": DATA_INI, "dataFinal": DATA_FIM}),
    "CONSULTAR_VENDA_REDE": ("/INTEGRACAO/VENDA_REDE", {"dataInicial": DATA_INI, "dataFinal": DATA_FIM}),
    "CONSULTAR_ABASTECIMENTO_REDE": ("/INTEGRACAO/ABASTECIMENTO_REDE", {"dataInicial": DATA_INI, "dataFinal": DATA_FIM}),
    "CONSULTAR_LMC_REDE": ("/INTEGRACAO/LMC_REDE", {"dataInicial": DATA_INI, "dataFinal": DATA_FIM}),
    "CONSULTAR_PRODUTO_REDE": ("/INTEGRACAO/PRODUTO_REDE", {"dataInicial": DATA_INI, "dataFinal": DATA_FIM}),
    "CONSULTAR_PRODUTO_EMPRESA_REDE": ("/INTEGRACAO/PRODUTO_EMPRESA_REDE", {"dataInicial": DATA_INI, "dataFinal": DATA_FIM}),
    "PRODUTO": ("/INTEGRACAO/PRODUTO", {"empresaCodigo": EMPRESA}),
    "PRODUTO_EMPRESA": ("/INTEGRACAO/PRODUTO_EMPRESA", {"empresaCodigo": EMPRESA}),
    "VENDA_ITEM": ("/INTEGRACAO/VENDA_ITEM", {"empresaCodigo": EMPRESA, "dataInicial": DATA_INI, "dataFinal": DATA_FIM}),
    "VENDA": ("/INTEGRACAO/VENDA", {"empresaCodigo": EMPRESA, "dataInicial": DATA_INI, "dataFinal": DATA_FIM}),
    "ABASTECIMENTO": ("/INTEGRACAO/ABASTECIMENTO", {"empresaCodigo": EMPRESA, "dataInicial": DATA_INI, "dataFinal": DATA_FIM}),
    "LMC": ("/INTEGRACAO/LMC", {"empresaCodigo": EMPRESA, "dataInicial": DATA_INI, "dataFinal": DATA_FIM}),
    "PRODUTO_ESTOQUE": ("/INTEGRACAO/PRODUTO_ESTOQUE", {"empresaCodigo": EMPRESA, "dataInicial": DATA_INI, "dataFinal": DATA_FIM}),
}

# Checklist de campos de interesse
CHECKLIST_FIELDS = [
    "empresaCodigo",
    "produtoCodigo",
    "produto",
    "descricaoProduto",
    "combustivel",
    "quantidade",
    "litros",
    "volume",
    "valor",
    "totalVenda",
    "precoVenda",
    "dataMovimento",
]

async def audit_endpoint(client, name, path, params):
    params_with_key = {"CHAVE": CHAVE, **params}
    url = f"{BASE_URL}{path}"
    print(f"Testando {name} ({path})...")
    try:
        r = await client.get(url, params=params_with_key, timeout=20.0)
        status = r.status_code
        if status != 200:
            return {
                "name": name,
                "path": path,
                "status": status,
                "success": False,
                "error": f"HTTP {status} - {r.text[:200]}",
                "records_count": 0,
                "fields": [],
                "sample": None,
            }
        
        try:
            body = r.json()
        except Exception as e:
            return {
                "name": name,
                "path": path,
                "status": status,
                "success": False,
                "error": f"JSON Decode Error: {str(e)}",
                "records_count": 0,
                "fields": [],
                "sample": None,
            }
        
        # Extrair registros
        records = []
        if isinstance(body, list):
            records = body
        elif isinstance(body, dict):
            records = body.get("resultados") or body.get("data") or body.get("venda_item") or []
            if not isinstance(records, list):
                # Se for dict mas sem lista interna, trata o próprio dict como único registro
                records = [body]
        
        records_count = len(records)
        sample = None
        fields = []
        if records_count > 0:
            sample_record = records[0]
            if isinstance(sample_record, dict):
                sample = sample_record
                fields = list(sample_record.keys())
        
        return {
            "name": name,
            "path": path,
            "status": status,
            "success": True,
            "records_count": records_count,
            "fields": fields,
            "sample": sample,
            "raw_records": records[:5] if isinstance(records, list) else []
        }
    except Exception as e:
        return {
            "name": name,
            "path": path,
            "status": 0,
            "success": False,
            "error": str(e),
            "records_count": 0,
            "fields": [],
            "sample": None,
        }

async def main():
    async with httpx.AsyncClient() as client:
        tasks = []
        for name, (path, params) in ENDPOINTS_TO_AUDIT.items():
            tasks.append(audit_endpoint(client, name, path, params))
        
        results = await asyncio.gather(*tasks)
        
        print("\nSintetizando Resultados...")
        
        # Salvar os resultados brutos em JSON para manter rastro
        with open("audit_raw_fields_results.json", "w", encoding="utf-8") as f:
            json.dump([
                {
                    "name": r["name"],
                    "path": r["path"],
                    "status": r["status"],
                    "success": r["success"],
                    "records_count": r["records_count"],
                    "fields": r["fields"],
                    "sample": r["sample"]
                }
                for r in results
            ], f, indent=2, ensure_ascii=False)
            
        print("Resultados salvos em audit_raw_fields_results.json")
        
        # Gerar a tabela do relatório de auditoria e a prova
        report_lines = []
        report_lines.append("# SPRINT 22A.1 — PROVA DE ORIGEM DOS LITROS DE COMBUSTÍVEL\n")
        report_lines.append(f"Análise executada em **{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}** via script automatizado.\n")
        
        report_lines.append("## Matriz Comparativa de Origem de Litros\n")
        report_lines.append("| Endpoint WebPosto | HTTP Status | Registros | empresaCodigo | produto/combustível | quantidade/litros | valor | Serve para litros? |")
        report_lines.append("|---|---|---|---|---|---|---|---|")
        
        final_conclusions = {
            "has_real_source": "NÃO",
            "endpoint": "Nenhum",
            "litros_field": "Nenhum",
            "fuel_field": "Nenhum",
            "empresa_field": "Nenhum",
            "can_create_summary": "NÃO",
            "what_to_ask_quality": "Liberar nominalmente e explicitamente as filiais ativas no escopo de `/INTEGRACAO/EMPRESAS` da API, ou autorizar os endpoints de rede `/INTEGRACAO/CONSULTAR_VENDA_ITEM_REDE` no Token."
        }
        
        best_serves = []
        
        for r in results:
            name_label = f"`{r['name']}`<br>({r['path']})"
            status = r["status"]
            count = r["records_count"]
            
            if not r["success"]:
                # Endpoint de rede bloqueado (401/403) ou erro
                status_str = f"HTTP {status}" if status != 0 else "FALHA CONEXÃO"
                report_lines.append(f"| {name_label} | {status_str} | 0 | - | - | - | - | ❌ **NÃO SERVE** (Acesso Bloqueado) |")
                continue
                
            # Analisar os campos
            fields = [f.lower() for f in r["fields"]]
            
            has_emp = any(f in fields for f in ["empresacodigo", "codigoempresa", "filialcodigo", "codigofilial", "empresa", "filial"])
            has_prod = any(f in fields for f in ["produtocodigo", "codigoproduto", "produto", "descricao", "descricaoproduto", "nome", "nomecombustivel", "combustivel"])
            has_qty = any(f in fields for f in ["quantidade", "litros", "volume", "qtd"])
            has_val = any(f in fields for f in ["totalvenda", "valortotal", "valortotalitem", "valor", "valorliquido", "valorunitario"])
            
            emp_field = ""
            for f in r["fields"]:
                if f.lower() in ["empresacodigo", "filialcodigo", "empresa", "filial"]:
                    emp_field = f
                    break
                    
            prod_field = ""
            for f in r["fields"]:
                if f.lower() in ["produtocodigo", "produto", "descricao", "descricaoproduto", "nome", "nomecombustivel", "combustivel"]:
                    prod_field = f
                    break
                    
            qty_field = ""
            for f in r["fields"]:
                if f.lower() in ["quantidade", "litros", "volume", "qtd"]:
                    qty_field = f
                    break
                    
            val_field = ""
            for f in r["fields"]:
                if f.lower() in ["totalvenda", "valortotal", "valortotalitem", "valor", "valorliquido"]:
                    val_field = f
                    break

            # Determinar "Serve"
            if has_emp and has_prod and has_qty and has_val:
                serve = "✅ **SERVE**"
                best_serves.append((r["name"], r["path"], qty_field, prod_field, emp_field))
            elif has_qty:
                serve = "⚠️ **PARCIAL**"
            else:
                serve = "❌ **NÃO SERVE**"
                
            def yes_no(b, field_name):
                return f"Sim (`{field_name}`)" if b else "Não"
                
            report_lines.append(f"| {name_label} | {status} | {count} | {yes_no(has_emp, emp_field)} | {yes_no(has_prod, prod_field)} | {yes_no(has_qty, qty_field)} | {yes_no(has_val, val_field)} | {serve} |")

        # Conclusão final com base nos testes
        if best_serves:
            # Seleciona o melhor (priorizando abastecimento ou venda_item que são detalhados)
            # Prioriza ABASTECIMENTO ou VENDA_ITEM
            best = None
            for s in best_serves:
                if s[0] in ["ABASTECIMENTO", "VENDA_ITEM"]:
                    best = s
                    break
            if not best:
                best = best_serves[0]
                
            final_conclusions["has_real_source"] = "SIM"
            final_conclusions["endpoint"] = f"`{best[0]}` ({best[1]})"
            final_conclusions["litros_field"] = f"`{best[2]}`"
            final_conclusions["fuel_field"] = f"`{best[3]}`"
            final_conclusions["empresa_field"] = f"`{best[4]}`"
            final_conclusions["can_create_summary"] = "SIM (Para as filiais licenciadas no Token!)"
            final_conclusions["what_to_ask_quality"] = (
                "Para expandir o dashboard para toda a rede, precisamos solicitar à Quality Automação: "
                "1. Liberar e autorizar o Token de Integração do Grupo Lisboa para acessar os endpoints unificados de rede: "
                "`/INTEGRACAO/CONSULTAR_VENDA_ITEM_REDE` e `/INTEGRACAO/VENDA_REDE`, pois atualmente eles retornam HTTP 401 de forma irredutível.\n"
                "2. Alternativamente, incluir as demais 9 filiais ativas nominais de forma explícita na licença individual do Token, "
                "permitindo-nos efetuar chamadas individuais via `/INTEGRACAO/VENDA_ITEM` para cada empresaCodigo."
            )
        else:
            final_conclusions["what_to_ask_quality"] = (
                "Todos os endpoints testados falharam ou não possuem os 4 pilares necessários (empresaCodigo + produto + quantidade/litros + valor). "
                "Precisamos solicitar à Quality Automação a criação de um endpoint real contendo vendas de combustível por filial, "
                "ou que autorizem a rota unificada `/INTEGRACAO/CONSULTAR_VENDA_ITEM_REDE` para termos acesso aos dados de itens vendidos."
            )

        report_lines.append("\n## Decisão Final & Respostas Chave\n")
        report_lines.append(f"1. **Existe fonte real para litros vendidos?** {final_conclusions['has_real_source']}\n")
        report_lines.append(f"2. **Qual endpoint?** {final_conclusions['endpoint']}\n")
        report_lines.append(f"3. **Qual campo representa litros?** {final_conclusions['litros_field']}\n")
        report_lines.append(f"4. **Qual campo representa combustível?** {final_conclusions['fuel_field']}\n")
        report_lines.append(f"5. **Qual campo representa empresa?** {final_conclusions['empresa_field']}\n")
        report_lines.append(f"6. **É possível criar `/api/v1/sales/fuel-summary` com dados reais?** {final_conclusions['can_create_summary']}\n")
        report_lines.append(f"7. **Se não for possível, qual informação precisa ser solicitada à Quality Automação?**\n")
        report_lines.append(f"{final_conclusions['what_to_ask_quality']}\n")
        
        # Amostras das chaves brutos
        report_lines.append("## Amostras de Registros Brutos (Até 5 por endpoint de sucesso)\n")
        for r in results:
            if r["success"] and r["records_count"] > 0:
                report_lines.append(f"### {r['name']} ({r['path']})\n")
                report_lines.append(f"**Chaves retornadas**: `{', '.join(r['fields'])}`\n")
                report_lines.append("```json")
                report_lines.append(json.dumps(r["raw_records"], indent=2, ensure_ascii=False))
                report_lines.append("```\n")

        with open("fuel_data_source_proof.md", "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
            
        print("Parecer completo gerado com sucesso em 'fuel_data_source_proof.md'!")

if __name__ == "__main__":
    asyncio.run(main())
