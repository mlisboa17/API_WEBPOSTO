"""Modelagem de Adquirente/Bandeira/Modalidade/Taxa/Prazo para recebimento de cartão.

Objetivo: eliminar taxas e prazos hardcoded no código (ex.: DEFAULT_CARD_FEE_RATE em
src/domain/adelaide/tax_profile.py) e permitir configuração por Empresa + Adquirente +
Bandeira + Modalidade, com histórico de vigência (uma taxa pode mudar ao longo do tempo
sem perder o valor usado nas vendas antigas).

IMPORTANTE — limitação de dado confirmada em auditoria real (2026-07-21):
O cadastro `administradora_rede` do WebPosto só expõe 5 valores de `tipo`:
Crédito, Débito, PIX, Carteira Digital, Vale. Não existe "Crédito Pré-Pago" como
tipo distinto em nenhuma das 3 empresas auditadas (Vip/Casa Caiada/Doze). O endpoint
/INTEGRACAO/CARTAO (transação individual) também não traz nenhum campo de BIN ou
flag de pré-pago. Ou seja: hoje NÃO é possível identificar, a partir dos dados do
WebPosto, se uma venda de crédito foi feita com cartão pré-pago ou normal. O enum
ModalidadePagamento.CREDITO_PRE_PAGO abaixo existe para suportar a regra de negócio
(prazo D+2 úteis, taxa própria) assim que uma fonte de dado real permitir a
identificação — até lá, todo crédito à vista real classificado pelo WebPosto cai em
ModalidadePagamento.CREDITO_VISTA por padrão.

Este módulo é apenas o modelo (entidades + resolução por vigência). Persistência em
banco (Supabase/Postgres) fica para uma migration futura em supabase/migrations/,
seguindo o padrão já usado pelo módulo TMS (ver 20260709_create_tms_fleet_and_drivers.sql).
Por ora, o "repositório" é uma lista em memória (seed), o suficiente para validar a
regra sem embutir percentuais em condicionais de código.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any


class Bandeira(str, Enum):
    VISA = "VISA"
    MASTERCARD = "MASTERCARD"
    ELO = "ELO"
    HIPERCARD = "HIPERCARD"
    AMEX = "AMEX"
    MAESTRO = "MAESTRO"
    DINERS = "DINERS"


class ModalidadePagamento(str, Enum):
    DEBITO = "DEBITO"
    CREDITO_VISTA = "CREDITO_VISTA"
    CREDITO_PARCELADO = "CREDITO_PARCELADO"
    CREDITO_PRE_PAGO = "CREDITO_PRE_PAGO"
    PIX = "PIX"


class Adquirente(str, Enum):
    PAGBANK = "PAGBANK"
    REDE = "REDE"
    CIELO = "CIELO"
    STONE = "STONE"
    GETNET = "GETNET"
    SAFRAPAY = "SAFRAPAY"


@dataclass(frozen=True)
class AdquirenteBandeira:
    """Vínculo N:N — quais bandeiras cada adquirente processa."""

    adquirente: Adquirente
    bandeira: Bandeira


@dataclass(frozen=True)
class TaxaOperadora:
    """Taxa percentual vigente para (empresa, adquirente, bandeira, modalidade)."""

    empresa_codigo: int
    adquirente: Adquirente
    bandeira: Bandeira
    modalidade: ModalidadePagamento
    percentual: Decimal
    vigencia_inicio: date
    vigencia_fim: date | None = None
    parcelas: int | None = None  # None = não se aplica (débito/à vista/pix)


@dataclass(frozen=True)
class PrazoRecebimento:
    """Prazo de liquidação para (adquirente, modalidade)."""

    adquirente: Adquirente
    modalidade: ModalidadePagamento
    dias: int
    dias_uteis: bool  # False = dias corridos (ex.: PagBank D+0 inclusive fim de semana)
    inclui_fim_de_semana: bool


@dataclass
class RecebimentoCartao:
    """Instância de recebimento esperado/efetivo de uma venda de cartão."""

    empresa_codigo: int
    venda_codigo: int
    adquirente: Adquirente
    bandeira: Bandeira
    modalidade: ModalidadePagamento
    valor_bruto: Decimal
    valor_liquido: Decimal
    data_venda: date
    data_prevista_recebimento: date | None = None
    data_efetiva_recebimento: date | None = None
    taxa_aplicada: Decimal | None = None


def _d(value: str) -> Decimal:
    return Decimal(value)


# --- Seed com taxas REAIS validadas pelo usuário em 2026-07-21 (oficial PagBank) ---
# Casa Caiada (5555) e Posto Doze Filial II (74014). Origem: mensagem do usuário
# comparando com o cadastro administradora_rede real (ver /memories/repo/runtime-diagnostics.md).
PAGBANK_TAXAS_OFICIAIS: list[TaxaOperadora] = [
    # Casa Caiada (5555)
    TaxaOperadora(5555, Adquirente.PAGBANK, Bandeira.VISA, ModalidadePagamento.PIX, _d("0.50"), date(2026, 7, 21)),
    TaxaOperadora(5555, Adquirente.PAGBANK, Bandeira.VISA, ModalidadePagamento.DEBITO, _d("1.05"), date(2026, 7, 21)),
    TaxaOperadora(5555, Adquirente.PAGBANK, Bandeira.MASTERCARD, ModalidadePagamento.DEBITO, _d("1.05"), date(2026, 7, 21)),
    TaxaOperadora(5555, Adquirente.PAGBANK, Bandeira.ELO, ModalidadePagamento.DEBITO, _d("1.65"), date(2026, 7, 21)),
    TaxaOperadora(5555, Adquirente.PAGBANK, Bandeira.VISA, ModalidadePagamento.CREDITO_VISTA, _d("3.39"), date(2026, 7, 21)),
    TaxaOperadora(5555, Adquirente.PAGBANK, Bandeira.MASTERCARD, ModalidadePagamento.CREDITO_VISTA, _d("3.39"), date(2026, 7, 21)),
    TaxaOperadora(5555, Adquirente.PAGBANK, Bandeira.ELO, ModalidadePagamento.CREDITO_VISTA, _d("4.32"), date(2026, 7, 21)),
    TaxaOperadora(5555, Adquirente.PAGBANK, Bandeira.AMEX, ModalidadePagamento.CREDITO_VISTA, _d("3.19"), date(2026, 7, 21)),
    # Posto Doze Filial II (74014)
    TaxaOperadora(74014, Adquirente.PAGBANK, Bandeira.VISA, ModalidadePagamento.PIX, _d("0.20"), date(2026, 7, 21)),
    TaxaOperadora(74014, Adquirente.PAGBANK, Bandeira.VISA, ModalidadePagamento.DEBITO, _d("0.65"), date(2026, 7, 21)),
    TaxaOperadora(74014, Adquirente.PAGBANK, Bandeira.MASTERCARD, ModalidadePagamento.DEBITO, _d("0.65"), date(2026, 7, 21)),
    TaxaOperadora(74014, Adquirente.PAGBANK, Bandeira.ELO, ModalidadePagamento.DEBITO, _d("1.04"), date(2026, 7, 21)),
    TaxaOperadora(74014, Adquirente.PAGBANK, Bandeira.VISA, ModalidadePagamento.CREDITO_VISTA, _d("2.79"), date(2026, 7, 21)),
    TaxaOperadora(74014, Adquirente.PAGBANK, Bandeira.MASTERCARD, ModalidadePagamento.CREDITO_VISTA, _d("2.79"), date(2026, 7, 21)),
    TaxaOperadora(74014, Adquirente.PAGBANK, Bandeira.ELO, ModalidadePagamento.CREDITO_VISTA, _d("4.28"), date(2026, 7, 21)),
    TaxaOperadora(74014, Adquirente.PAGBANK, Bandeira.AMEX, ModalidadePagamento.CREDITO_VISTA, _d("3.19"), date(2026, 7, 21)),
]

PAGBANK_PRAZOS: list[PrazoRecebimento] = [
    PrazoRecebimento(Adquirente.PAGBANK, ModalidadePagamento.PIX, dias=0, dias_uteis=False, inclui_fim_de_semana=True),
    PrazoRecebimento(Adquirente.PAGBANK, ModalidadePagamento.DEBITO, dias=0, dias_uteis=False, inclui_fim_de_semana=True),
    PrazoRecebimento(Adquirente.PAGBANK, ModalidadePagamento.CREDITO_VISTA, dias=0, dias_uteis=False, inclui_fim_de_semana=True),
    # Regra explícita pedida pelo usuário: cartão pré-pago tem prazo próprio, D+2 úteis,
    # independente da adquirente. Só pode ser aplicada quando a venda for identificável
    # como pré-paga (hoje não é possível — ver limitação de dado no docstring do módulo).
    PrazoRecebimento(Adquirente.PAGBANK, ModalidadePagamento.CREDITO_PRE_PAGO, dias=2, dias_uteis=True, inclui_fim_de_semana=False),
]


def resolver_taxa(
    taxas: list[TaxaOperadora],
    *,
    empresa_codigo: int,
    adquirente: Adquirente,
    bandeira: Bandeira,
    modalidade: ModalidadePagamento,
    na_data: date,
) -> TaxaOperadora | None:
    """Resolve a taxa vigente em `na_data`, sem nenhum percentual fixo no código."""
    candidatas = [
        t
        for t in taxas
        if t.empresa_codigo == empresa_codigo
        and t.adquirente == adquirente
        and t.bandeira == bandeira
        and t.modalidade == modalidade
        and t.vigencia_inicio <= na_data
        and (t.vigencia_fim is None or na_data <= t.vigencia_fim)
    ]
    if not candidatas:
        return None
    return max(candidatas, key=lambda t: t.vigencia_inicio)


def resolver_prazo(
    prazos: list[PrazoRecebimento],
    *,
    adquirente: Adquirente,
    modalidade: ModalidadePagamento,
) -> PrazoRecebimento | None:
    for p in prazos:
        if p.adquirente == adquirente and p.modalidade == modalidade:
            return p
    return None


# ---------------------------------------------------------------------------
# Repositório — ordem de resolução: Supabase (se configurado) -> arquivo JSON
# local (config/acquirer_fee_model.json, persistência provisória enquanto o
# Supabase real não está configurado) -> seed em memória (último fallback).
# Ver migration supabase/migrations/20260721_create_card_acquirer_fee_model.sql.
# ---------------------------------------------------------------------------
_TAXA_SELECT = (
    "empresa_codigo,percentual,parcelas,vigencia_inicio,vigencia_fim,"
    "adquirente:adquirente_id(nome),bandeira:bandeira_id(nome),modalidade:modalidade_id(nome)"
)
_PRAZO_SELECT = (
    "dias,dias_uteis,inclui_fim_de_semana,"
    "adquirente:adquirente_id(nome),modalidade:modalidade_id(nome)"
)
_CONFIG_JSON_PATH = Path(__file__).resolve().parents[3] / "config" / "acquirer_fee_model.json"


def _parse_date(value: str | date | None) -> date | None:
    if value is None or isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _carregar_config_json() -> dict[str, list[dict[str, Any]]] | None:
    if not _CONFIG_JSON_PATH.exists():
        return None
    try:
        return json.loads(_CONFIG_JSON_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _taxas_do_json(empresa_codigo: int | None) -> list[TaxaOperadora] | None:
    config = _carregar_config_json()
    if not config:
        return None
    taxas = [
        TaxaOperadora(
            empresa_codigo=row["empresaCodigo"],
            adquirente=Adquirente(row["adquirente"]),
            bandeira=Bandeira(row["bandeira"]),
            modalidade=ModalidadePagamento(row["modalidade"]),
            percentual=Decimal(row["percentual"]),
            vigencia_inicio=_parse_date(row["vigenciaInicio"]),
            vigencia_fim=_parse_date(row.get("vigenciaFim")),
            parcelas=row.get("parcelas"),
        )
        for row in config.get("taxas", [])
        if empresa_codigo is None or row["empresaCodigo"] == empresa_codigo
    ]
    return taxas or None


def _prazos_do_json() -> list[PrazoRecebimento] | None:
    config = _carregar_config_json()
    if not config:
        return None
    prazos = [
        PrazoRecebimento(
            adquirente=Adquirente(row["adquirente"]),
            modalidade=ModalidadePagamento(row["modalidade"]),
            dias=row["dias"],
            dias_uteis=row["diasUteis"],
            inclui_fim_de_semana=row["incluiFimDeSemana"],
        )
        for row in config.get("prazos", [])
    ]
    return prazos or None


def carregar_taxas(supabase_client: Any = None, *, empresa_codigo: int | None = None) -> list[TaxaOperadora]:
    """Carrega taxas: Supabase -> config/acquirer_fee_model.json -> seed em memória."""
    if supabase_client is not None:
        try:
            query = supabase_client.table("taxa_operadora").select(_TAXA_SELECT)
            if empresa_codigo is not None:
                query = query.eq("empresa_codigo", empresa_codigo)
            rows = query.execute().data or []
            taxas = [
                TaxaOperadora(
                    empresa_codigo=row["empresa_codigo"],
                    adquirente=Adquirente(row["adquirente"]["nome"]),
                    bandeira=Bandeira(row["bandeira"]["nome"]),
                    modalidade=ModalidadePagamento(row["modalidade"]["nome"]),
                    percentual=Decimal(str(row["percentual"])),
                    vigencia_inicio=_parse_date(row["vigencia_inicio"]),
                    vigencia_fim=_parse_date(row.get("vigencia_fim")),
                    parcelas=row.get("parcelas"),
                )
                for row in rows
            ]
            if taxas:
                return taxas
        except Exception:
            pass

    return _taxas_do_json(empresa_codigo) or PAGBANK_TAXAS_OFICIAIS


def carregar_prazos(supabase_client: Any = None) -> list[PrazoRecebimento]:
    """Carrega prazos: Supabase -> config/acquirer_fee_model.json -> seed em memória."""
    if supabase_client is not None:
        try:
            rows = supabase_client.table("prazo_recebimento").select(_PRAZO_SELECT).execute().data or []
            prazos = [
                PrazoRecebimento(
                    adquirente=Adquirente(row["adquirente"]["nome"]),
                    modalidade=ModalidadePagamento(row["modalidade"]["nome"]),
                    dias=row["dias"],
                    dias_uteis=row["dias_uteis"],
                    inclui_fim_de_semana=row["inclui_fim_de_semana"],
                )
                for row in rows
            ]
            if prazos:
                return prazos
        except Exception:
            pass

    return _prazos_do_json() or PAGBANK_PRAZOS
