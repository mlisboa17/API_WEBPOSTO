#!/usr/bin/env python3
"""
EXECUTOR CONTÍNUO — FASES A-I SEM INTERRUPÇÕES
Empresa 118508 | WebPosto Conveniência 24 Horas

Executa sequencialmente:
  A. Validar/reconciliar 484 registros (GTIN, checksum, duplicidade)
  B. Reutilizar 174 NF-e / 928 itens (índice EAN → nota)
  C. Resolver grupos automaticamente (catálogo WebPosto)
  D. Resolver NCM/CEST (NF-e, modelo, consenso)
  E. Preço compra/custo (NF-e com conversão, regra)
  F. Tributação (modelo fiscal aprovado)
  G. Novo preflight pós-enriquecimento (READY, REVIEW, BLOCKED)
  H. Cadastro real autorizado (POST /INTEGRACAO/INCLUIR_PRODUTO)
  I. Relatório final com contagens e audit trail
"""

import sys
import os
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent))

import json
import hashlib
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from collections import defaultdict

import httpx
from openpyxl import load_workbook
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

BASE_URL = "https://web.qualityautomacao.com.br"
API_KEY = os.getenv("WEBPOSTO_API_KEY")
EMPRESA_CODIGO = 118508
EMPRESA_NOME = "CONVENIENCIA 24 HORAS"
CNPJ = "02080237000155"
REGIME = "LUCRO_PRESUMIDO"
UF = "PE"
CENTRO_CUSTO = 24886

# Planilha de produtos (484 registros linha 5-488, cabeçalho linha 4)
PLANILHA_PATH = Path(
    r"C:\Users\mlisb\Documents\Codex\2026-08-11\logos-webposto-codex-alterar-produto-safe\outputs\019ff247-8453-7c90-93f1-1458b660ffc2\CADASTRO_PRODUTOS_WEBPOSTO_VALIDADO.xlsx"
)

# Armazenamento DF-e
DFE_STORE_DIR = Path(__file__).parent / "data" / "dfe_store"

# Output
OUTPUT_DIR = Path(__file__).parent / "data" / "product_registration" / "executions"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Logging
import io
import sys

LOG_LEVEL = logging.INFO
log_filename = datetime.now().strftime("%Y%m%d_%H%M%S")

# Reconfigurar stdout/stderr para UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(OUTPUT_DIR / f"execution_{log_filename}.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# SCHEMAS LOCAIS
# ============================================================================

class GTINValidator:
    """Validar GTIN-8, 12, 13, 14 com checksum."""
    
    @staticmethod
    def calculate_checksum(ean_without_check: str) -> str:
        """Calcula dígito verificador GTIN."""
        ean = ean_without_check.strip()
        total = 0
        for i, d in enumerate(reversed(ean)):
            weight = 3 if i % 2 == 0 else 1
            total += int(d) * weight
        check_digit = (10 - (total % 10)) % 10
        return str(check_digit)
    
    @staticmethod
    def validate(ean: str) -> tuple[bool, Optional[str], str]:
        """
        Valida GTIN.
        Retorna (válido, tipo_gtin, mensagem)
        """
        if not ean:
            return False, None, "EAN vazio"
        
        ean = str(ean).strip()
        
        # Preservar zeros à esquerda
        if not ean.isdigit():
            return False, None, "EAN contém caracteres não numéricos"
        
        gtin_type = None
        if len(ean) == 8:
            gtin_type = "GTIN-8"
        elif len(ean) == 12:
            gtin_type = "GTIN-12"
        elif len(ean) == 13:
            gtin_type = "GTIN-13"
        elif len(ean) == 14:
            gtin_type = "GTIN-14"
        else:
            return False, None, f"Tamanho inválido: {len(ean)} dígitos"
        
        # Validar checksum
        ean_base = ean[:-1]
        expected_check = GTINValidator.calculate_checksum(ean_base)
        actual_check = ean[-1]
        
        if expected_check != actual_check:
            return False, gtin_type, f"Checksum inválido: esperado {expected_check}, obtido {actual_check}"
        
        return True, gtin_type, "OK"


class DFEIndexer:
    """Carrega índice DF-e em memória (174 NF-e, 928 itens)."""
    
    def __init__(self, dfe_store_dir: Path):
        self.dfe_store_dir = Path(dfe_store_dir)
        self.index: dict[str, list[dict]] = defaultdict(list)  # ean → [items]
        self.nfe_map: dict[str, dict] = {}  # chave_nfe → metadata
        self.load_index()
    
    def load_index(self):
        """Carregar arquivos de itens JSON."""
        if not self.dfe_store_dir.exists():
            logger.warning(f"DFE store nao encontrado: {self.dfe_store_dir}")
            return
        
        items_dir = self.dfe_store_dir / "items"
        if not items_dir.exists():
            logger.warning(f"Items dir nao encontrado: {items_dir}")
            return
        
        count = 0
        for json_file in items_dir.glob("dfe_doc_*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Esperado: {document_id, items: [...]}
                items = data.get("items", []) if isinstance(data, dict) else []
                
                for item in items:
                    # Procurar EAN em raw_json ou normalized_json
                    raw = item.get("raw_json", {})
                    normalized = item.get("normalized_json", {})
                    
                    ean = (raw.get("cEAN") or 
                           raw.get("cEANTrib") or
                           normalized.get("c_ean") or
                           normalized.get("c_ean_trib"))
                    
                    if ean and ean != "SEM GTIN":
                        self.index[ean].append(item)
                        count += 1
            except Exception as e:
                logger.debug(f"Erro lendo {json_file}: {e}")
        
        logger.info(f"DFE INDEX CARREGADO: {count} items, {len(self.index)} EANs unicos")


class SpreadsheetReader:
    """Lê planilha com 484 produtos."""
    
    def __init__(self, xlsx_path: Path):
        self.xlsx_path = Path(xlsx_path)
        self.products: list[dict] = []
        self.metadata = {}
        self.read()
    
    def read(self):
        """Lê 484 produtos, linha 5-488, cabeçalho linha 4."""
        if not self.xlsx_path.exists():
            raise FileNotFoundError(f"Planilha não encontrada: {self.xlsx_path}")
        
        wb = load_workbook(self.xlsx_path, data_only=True)
        
        # Tentar encontrar a aba PRODUTOS_ANALISADOS ou primeira aba
        sheet_name = "PRODUTOS_ANALISADOS" if "PRODUTOS_ANALISADOS" in wb.sheetnames else wb.sheetnames[0]
        ws = wb[sheet_name]
        
        # Linha 4: cabeçalho
        header_row = 4
        column_map = {}
        for col_idx, cell in enumerate(ws[header_row], 1):
            header = str(cell.value or "").strip().upper()
            if header:
                column_map[header] = col_idx
        
        logger.info(f"Colunas encontradas: {sorted(column_map.keys())}")
        
        # Ler dados: linhas 5-488
        for row_idx in range(5, 489):
            ean_col = column_map.get("EAN")
            if not ean_col or ws.cell(row_idx, ean_col).value is None:
                break
            
            produto = {}
            for header, col_idx in column_map.items():
                value = ws.cell(row_idx, col_idx).value
                
                # Normalizar
                if header == "EAN":
                    value = str(value).strip() if value else None
                elif header in ["PRECO_VENDA", "PRECO_COMPRA", "PRECO_CUSTO"]:
                    try:
                        value = float(value) if value else None
                    except:
                        value = None
                elif header in ["EMPRESA_CODIGO", "GRUPO_API_CODIGO", "CENTRO_API_CODIGO"]:
                    try:
                        value = int(value) if value else None
                    except:
                        value = None
                
                produto[header.lower()] = value
            
            produto["linha_origem"] = row_idx
            self.products.append(produto)
        
        wb.close()
        
        self.metadata = {
            "arquivo": str(self.xlsx_path),
            "aba": sheet_name,
            "total_linhas": len(self.products),
            "cabeçalho_linha": header_row,
            "dados_linha_inicio": 5,
            "dados_linha_fim": 488,
            "lido_em": datetime.now(timezone.utc).isoformat(),
        }
        
        logger.info(f"PLANILHA LIDA: {len(self.products)} produtos")


# ============================================================================
# FASE A: CORRIGIR PREFLIGHT
# ============================================================================

def fase_a_validacao_preflight(produtos: list[dict]) -> dict[str, Any]:
    """
    FASE A — Validar 484 registros:
    - GTIN checksum
    - Tipo GTIN
    - Duplicatas na planilha
    """
    logger.info("\n" + "="*80)
    logger.info("FASE A — VALIDAÇÃO PREFLIGHT (GTIN, CHECKSUM, DUPLICATA)")
    logger.info("="*80)
    
    stats = {
        "TOTAL": len(produtos),
        "VALID_GTIN_8": 0,
        "VALID_GTIN_12": 0,
        "VALID_GTIN_13": 0,
        "VALID_GTIN_14": 0,
        "VALID_CHECKSUM": 0,
        "INVALID_GTIN": 0,
        "NON_STANDARD": 0,
        "DUPLICATES": {},
        "LEADING_ZEROS": 0,
    }
    
    ean_map = {}  # ean → [linhas]
    
    for produto in produtos:
        ean = produto.get("ean")
        linha = produto.get("linha_origem")
        
        if not ean:
            stats["INVALID_GTIN"] += 1
            produto["_status_preflight"] = "MISSING_EAN"
            continue
        
        # Validar checksum
        is_valid, gtin_type, msg = GTINValidator.validate(ean)
        
        if is_valid:
            stats["VALID_CHECKSUM"] += 1
            if gtin_type == "GTIN-8":
                stats["VALID_GTIN_8"] += 1
            elif gtin_type == "GTIN-12":
                stats["VALID_GTIN_12"] += 1
            elif gtin_type == "GTIN-13":
                stats["VALID_GTIN_13"] += 1
            elif gtin_type == "GTIN-14":
                stats["VALID_GTIN_14"] += 1
            
            # Detectar zeros à esquerda
            if ean != ean.lstrip("0") and len(ean.lstrip("0")) > 0:
                stats["LEADING_ZEROS"] += 1
            
            produto["_status_preflight"] = "VALID_GTIN"
            produto["_gtin_type"] = gtin_type
        else:
            stats["INVALID_GTIN"] += 1
            produto["_status_preflight"] = f"INVALID_GTIN: {msg}"
        
        # Detectar duplicatas
        if ean in ean_map:
            ean_map[ean].append(linha)
            stats["DUPLICATES"][ean] = ean_map[ean]
        else:
            ean_map[ean] = [linha]
    
    logger.info(f"✓ Total: {stats['TOTAL']}")
    logger.info(f"✓ GTIN-8: {stats['VALID_GTIN_8']}")
    logger.info(f"✓ GTIN-12: {stats['VALID_GTIN_12']}")
    logger.info(f"✓ GTIN-13: {stats['VALID_GTIN_13']}")
    logger.info(f"✓ GTIN-14: {stats['VALID_GTIN_14']}")
    logger.info(f"✓ Checksum válido: {stats['VALID_CHECKSUM']}")
    logger.info(f"✗ GTIN inválido: {stats['INVALID_GTIN']}")
    logger.info(f"✓ Com zeros à esquerda: {stats['LEADING_ZEROS']}")
    logger.info(f"✓ Duplicatas na planilha: {len(stats['DUPLICATES'])}")
    
    return {
        "fase": "A",
        "stats": stats,
        "ean_map": ean_map,
    }


# ============================================================================
# FASE B: REUTILIZAR DF-e REAL
# ============================================================================

def fase_b_enriquecer_dfe(produtos: list[dict], dfe_indexer: DFEIndexer) -> dict[str, Any]:
    """
    FASE B — Enriquecer com dados DF-e (174 NF-e, 928 itens).
    """
    logger.info("\n" + "="*80)
    logger.info("FASE B — ENRIQUECIMENTO COM DF-e")
    logger.info("="*80)
    
    stats = {
        "DFE_MATCHED": 0,
        "DFE_NOT_MATCHED": 0,
        "DFE_INDEX_SIZE": len(dfe_indexer.index),
        "DFE_TOTAL_ITEMS": sum(len(v) for v in dfe_indexer.index.values()),
    }
    
    for produto in produtos:
        if produto.get("_status_preflight") != "VALID_GTIN":
            continue
        
        ean = produto.get("ean")
        
        if ean in dfe_indexer.index:
            items = dfe_indexer.index[ean]
            # Pegar primeiro item como evidência
            first_item = items[0]
            
            produto["_dfe_matched"] = True
            produto["_dfe_ncm"] = first_item.get("NCM") or first_item.get("ncm")
            produto["_dfe_cest"] = first_item.get("CEST") or first_item.get("cest")
            produto["_dfe_cfop_entrada"] = first_item.get("CFOP", {}).get("entrada") or "1.102"
            produto["_dfe_cfop_saida"] = first_item.get("CFOP", {}).get("saida") or "5.405"
            produto["_dfe_unidade_comercial"] = first_item.get("uCom") or first_item.get("unidade")
            produto["_dfe_unidade_tributaria"] = first_item.get("uTrib") or first_item.get("unidade")
            
            stats["DFE_MATCHED"] += 1
        else:
            produto["_dfe_matched"] = False
            stats["DFE_NOT_MATCHED"] += 1
    
    logger.info(f"✓ DFe matched: {stats['DFE_MATCHED']}")
    logger.info(f"✗ DFe not matched: {stats['DFE_NOT_MATCHED']}")
    logger.info(f"  DFe index size: {stats['DFE_INDEX_SIZE']} EANs únicos")
    logger.info(f"  DFe total items: {stats['DFE_TOTAL_ITEMS']}")
    
    return {
        "fase": "B",
        "stats": stats,
    }


# ============================================================================
# FASES C-I (PLACEHOLDERS — continuar desenvolvimento)
# ============================================================================

def fase_c_resolver_grupos(produtos: list[dict], api_client: httpx.Client) -> dict[str, Any]:
    """FASE C — Resolver grupos."""
    logger.info("\n" + "="*80)
    logger.info("FASE C — RESOLVER GRUPOS")
    logger.info("="*80)
    
    # TODO: Implementar lógica completa
    logger.warning("⚠ FASE C (Resolver Grupos) — placeholder")
    
    return {"fase": "C", "stats": {"grupos_resolvidos": 0}}


def fase_d_resolver_ncm_cest(produtos: list[dict]) -> dict[str, Any]:
    """FASE D — Resolver NCM/CEST."""
    logger.info("\n" + "="*80)
    logger.info("FASE D — RESOLVER NCM/CEST")
    logger.info("="*80)
    
    logger.warning("⚠ FASE D (Resolver NCM/CEST) — placeholder")
    
    return {"fase": "D", "stats": {"ncm_resolvidos": 0}}


def fase_e_preco_compra_custo(produtos: list[dict]) -> dict[str, Any]:
    """FASE E — Preço de compra e custo."""
    logger.info("\n" + "="*80)
    logger.info("FASE E — PREÇO COMPRA/CUSTO")
    logger.info("="*80)
    
    logger.warning("⚠ FASE E (Preço Compra/Custo) — placeholder")
    
    return {"fase": "E", "stats": {"precos_resolvidos": 0}}


def fase_f_tributacao(produtos: list[dict], api_client: httpx.Client) -> dict[str, Any]:
    """FASE F — Tributação."""
    logger.info("\n" + "="*80)
    logger.info("FASE F — TRIBUTAÇÃO")
    logger.info("="*80)
    
    logger.warning("⚠ FASE F (Tributação) — placeholder")
    
    return {"fase": "F", "stats": {"modelos_aplicados": 0}}


def fase_g_preflight_pos_enriquecimento(produtos: list[dict]) -> dict[str, Any]:
    """FASE G — Preflight pós-enriquecimento."""
    logger.info("\n" + "="*80)
    logger.info("FASE G — PREFLIGHT PÓS-ENRIQUECIMENTO")
    logger.info("="*80)
    
    stats = {
        "READY_TO_CREATE": 0,
        "REVIEW_REQUIRED": 0,
        "BLOCKED": 0,
    }
    
    for produto in produtos:
        # Lógica simplificada: se passou FASE A+B, considerar READY
        if produto.get("_status_preflight") == "VALID_GTIN":
            stats["READY_TO_CREATE"] += 1
            produto["_final_status"] = "READY_TO_CREATE"
        else:
            stats["BLOCKED"] += 1
            produto["_final_status"] = "BLOCKED"
    
    logger.info(f"✓ READY_TO_CREATE: {stats['READY_TO_CREATE']}")
    logger.info(f"⚠ REVIEW_REQUIRED: {stats['REVIEW_REQUIRED']}")
    logger.info(f"✗ BLOCKED: {stats['BLOCKED']}")
    
    return {
        "fase": "G",
        "stats": stats,
    }


def fase_h_cadastro_real(produtos: list[dict], api_client: httpx.Client, api_key: str) -> dict[str, Any]:
    """FASE H — Cadastro real (POST /INTEGRACAO/INCLUIR_PRODUTO)."""
    logger.info("\n" + "="*80)
    logger.info("FASE H — CADASTRO REAL (HTTP POST)")
    logger.info("="*80)
    
    logger.warning("⚠ FASE H (Cadastro Real) — placeholder (não faz POST sem revisão)")
    
    return {
        "fase": "H",
        "stats": {
            "posts_executados": 0,
            "sucessos": 0,
            "falhas": 0,
        },
    }


def fase_i_relatorio_final(
    produtos: list[dict],
    metadata: dict,
    fase_results: list[dict]
) -> dict[str, Any]:
    """FASE I — Relatório final."""
    logger.info("\n" + "="*80)
    logger.info("FASE I — RELATÓRIO FINAL")
    logger.info("="*80)
    
    ready_count = sum(1 for p in produtos if p.get("_final_status") == "READY_TO_CREATE")
    blocked_count = sum(1 for p in produtos if p.get("_final_status") == "BLOCKED")
    
    report = {
        "empresa": EMPRESA_CODIGO,
        "empresa_nome": EMPRESA_NOME,
        "cnpj": CNPJ,
        "regime": REGIME,
        "uf": UF,
        "centro_custo": CENTRO_CUSTO,
        "total_produtos": len(produtos),
        "ready_to_create": ready_count,
        "blocked": blocked_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fases_executadas": [r["fase"] for r in fase_results],
    }
    
    logger.info(f"✓ Total de produtos: {report['total_produtos']}")
    logger.info(f"✓ READY_TO_CREATE: {report['ready_to_create']}")
    logger.info(f"✗ BLOCKED: {report['blocked']}")
    logger.info(f"✓ Relatório gerado: {datetime.now().isoformat()}")
    
    return report


# ============================================================================
# MAIN: EXECUTAR FASES A-I
# ============================================================================

def main():
    """Executar FASES A-I sem interrupções."""
    
    logger.info("\n" + "="*80)
    logger.info("=" + " "*78 + "=")
    logger.info("=" + "  EXECUTOR CONTINUO - FASES A-I SEM INTERRUPCOES".center(78) + "=")
    logger.info("=" + f"  Empresa {EMPRESA_CODIGO} | {EMPRESA_NOME}".center(78) + "=")
    logger.info("=" + " "*78 + "=")
    logger.info("="*80)
    
    # 1. Ler planilha
    logger.info("\n[1/3] Lendo planilha de produtos...")
    reader = SpreadsheetReader(PLANILHA_PATH)
    produtos = reader.products
    
    # 2. Carregar índice DF-e
    logger.info("[2/3] Carregando índice DF-e...")
    dfe_indexer = DFEIndexer(DFE_STORE_DIR)
    
    # 3. HTTP client para API WebPosto
    logger.info("[3/3] Inicializando cliente HTTP...")
    
    fase_results = []
    
    try:
        with httpx.Client(timeout=120) as http_client:
            # FASE A: Validação preflight
            resultado_a = fase_a_validacao_preflight(produtos)
            fase_results.append(resultado_a)
            
            # FASE B: Enriquecimento DF-e
            resultado_b = fase_b_enriquecer_dfe(produtos, dfe_indexer)
            fase_results.append(resultado_b)
            
            # FASE C: Resolver grupos
            resultado_c = fase_c_resolver_grupos(produtos, http_client)
            fase_results.append(resultado_c)
            
            # FASE D: NCM/CEST
            resultado_d = fase_d_resolver_ncm_cest(produtos)
            fase_results.append(resultado_d)
            
            # FASE E: Preço
            resultado_e = fase_e_preco_compra_custo(produtos)
            fase_results.append(resultado_e)
            
            # FASE F: Tributação
            resultado_f = fase_f_tributacao(produtos, http_client)
            fase_results.append(resultado_f)
            
            # FASE G: Preflight pós-enriquecimento
            resultado_g = fase_g_preflight_pos_enriquecimento(produtos)
            fase_results.append(resultado_g)
            
            # FASE H: Cadastro real
            resultado_h = fase_h_cadastro_real(produtos, http_client, API_KEY)
            fase_results.append(resultado_h)
            
            # FASE I: Relatório final
            relatorio = fase_i_relatorio_final(produtos, reader.metadata, fase_results)
            
            # Salvar relatório
            report_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = OUTPUT_DIR / f"relatorio_fases_a_i_{report_ts}.json"
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(relatorio, f, indent=2, ensure_ascii=False)
            
            logger.info(f"\n[OK] Relatorio salvo em: {report_path}")
            
    except Exception as e:
        logger.error(f"[ERRO] Erro durante execucao: {e}", exc_info=True)
        raise
    
    logger.info("\n" + "="*80)
    logger.info("=" + " FIM DA EXECUCAO ".center(78, "=") + "=")
    logger.info("="*80 + "\n")


if __name__ == "__main__":
    main()
