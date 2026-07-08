"""DIR-01C — extração nominal de vales a partir de Prestação de Contas (markdown/PDF export)."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from src.services.decision_evidence.models import NominalEvidenceItem

ROOT = Path(__file__).resolve().parents[3]

SOURCE_PRESTACAO = "PRESTACAO_CONTAS"
FINANCIAL_NATURE_VALE = "VALE_FUNCIONARIO"
CAPTURE_ACCOUNTABILITY = "ACCOUNTABILITY_REPORT"

VALE_SECTION_MARKERS = (
    "vale de funcionários",
    "vale de funcionario",
    "vale de funcionários",
)
TABLE_ROW_RE = re.compile(
    r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|"
)
EMPRESA_RE = re.compile(
    r"(?:empresaCodigo|Código \(empresaCodigo\))[^|\n]*\|\s*(\d+)",
    re.I,
)
PERIOD_RE = re.compile(
    r"Per[ií]odo:?\*?\*?\s*(\d{2}/\d{2}/\d{4})\s*[aà\-—]\s*(\d{2}/\d{2}/\d{4})",
    re.I,
)
SOURCE_FILE_RE = re.compile(r"Arquivo Fonte:\*\*\s*`([^`]+)`")
TENANT_NAME_RE = re.compile(r"Tenant:\s*(\d+)\s*[—\-]\s*(.+)", re.I)


def _prestacao_search_dirs() -> list[Path]:
    logos_space = ROOT.parent.parent
    return [
        ROOT / "data" / "prestacao",
        ROOT / "docs" / "validation" / "prestacao",
        logos_space / "NewWebLogos" / "docs" / "validation",
        ROOT.parent / "NewWebLogos" / "docs" / "validation",
    ]


def _parse_br_date(value: str) -> str | None:
    raw = value.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw[:10], fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _parse_br_money(value: str) -> Decimal | None:
    raw = str(value or "").strip()
    if not raw or raw.upper() in {"—", "-", "TOTAL"}:
        return None
    try:
        normalized = raw.replace(".", "").replace(",", ".")
        return Decimal(normalized).quantize(Decimal("0.01"))
    except Exception:
        return None


def _periods_overlap(
    start_a: str | None,
    end_a: str | None,
    start_b: str | None,
    end_b: str | None,
) -> bool:
    if not all((start_a, end_a, start_b, end_b)):
        return True
    try:
        a0 = datetime.fromisoformat(start_a[:10])
        a1 = datetime.fromisoformat(end_a[:10])
        b0 = datetime.fromisoformat(start_b[:10])
        b1 = datetime.fromisoformat(end_b[:10])
        return a0 <= b1 and b0 <= a1
    except ValueError:
        return True


def locate_prestacao_source(
    *,
    empresa_codigo: str | int,
    period_start: str,
    period_end: str,
) -> dict[str, Any]:
    """Localiza arquivo de Prestação para empresa/período — nunca cruza postos."""
    target = str(empresa_codigo).strip()
    candidates: list[dict[str, Any]] = []

    for base in _prestacao_search_dirs():
        if not base.is_dir():
            continue
        for path in sorted(base.glob("RAW_DATA*.md")):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            empresa_match = EMPRESA_RE.search(text) or TENANT_NAME_RE.search(text)
            if not empresa_match:
                continue
            file_empresa = str(empresa_match.group(1)).strip()
            if file_empresa != target:
                continue
            period_match = PERIOD_RE.search(text)
            file_start = _parse_br_date(period_match.group(1)) if period_match else None
            file_end = _parse_br_date(period_match.group(2)) if period_match else None
            if not _periods_overlap(period_start, period_end, file_start, file_end):
                continue
            source_file = SOURCE_FILE_RE.search(text)
            candidates.append(
                {
                    "path": str(path),
                    "empresa_codigo": file_empresa,
                    "period_start": file_start,
                    "period_end": file_end,
                    "source_file": source_file.group(1) if source_file else path.name,
                    "tenant_name": empresa_match.group(2).strip() if empresa_match.lastindex and empresa_match.lastindex >= 2 else None,
                }
            )

    if not candidates:
        return {
            "found": False,
            "source_gap": True,
            "empresa_codigo": target,
            "searched_dirs": [str(p) for p in _prestacao_search_dirs()],
            "reason": (
                f"Nenhuma Prestação de Contas localizada para empresaCodigo={target} "
                f"com sobreposição ao período {period_start}..{period_end}."
            ),
        }

    chosen = candidates[0]
    return {"found": True, "source_gap": False, **chosen}


def _extract_vale_section(text: str) -> str:
    lines = text.splitlines()
    start_idx: int | None = None
    for idx, line in enumerate(lines):
        lower = line.casefold()
        if any(marker in lower for marker in VALE_SECTION_MARKERS) and line.strip().startswith("#"):
            start_idx = idx + 1
            break
    if start_idx is None:
        return ""
    chunk: list[str] = []
    for line in lines[start_idx:]:
        if line.strip().startswith("## ") and chunk:
            break
        chunk.append(line)
    return "\n".join(chunk)


def extract_vale_funcionario_items(
    *,
    path: Path | str,
    empresa_codigo: str | int,
    tenant_id: str | None = None,
    tenant_name: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
) -> tuple[list[NominalEvidenceItem], dict[str, Any]]:
    """Extrai linhas nominais da seção Vale de Funcionários de export markdown."""
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    empresa = str(empresa_codigo).strip()
    source_pdf = SOURCE_FILE_RE.search(text)
    source_file = source_pdf.group(1) if source_pdf else file_path.name
    period_match = PERIOD_RE.search(text)
    p_start = period_start or (_parse_br_date(period_match.group(1)) if period_match else None)
    p_end = period_end or (_parse_br_date(period_match.group(2)) if period_match else None)

    section = _extract_vale_section(text)
    items: list[NominalEvidenceItem] = []
    page_number = None
    for line in section.splitlines():
        if not line.strip().startswith("|"):
            continue
        if "---" in line or "Funcionário" in line or "TOTAL" in line.upper():
            continue
        match = TABLE_ROW_RE.match(line.strip())
        if not match:
            continue
        person = match.group(1).strip()
        if person.upper().startswith("TOTAL"):
            continue
        falta_raw = match.group(2).strip()
        vale_raw = match.group(3).strip()
        total_raw = match.group(4).strip()
        vale_amount = _parse_br_money(vale_raw)
        if vale_amount is None or vale_amount == 0:
            continue
        amount_abs = abs(vale_amount)
        falta = _parse_br_money(falta_raw)
        total = _parse_br_money(total_raw)
        raw_text = line.strip()
        items.append(
            NominalEvidenceItem(
                source=SOURCE_PRESTACAO,
                source_file=source_file,
                empresa_codigo=empresa,
                tenant_id=tenant_id or empresa,
                tenant_name=tenant_name,
                period_start=p_start,
                period_end=p_end,
                cash_register=None,
                shift=None,
                date=None,
                financial_nature=FINANCIAL_NATURE_VALE,
                capture_origin=CAPTURE_ACCOUNTABILITY,
                person_name=person,
                funcionario_codigo=None,
                amount=float(amount_abs),
                raw_amount=float(vale_amount),
                description=f"Vale mensal consolidado — Falta={falta_raw}; Total={total_raw}",
                document_reference=source_file,
                raw_text=raw_text,
                page_number=page_number,
                line_reference=f"vale_funcionario:{person}",
                extraction_confidence=0.85,
                metadata={
                    "falta_caixa": float(falta) if falta is not None else None,
                    "total_linha": float(total) if total is not None else None,
                    "granularity": "MONTHLY_EMPLOYEE_AGGREGATE",
                },
            )
        )

    meta = {
        "path": str(file_path),
        "source_file": source_file,
        "empresa_codigo": empresa,
        "period_start": p_start,
        "period_end": p_end,
        "items_extracted": len(items),
        "granularity": "MONTHLY_EMPLOYEE_AGGREGATE",
        "note": (
            "Seção Vale de Funcionários da Prestação traz totais mensais por funcionário — "
            "não lançamentos diários linha a linha."
        ),
    }
    return items, meta


def load_prestacao_nominal_items(
    *,
    empresa_codigo: str | int,
    period_start: str,
    period_end: str,
    tenant_name: str | None = None,
) -> tuple[list[NominalEvidenceItem], dict[str, Any]]:
    """Resolve fonte + extrai NominalEvidenceItems para empresa/período."""
    locate = locate_prestacao_source(
        empresa_codigo=empresa_codigo,
        period_start=period_start,
        period_end=period_end,
    )
    if not locate.get("found"):
        return [], locate

    items, extract_meta = extract_vale_funcionario_items(
        path=locate["path"],
        empresa_codigo=empresa_codigo,
        tenant_id=str(empresa_codigo),
        tenant_name=tenant_name or locate.get("tenant_name"),
        period_start=locate.get("period_start") or period_start,
        period_end=locate.get("period_end") or period_end,
    )
    locate["extraction"] = extract_meta
    locate["items_extracted"] = len(items)
    return items, locate
