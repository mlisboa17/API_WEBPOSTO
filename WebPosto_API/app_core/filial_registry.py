"""Onda 1 — Fonte única de filiais LOGOS SPACE (sem WebPosto live)."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.domain.entities.filial_master import FILIAIS_MASTER, FilialMaster

ROOT = Path(__file__).resolve().parents[1]
EXEC_SNAPSHOT_GLOB = ROOT / "snapshots" / "executive" / "*.json"

# Códigos homologados em snapshot executive (rede ativa observada).
SNAPSHOT_ACTIVE_CODES_FALLBACK: frozenset[int] = frozenset(
    {5256, 5333, 5555, 5556, 5557, 5559, 5560, 11495, 46433, 74014}
)

FRONTEND_UI_EXTRAS: dict[str, dict[str, str | bool]] = {
    "11495": {"nro": 1, "cidade": "OLINDA", "uf": "PE", "tipoFilial": "Posto"},
    "5555": {"nro": 2, "cidade": "OLINDA", "uf": "PE", "tipoFilial": "Posto"},
    "5256": {"nro": 3, "cidade": "OLINDA", "uf": "PE", "tipoFilial": "Posto"},
    "5333": {"nro": 4, "cidade": "PAULISTA", "uf": "PE", "tipoFilial": "Posto"},
    "5556": {"nro": 5, "cidade": "OLINDA", "uf": "PE", "tipoFilial": "Posto"},
    "5557": {"nro": 6, "cidade": "OLINDA", "uf": "PE", "tipoFilial": "Posto"},
    "5558": {"nro": 7, "cidade": "ABREU E LIMA", "uf": "PE", "tipoFilial": "Posto"},
    "5559": {"nro": 8, "cidade": "OLINDA", "uf": "PE", "tipoFilial": "Posto"},
    "5560": {"nro": 10, "cidade": "IGARASSU", "uf": "PE", "tipoFilial": "Posto"},
    "46433": {"nro": 11, "cidade": "OLINDA", "uf": "PE", "tipoFilial": "Posto"},
    "74014": {"nro": 12, "cidade": "ABREU E LIMA", "uf": "PE", "tipoFilial": "Posto"},
    "GLOBO": {"nro": 9, "cidade": "OLINDA", "uf": "PE", "tipoFilial": "Posto"},
}


def _clean_cnpj(value: str | None) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _load_snapshot_active_codes() -> frozenset[int]:
    codes: set[int] = set()
    if EXEC_SNAPSHOT_GLOB.parent.exists():
        for path in sorted(EXEC_SNAPSHOT_GLOB.parent.glob("*.json"), reverse=True):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(raw, dict):
                continue
            candidates: list[Any] = []
            data = raw.get("data")
            if isinstance(data, dict):
                candidates.extend(
                    [
                        data.get("redeAtivaEmpresaCodigos"),
                        data.get("empresaCodigosRede"),
                        (data.get("kpis") or {}).get("empresasCodigos"),
                    ]
                )
            candidates.extend(
                [
                    raw.get("redeAtivaEmpresaCodigos"),
                    raw.get("empresaCodigosRede"),
                    (raw.get("kpis") or {}).get("empresasCodigos"),
                ]
            )
            for rede in candidates:
                if isinstance(rede, list) and rede:
                    for item in rede:
                        try:
                            codes.add(int(item))
                        except (TypeError, ValueError):
                            continue
                    if codes:
                        return frozenset(codes)
    return SNAPSHOT_ACTIVE_CODES_FALLBACK


@dataclass(frozen=True)
class Filial:
    empresa_codigo: str
    cod_web: str | None
    cnpj: str | None
    nome_fantasia: str
    razao_social: str | None
    ativa: bool
    fonte: str
    status_evidencia: str
    snapshot_ativa: bool = False
    nro: int | None = None
    cidade: str | None = None
    uf: str | None = None
    tipo_filial: str | None = None
    data_encerramento: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "empresaCodigo": self.empresa_codigo,
            "codWeb": self.cod_web,
            "cnpj": self.cnpj,
            "nomeFantasia": self.nome_fantasia,
            "razaoSocial": self.razao_social,
            "ativa": self.ativa,
            "fonte": self.fonte,
            "statusEvidencia": self.status_evidencia,
            "snapshotAtiva": self.snapshot_ativa,
            "nro": self.nro,
            "cidade": self.cidade,
            "uf": self.uf,
            "tipoFilial": self.tipo_filial,
            "dataEncerramento": self.data_encerramento,
        }

    def to_manifest_row(self) -> dict[str, Any]:
        return {
            "empresaCodigo": self.empresa_codigo,
            "codWeb": self.cod_web,
            "cnpj": self.cnpj,
            "nomeFantasia": self.nome_fantasia,
            "razaoSocial": self.razao_social,
            "ativa": self.ativa,
            "fonte": self.fonte,
            "statusEvidencia": self.status_evidencia,
        }

    def to_frontend_row(self) -> dict[str, Any]:
        row = {
            "nro": self.nro,
            "codWeb": int(self.cod_web) if self.cod_web and self.cod_web.isdigit() else None,
            "razaoSocial": self.razao_social or "",
            "nomeFantasia": self.nome_fantasia,
            "cnpj": self.cnpj,
            "ativo": self.ativa,
            "cidade": self.cidade,
            "uf": self.uf,
            "tipoFilial": self.tipo_filial or "Posto",
            "status": self.status_evidencia,
            "statusEvidencia": self.status_evidencia,
            "comprovada": self.status_evidencia == "COMPROVADA",
            "origem": "app_core.filial_registry",
        }
        if self.data_encerramento:
            row["dataEncerramento"] = self.data_encerramento
        return row


def _resolve_status_evidencia(master: FilialMaster) -> str:
    if master.empresa_codigo is None or master.cod_web is None:
        return "PENDENTE_EVIDENCIA"
    if not master.cnpj or not master.nome_fantasia:
        return "PENDENTE_EVIDENCIA"
    if master.status in ("PENDENTE_IDENTIFICACAO",):
        return "PENDENTE_EVIDENCIA"
    return "COMPROVADA"


def _build_filial(master: FilialMaster, snapshot_codes: frozenset[int]) -> Filial:
    empresa_key = (
        str(master.empresa_codigo)
        if master.empresa_codigo is not None
        else f"PENDENTE_{_clean_cnpj(master.cnpj) or master.nome_fantasia.replace(' ', '_')}"
    )
    ui_key = str(master.empresa_codigo) if master.empresa_codigo is not None else "GLOBO"
    ui = FRONTEND_UI_EXTRAS.get(ui_key, {})
    cod_web = str(master.cod_web) if master.cod_web is not None else None
    status_evidencia = _resolve_status_evidencia(master)
    ativa = status_evidencia == "COMPROVADA" and master.status == "CONFIRMADA"
    snapshot_ativa = master.empresa_codigo in snapshot_codes if master.empresa_codigo else False
    return Filial(
        empresa_codigo=empresa_key,
        cod_web=cod_web,
        cnpj=master.cnpj or None,
        nome_fantasia=master.nome_fantasia,
        razao_social=master.razao_social,
        ativa=ativa,
        fonte=master.origem,
        status_evidencia=status_evidencia,
        snapshot_ativa=snapshot_ativa,
        nro=int(ui["nro"]) if ui.get("nro") is not None else None,
        cidade=str(ui["cidade"]) if ui.get("cidade") else None,
        uf=str(ui["uf"]) if ui.get("uf") else None,
        tipo_filial=str(ui["tipoFilial"]) if ui.get("tipoFilial") else None,
        data_encerramento=master.data_encerramento,
    )


@lru_cache(maxsize=1)
def _registry_rows() -> tuple[Filial, ...]:
    snapshot_codes = _load_snapshot_active_codes()
    return tuple(_build_filial(master, snapshot_codes) for master in FILIAIS_MASTER)


def list_filiais() -> list[Filial]:
    return list(_registry_rows())


def get_filial(empresa_codigo: str | int | None) -> Filial | None:
    if empresa_codigo is None:
        return None
    target = str(empresa_codigo).strip()
    for filial in _registry_rows():
        if filial.empresa_codigo == target:
            return filial
        if filial.cod_web == target:
            return filial
    return None


def is_filial_ativa(empresa_codigo: str | int | None) -> bool:
    filial = get_filial(empresa_codigo)
    return bool(filial and filial.ativa)


def get_filiais_ativas() -> list[Filial]:
    return [filial for filial in _registry_rows() if filial.ativa]


def discovery_summary() -> dict[str, Any]:
    filiais = list_filiais()
    snapshot_codes = _load_snapshot_active_codes()
    codigos = [f.empresa_codigo for f in filiais if f.empresa_codigo and not f.empresa_codigo.startswith("PENDENTE_")]
    return {
        "oficiaisMaster": len(FILIAIS_MASTER),
        "registryCount": len(filiais),
        "ativasRegistry": sum(1 for f in filiais if f.ativa),
        "snapshotAtivas": len(snapshot_codes),
        "snapshotCodes": sorted(snapshot_codes),
        "comCnpj": sum(1 for f in filiais if f.cnpj),
        "comNomeFantasia": sum(1 for f in filiais if f.nome_fantasia),
        "pendenteEvidencia": [f.nome_fantasia for f in filiais if f.status_evidencia == "PENDENTE_EVIDENCIA"],
        "codigosUnicos": len(set(codigos)) == len(codigos),
        "duplicados": len(codigos) - len(set(codigos)),
    }
