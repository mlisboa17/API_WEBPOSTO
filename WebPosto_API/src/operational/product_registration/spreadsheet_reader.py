"""Leitura de XLSX com mapeamento flexível de colunas (FASE 3)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import openpyxl

from .schemas import ProductRow


def calculate_file_hash(filepath: Path | str) -> str:
    """Calcula SHA-256 do arquivo XLSX."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def read_products_sheet(
    filepath: Path | str,
    sheet_name: str = "PRODUTOS_ANALISADOS",
    header_row: int = 4,
    data_start_row: int = 5,
) -> tuple[list[ProductRow], dict[str, Any]]:
    """
    Lê planilha de produtos com mapeamento de colunas.
    
    Retorna (produtos, metadata).
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Planilha não encontrada: {filepath}")

    wb = openpyxl.load_workbook(filepath, data_only=True)
    if sheet_name not in wb.sheetnames:
        raise ValueError(f"Aba '{sheet_name}' não encontrada. Abas: {wb.sheetnames}")

    ws = wb[sheet_name]

    # Mapear colunas a partir da linha 4
    header_row_data = ws[header_row]
    column_map: dict[str, int] = {}
    for col_idx, cell in enumerate(header_row_data, 1):
        header_name = str(cell.value or "").strip().upper()
        if header_name:
            column_map[header_name] = col_idx

    # Validar colunas obrigatórias
    required_columns = ["EAN", "DESCRICAO", "PRECO_VENDA", "EMPRESA_CODIGO"]
    missing_columns = [col for col in required_columns if col not in column_map]
    if missing_columns:
        raise ValueError(f"Colunas obrigatórias ausentes: {missing_columns}")

    # Mapear coluna → propriedade ProductRow
    column_mapping: dict[str, str] = {
        "LINHA_ORIGEM": "linha_origem",
        "EAN": "ean",
        "DESCRICAO": "descricao",
        "PRECO_VENDA": "preco_venda",
        "EMPRESA_CODIGO": "empresa_codigo",
        "EMPRESA_NOME": "empresa_nome",
        "GRUPO_API_CODIGO": "grupo_api_codigo",
        "CENTRO_API_CODIGO": "centro_api_codigo",
        "PRECO_COMPRA": "preco_compra",
        "PRECO_CUSTO": "preco_custo",
        "NCM": "ncm",
        "CEST": "cest",
        "CFOP_ENTRADA": "cfop_entrada",
        "CFOP_SAIDA": "cfop_saida",
        "IAT": "iat",
        "IPPT": "ippt",
        "ICMS_MODELO": "icms_modelo",
        "PIS_COFINS_MODELO": "pis_cofins_modelo",
        "EVIDENCIA_NFE": "evidencia_nfe",
        "EAN_VALIDO": "ean_valido_coluna",
        "DUPLICADO_NA_PLANILHA": "duplicado_na_planilha",
        "STATUS": "status_planilha",
        "OBSERVACAO": "observacao",
    }

    products: list[ProductRow] = []
    row_idx = data_start_row
    max_row = ws.max_row

    while row_idx <= max_row:
        # Verificar se há dados na linha (coluna EAN)
        ean_col_idx = column_map["EAN"]
        ean_cell = ws.cell(row_idx, ean_col_idx)
        if ean_cell.value is None:
            break

        # Extrair dados
        row_data: dict[str, Any] = {}
        for header_key, prop_name in column_mapping.items():
            if header_key in column_map:
                col_idx = column_map[header_key]
                cell = ws.cell(row_idx, col_idx)
                value = cell.value
                
                # Preservar zeros à esquerda em EAN
                if header_key == "EAN" and value is not None:
                    value = str(value).strip()
                
                # Normalizar tipos numéricos
                if header_key in ["PRECO_VENDA", "PRECO_COMPRA", "PRECO_CUSTO"]:
                    if value is not None:
                        try:
                            value = float(value)
                        except (ValueError, TypeError):
                            value = None
                
                if header_key in ["EMPRESA_CODIGO", "GRUPO_API_CODIGO", "CENTRO_API_CODIGO"]:
                    if value is not None:
                        try:
                            value = int(value)
                        except (ValueError, TypeError):
                            value = None
                
                if header_key in ["EVIDENCIA_NFE", "EAN_VALIDO", "DUPLICADO_NA_PLANILHA"]:
                    if isinstance(value, bool):
                        pass
                    elif isinstance(value, str):
                        value = value.lower() in ("sim", "true", "1", "yes")
                    elif isinstance(value, (int, float)):
                        value = bool(value)
                    else:
                        value = False
                
                row_data[prop_name] = value

        # Criar ProductRow
        try:
            product = ProductRow(**row_data)
            products.append(product)
        except Exception as e:
            # Log de erro, continuar
            print(f"Aviso: linha {row_idx} ignorada: {e}")

        row_idx += 1

    wb.close()

    # Metadata
    metadata = {
        "filepath": str(filepath),
        "sheet_name": sheet_name,
        "total_rows": len(products),
        "file_hash": calculate_file_hash(filepath),
        "header_row": header_row,
        "data_start_row": data_start_row,
        "read_at": datetime.now().isoformat(),
    }

    return products, metadata


from datetime import datetime
