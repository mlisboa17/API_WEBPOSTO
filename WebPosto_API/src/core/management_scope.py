"""Escopo gerencial autorizado para análises WebPosto."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class LicensedCompany(BaseModel):
    model_config = ConfigDict(frozen=True)

    empresa_codigo: int
    nome: str


DepartmentId = Literal["combustiveis", "conveniencia", "lubrificantes"]

LICENSED_COMPANIES = (
    LicensedCompany(empresa_codigo=11495, nome="POSTO VIP"),
    LicensedCompany(empresa_codigo=5555, nome="AP CASA CAIADA"),
    LicensedCompany(empresa_codigo=74014, nome="POSTO DOZE FILIAL II"),
)
LICENSED_COMPANY_CODES = frozenset(item.empresa_codigo for item in LICENSED_COMPANIES)
MANAGEMENT_DEPARTMENTS: tuple[DepartmentId, ...] = (
    "combustiveis",
    "conveniencia",
    "lubrificantes",
)

# Códigos confirmados em /INTEGRACAO/GRUPO nas três licenças em 17/07/2026.
WEBPOSTO_GROUP_DEPARTMENT_MAP: dict[int, DepartmentId] = {
    24554: "combustiveis",
    24555: "lubrificantes",
    24556: "lubrificantes",
    24557: "lubrificantes",
    28811: "lubrificantes",
    62009: "lubrificantes",
    166355: "lubrificantes",
    162956: "conveniencia",
    162989: "conveniencia",
    51350: "conveniencia",
    55443: "conveniencia",
    55444: "conveniencia",
    55445: "conveniencia",
    55446: "conveniencia",
    55447: "conveniencia",
    55449: "conveniencia",
    55450: "conveniencia",
    55451: "conveniencia",
    55452: "conveniencia",
    55453: "conveniencia",
    56795: "conveniencia",
}
QUARANTINED_WEBPOSTO_GROUPS: dict[int, str] = {
    25016: "COMODATO",
    26039: "DIVERSOS",
    29273: "USO E CONSUMO",
}
UNMAPPED_WEBPOSTO_GROUP_CODES = frozenset(QUARANTINED_WEBPOSTO_GROUPS)


def department_for_group(group_code: int | str | None) -> DepartmentId | None:
    try:
        return WEBPOSTO_GROUP_DEPARTMENT_MAP.get(int(group_code))
    except (TypeError, ValueError):
        return None


def is_licensed_company(empresa_codigo: int | str | None) -> bool:
    try:
        return int(empresa_codigo) in LICENSED_COMPANY_CODES
    except (TypeError, ValueError):
        return False


def quarantine_reason_for_group(group_code: int | str | None) -> str | None:
    try:
        name = QUARANTINED_WEBPOSTO_GROUPS.get(int(group_code))
    except (TypeError, ValueError):
        return None
    return f"GRUPO_AMBIGUO:{name}" if name else None
