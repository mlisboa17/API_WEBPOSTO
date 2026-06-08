from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


def _clean_cnpj(value: str | None) -> str:
    return re.sub(r"\D+", "", str(value or ""))


@dataclass(frozen=True)
class FilialMaster:
    nome_fantasia: str
    razao_social: str
    cnpj: str
    cod_web: int | None
    empresa_codigo: int | None
    status: str
    origem: str = "TABELA_CORPORATIVA"
    data_encerramento: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "nomeFantasia": self.nome_fantasia,
            "razaoSocial": self.razao_social,
            "cnpj": self.cnpj,
            "codWeb": self.cod_web,
            "empresaCodigo": self.empresa_codigo,
            "status": self.status,
            "origem": self.origem,
            "dataEncerramento": self.data_encerramento,
        }


FILIAIS_MASTER: tuple[FilialMaster, ...] = (
    FilialMaster(
        nome_fantasia="POSTO VIP",
        razao_social="RIO DOCE COMERCIO E SERVICOS LTDA",
        cnpj="03.008.754/0001-86",
        cod_web=11495,
        empresa_codigo=11495,
        status="CONFIRMADA",
    ),
    FilialMaster(
        nome_fantasia="AP CASA CAIADA",
        razao_social="AUTO POSTO CASA CAIADA LTDA",
        cnpj="04.284.939/0001-86",
        cod_web=5555,
        empresa_codigo=5555,
        status="CONFIRMADA",
    ),
    FilialMaster(
        nome_fantasia="POSTO BR SHOPPING",
        razao_social="DISTRIBUIDORA RS DERIVADOS DE PETROLEO LTDA",
        cnpj="07.018.760/0001-75",
        cod_web=5256,
        empresa_codigo=5256,
        status="CONFIRMADA",
    ),
    FilialMaster(
        nome_fantasia="POSTO JANGA",
        razao_social="POSTO CIDADE PATRIMONIO LTDA",
        cnpj="05.428.059/0002-80",
        cod_web=5333,
        empresa_codigo=5333,
        status="CONFIRMADA",
    ),
    FilialMaster(
        nome_fantasia="POSTO CIDADE PATRIMONIO",
        razao_social="POSTO CIDADE PATRIMONIO LTDA",
        cnpj="05.428.059/0001-07",
        cod_web=5556,
        empresa_codigo=5556,
        status="CONFIRMADA",
    ),
    FilialMaster(
        nome_fantasia="POSTO ENSEADA DO NORTE",
        razao_social="POSTO ENSEADA DO NORTE LTDA",
        cnpj="00.338.804/0001-03",
        cod_web=5557,
        empresa_codigo=5557,
        status="CONFIRMADA",
    ),
    FilialMaster(
        nome_fantasia="POSTO REAL",
        razao_social="REAL RECIFE LTDA",
        cnpj="24.156.978/0001-05",
        cod_web=5558,
        empresa_codigo=5558,
        status="INATIVA",
        data_encerramento="2026-05-20",
    ),
    FilialMaster(
        nome_fantasia="POSTO RJ",
        razao_social="RJ COMBUSTIVEIS E LUBRIFICANTES",
        cnpj="08.726.064/0001-86",
        cod_web=5559,
        empresa_codigo=5559,
        status="CONFIRMADA",
    ),
    FilialMaster(
        nome_fantasia="POSTO SERTÃ",
        razao_social="AUTO POSTO IGARASSU LTDA",
        cnpj="04.274.378/0001-34",
        cod_web=5560,
        empresa_codigo=5560,
        status="CONFIRMADA",
    ),
    FilialMaster(
        nome_fantasia="POSTO DOZE",
        razao_social="POSTO DOZE COMERCIO DE COMBUSTIVEIS E DERIVADOS DE PETROLEO",
        cnpj="52.308.604/0001-01",
        cod_web=46433,
        empresa_codigo=46433,
        status="CONFIRMADA",
    ),
    FilialMaster(
        nome_fantasia="POSTO DOZE FILIAL II",
        razao_social="POSTO DOZE COMERCIO DE COMBUSTIVEIS E DERIVADOS DE PETROLEO",
        cnpj="52.308.604/0002-84",
        cod_web=74014,
        empresa_codigo=74014,
        status="CONFIRMADA",
    ),
    FilialMaster(
        nome_fantasia="AUTO POSTO GLOBO",
        razao_social="AUTO POSTO GLOBO LTDA",
        cnpj="41.043.647/0001-88",
        cod_web=None,
        empresa_codigo=None,
        status="PENDENTE_IDENTIFICACAO",
    ),
)


def list_filiais_master() -> list[FilialMaster]:
    return list(FILIAIS_MASTER)


def filial_name_lookup() -> dict[int, str]:
    return {
        filial.empresa_codigo: filial.nome_fantasia
        for filial in FILIAIS_MASTER
        if filial.empresa_codigo is not None
    }


def find_filial_master_by_codigo(codigo: int | None) -> FilialMaster | None:
    if codigo is None:
        return None
    for filial in FILIAIS_MASTER:
        if filial.empresa_codigo == codigo or filial.cod_web == codigo:
            return filial
    return None


def find_filial_master_by_cnpj(cnpj: str | None) -> FilialMaster | None:
    cnpj_clean = _clean_cnpj(cnpj)
    if not cnpj_clean:
        return None
    for filial in FILIAIS_MASTER:
        if _clean_cnpj(filial.cnpj) == cnpj_clean:
            return filial
    return None