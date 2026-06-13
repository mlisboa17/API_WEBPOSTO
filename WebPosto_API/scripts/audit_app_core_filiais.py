#!/usr/bin/env python3
"""Onda 1 — QA gate app_core filiais registry."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app_core.filial_registry import discovery_summary, get_filiais_ativas, list_filiais

MANIFEST = ROOT / "frontend" / "data" / "filiais.json"
ALLOWED_STATUS = frozenset({"COMPROVADA", "PENDENTE_EVIDENCIA"})
MANIFEST_FIELDS = frozenset(
    {
        "empresaCodigo",
        "codWeb",
        "cnpj",
        "nomeFantasia",
        "razaoSocial",
        "ativa",
        "fonte",
        "statusEvidencia",
    }
)


def main() -> None:
    filiais = list_filiais()
    summary = discovery_summary()
    errors: list[str] = []

    if not MANIFEST.exists():
        errors.append("manifest ausente — execute sync_filiais_manifest.py")
    else:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        if manifest.get("count") != len(filiais):
            errors.append("manifest desatualizado (count diverge)")
        if manifest.get("activeCount") != len(get_filiais_ativas()):
            errors.append("manifest activeCount diverge do registry")
        if len(manifest.get("filiais") or []) != len(filiais):
            errors.append("manifest filiais length diverge")
        for row in manifest.get("filiais") or []:
            if set(row.keys()) != MANIFEST_FIELDS:
                errors.append(f"manifest row campos invalidos: {row.get('empresaCodigo')}")
            if row.get("statusEvidencia") not in ALLOWED_STATUS:
                errors.append(f"statusEvidencia invalido: {row.get('empresaCodigo')}")
            if row.get("statusEvidencia") == "PENDENTE_EVIDENCIA" and row.get("ativa") is True:
                errors.append(f"PENDENTE_EVIDENCIA tratada como ativa: {row.get('empresaCodigo')}")

    codigos = [
        f.empresa_codigo
        for f in filiais
        if f.empresa_codigo and not str(f.empresa_codigo).startswith("PENDENTE_")
    ]
    if len(codigos) != len(set(codigos)):
        errors.append("codigo duplicado detectado")

    if summary["duplicados"] > 0:
        errors.append("duplicidade no master")

    pendente_ativa = [f.empresa_codigo for f in filiais if f.status_evidencia == "PENDENTE_EVIDENCIA" and f.ativa]
    if pendente_ativa:
        errors.append(f"PENDENTE_EVIDENCIA com ativa=true: {pendente_ativa}")

    print("APP_CORE FILIAIS QA")
    print(f"  oficiais: {summary['oficiaisMaster']}")
    print(f"  ativas registry: {summary['ativasRegistry']}")
    print(f"  snapshot ativas: {summary['snapshotAtivas']}")
    print(f"  pendente evidencia: {summary['pendenteEvidencia']}")
    print(f"  erros: {len(errors)}")

    if errors:
        for err in errors:
            print(f"  - {err}")
        raise SystemExit(1)

    print("[PARECER FINAL: ONDA 1 APP_CORE FILIAIS APROVADA]")


if __name__ == "__main__":
    main()
