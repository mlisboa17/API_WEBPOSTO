#!/usr/bin/env python3
"""
SUMÁRIO EXECUTIVO — FASES A-I
Gera dashboard textual com estatísticas consolidadas
"""

import json
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path(__file__).parent / "data" / "product_registration" / "executions"

# Encontrar relatório mais recente
relatorios = sorted(OUTPUT_DIR.glob("relatorio_fases_a_i_*.json"), reverse=True)

if not relatorios:
    print("[ERRO] Nenhum relatório encontrado")
    exit(1)

rel_path = relatorios[0]

with open(rel_path, "r", encoding="utf-8") as f:
    relatorio = json.load(f)

# ============================================================================
# DASHBOARD
# ============================================================================

print("\n" + "="*80)
print("SUMARIO EXECUTIVO — FASES A-I")
print("="*80)

print(f"\nEmpresa:  {relatorio.get('empresa')} | {relatorio.get('cnpj', 'N/A')}")
print(f"CNPJ:     {relatorio.get('cnpj', 'N/A')}")
print(f"Regime:   {relatorio.get('regime', 'N/A')}")
print(f"UF:       {relatorio.get('uf', 'N/A')}")
print(f"Centro:   {relatorio.get('centro_custo', 'N/A')}")
print(f"Data:     {relatorio.get('timestamp', 'N/A')}")

print("\n" + "-"*80)
print("CONTADORES CONSOLIDADOS")
print("-"*80)

total = relatorio.get('total', 0)
ready = relatorio.get('ready_to_create', 0)
review = relatorio.get('review_required', 0)
blocked = relatorio.get('blocked', 0)

def pct(n, total):
    return f"{(100*n/total if total else 0):.1f}%" if total else "N/A"

print(f"\nTotal de Produtos:    {total:>4d}")
print(f"  READY_TO_CREATE:    {ready:>4d}  [{pct(ready, total):>5}]  [OK] Autorizado POST")
print(f"  REVIEW_REQUIRED:    {review:>4d}  [{pct(review, total):>5}]  [REVISAO] Requer enriquecimento")
print(f"  BLOCKED:            {blocked:>4d}  [{pct(blocked, total):>5}]  [ERRO] GTIN invalido")

print("\n" + "-"*80)
print("ANÁLISE DE RISCO")
print("-"*80)

if ready > 0:
    print(f"\n[OK] PRONTO PARA CADASTRO ({ready} produtos)")
    print(f"  - GTIN valido: SIM")
    print(f"  - DFe evidencia: SIM")
    print(f"  - Preco venda: SIM")
    print(f"  - Risco: BAIXO")
    print(f"  - Acao: Prosseguir com FASE H (POST /INTEGRACAO/INCLUIR_PRODUTO)")

if review > 0:
    print(f"\n[REVISAO] REQUER REVISAO ({review} produtos)")
    print(f"  - Status: GTIN valido mas dados incompletos")
    print(f"  - Faltando: Grupo, NCM, CEST, modelo fiscal")
    print(f"  - Risco: MEDIO")
    print(f"  - Acao: Enriquecimento automatico + manual")
    print(f"  - Timeline: 3-5 dias (80% automatico)")

if blocked > 0:
    print(f"\n[ERRO] BLOQUEADO ({blocked} produtos)")
    print(f"  - Status: GTIN invalido ou checksum incorreto")
    print(f"  - Risco: CRITICO")
    print(f"  - Acao: Retornar a origem, corrigir EAN")
    print(f"  - Timeline: 1-2 dias")

print("\n" + "-"*80)
print("PROXIMOS PASSOS")
print("-"*80)

print("\n1. IMEDIATO (48 horas)")
print("   [ ] Corrigir 18 GTINs inválidos")
print("   [ ] Completar GRUPO_API_CODIGO para 431 produtos")
print("   [ ] Obter DF-e complementar para 435 produtos")

print("\n2. CURTO PRAZO (1 semana)")
print("   [ ] Resolver NCM/CEST para 80%+ dos 435")
print("   [ ] Aplicar modelo fiscal aprovado")
print("   [ ] Calcular PRECO_COMPRA (conversão DF-e)")
print("   [ ] Expandir READY_TO_CREATE para 300+ produtos")

print("\n3. EXECUÇÃO (Semana 2)")
print("   [ ] FASE H: POST /INTEGRACAO/INCLUIR_PRODUTO")
print("   [ ] Monitorar respostas (HTTP 200/201, RET=3, etc.)")
print("   [ ] Validar pós-cadastro (GET /INTEGRACAO/V1/PRODUTOS)")
print("   [ ] Gerar relatório de audit trail")

print("\n" + "="*80)
print(f"Relatório: {rel_path.name}")
print("="*80 + "\n")
