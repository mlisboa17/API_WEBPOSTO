"""Camada de pista — contrato REST v1 (Quality Automação / LOGOS).

Expõe DTOs canônicos:
  - PENDENTE: sem Cupom Fiscal, sem Hora Fiscal e sem Abast.×Venda (UI WebPosto);
    na INTEGRACAO também: vendaItemCodigo vazio/zero
  - BAIXADO: faturado/liquidado (com venda, fiscal e forma de pagamento)

Fonte física Quality (INTEGRACAO):
  GET /INTEGRACAO/CONSULTAR_ABASTECIMENTO_REDE  (preferencial)
  GET /INTEGRACAO/ABASTECIMENTO                 (fallback)

Os paths públicos LOGOS (`/api/v1/abastecimentos/pendentes|baixados`)
normalizam o payload INTEGRACAO para o schema REST v1.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.domain.adelaide.fuel_catalog import rotulo_combustivel
from src.gateway.shared_client import get_webposto_client

LOGGER = logging.getLogger(__name__)

FILIAIS = {
    5555: "AP CASA CAIADA",
    11495: "POSTO VIP",
    74014: "POSTO REAL / DOZE",
}

StatusPista = Literal["PENDENTE", "BAIXADO"]

FONTE = "AbastecimentoRede"
ENDPOINT_REDE = "/INTEGRACAO/CONSULTAR_ABASTECIMENTO_REDE"
ENDPOINT_FALLBACK = "/INTEGRACAO/ABASTECIMENTO"
MAX_PAGES = 40


class AbastecimentoRestV1(BaseModel):
    """DTO oficial REST v1 — abastecimento de pista."""

    idAbastecimento: int
    uuid: str
    dataHora: str
    bico: int
    tanque: int | None = None
    idProduto: int | None = None
    descricaoProduto: str = "Combustível"
    litros: float = 0.0
    precoUnitario: float = 0.0
    valorTotal: float = 0.0
    idFrentista: int | None = None
    nomeFrentista: str = "N/I"
    status: StatusPista = "BAIXADO"
    reservado: bool = False
    idEmpresa: int = 0
    nomeEmpresa: str = ""
    # Extras baixados
    idVenda: int | None = None
    documentoFiscal: str | None = None
    chaveAcesso: str | None = None
    formaPagamento: str | None = None
    cliente: str | None = None
    dataHoraBaixa: str | None = None
    # TEF / CARTAO (JOIN VENDA_FORMA_PAGAMENTO + CARTAO por vendaCodigo)
    cartaoBandeira: str | None = None
    cartaoFinal: str | None = None
    cartaoNsu: str | None = None
    cartaoAutorizacao: str | None = None
    isEspecie: bool = False
    precoTabela: float | None = None
    valorDesconto: float = 0.0
    origemDesconto: str | None = None
    cpfCliente: str | None = None
    bomba: int | None = None


class FilialDiaResumo(BaseModel):
    """Totais reais do dia por filial (independente do subset do feed)."""

    idEmpresa: int
    nomeEmpresa: str = ""
    totalAbastecimentos: int = 0
    totalLitros: float = 0.0
    totalValor: float = 0.0
    totalPendentes: int = 0
    totalBaixados: int = 0


class ResumoDiaPista(BaseModel):
    """Agregação completa do dia — fonte dos KPIs do Cockpit."""

    totalAbastecimentos: int = 0
    totalLitros: float = 0.0
    totalValor: float = 0.0
    totalPendentes: int = 0
    totalBaixados: int = 0
    porFilial: list[FilialDiaResumo] = Field(default_factory=list)


class TotaisDiaPista(BaseModel):
    """Totais acumulados do dia (universo completo — ERR-01)."""

    faturamentoTotal: float = 0.0
    volumetriaTotalLitros: float = 0.0
    qtdTotalAbastecimentos: int = 0
    # KPIs executivos (Cockpit top cards)
    pvmMedio: float = 0.0  # R$/L = faturamento / litros
    valorCartoesDia: float = 0.0  # soma Cartão/TEF/Crédito/Débito do dia
    qtdCartoesDia: int = 0
    alertasCriticosRetencao: int = 0  # retenção cartão > 30 min (mesma regra anti-fraude)
    valorCriticoRetencao: float = 0.0


class ListaAbastecimentosResponse(BaseModel):
    success: bool = True
    synthetic: bool = False
    fonte: str = FONTE
    endpoint: str = ENDPOINT_REDE
    status: StatusPista | str = "TODOS"
    total: int = 0
    pagina: int = 1
    limite: int = 100
    items: list[AbastecimentoRestV1] = Field(default_factory=list)
    resumoDia: ResumoDiaPista | None = None
    totaisDia: TotaisDiaPista | None = None
    ultimaSincronizacaoIso: str | None = None
    totalRealDia: int | None = None
    volumetriaTotalDia: float | None = None
    fromCache: bool = False
    observacoes: list[str] = Field(default_factory=list)
    error: str | None = None


_CARD_KEYWORDS = (
    "CARTAO",
    "CARTÃO",
    "CREDITO",
    "CRÉDITO",
    "DEBITO",
    "DÉBITO",
    "TEF",
    "POS",
    "VISA",
    "MASTER",
    "ELO",
    "HIPER",
    "AMEX",
)
_CRITICAL_RETENTION_MIN = 30.0


def _is_pagamento_cartao(forma: str | None) -> bool:
    text = (forma or "").upper()
    return any(k in text for k in _CARD_KEYWORDS)


_DINHEIRO_KEYWORDS = (
    "DINHEIRO",
    "ESPECIE",
    "ESPÉCIE",
    "CASH",
    "NUMERARIO",
    "NUMERÁRIO",
)


def _is_especie(forma: str | None) -> bool:
    text = (forma or "").upper()
    return bool(text) and any(k in text for k in _DINHEIRO_KEYWORDS)


def _bandeira_from_admin_desc(desc: str | None) -> str:
    """Extrai bandeira de adiministradoraDescricao (ex: 'VISA CREDITO PAGSEGURO')."""
    upper = (desc or "").upper()
    for name, label in (
        ("MASTERCARD", "Mastercard"),
        ("MASTER", "Mastercard"),
        ("MAESTRO", "Maestro"),
        ("VISA", "Visa"),
        ("ELO", "Elo"),
        ("HIPER", "Hipercard"),
        ("AMEX", "Amex"),
        ("PREMMIA", "Premmia"),
    ):
        if name in upper:
            return label
    # primeiro token útil
    token = (desc or "").strip().split(" ")[0] if desc else ""
    return token.title() if token and token.upper() not in ("CARTAO", "CARTÃO", "TEF") else ""


def _final_from_cartao_row(row: dict[str, Any]) -> str:
    for key in (
        "finalCartao",
        "cartaoFinal",
        "ultimosDigitos",
        "numeroCartao",
        "cartaoNumero",
    ):
        raw = str(row.get(key) or "").strip()
        digits = "".join(ch for ch in raw if ch.isdigit())
        if len(digits) >= 4:
            return digits[-4:]
    # Fallback: últimos 4 do NSU numérico (ignora UUID/opaque da Quality)
    nsu = str(row.get("nsu") or row.get("nsuTef") or "").strip()
    if "-" in nsu or any(c.isalpha() for c in nsu):
        return ""
    nsu_digits = "".join(ch for ch in nsu if ch.isdigit())
    if len(nsu_digits) >= 4:
        return nsu_digits[-4:]
    return ""


def _retention_minutes(item: AbastecimentoRestV1) -> float | None:
    if not item.dataHora or not item.dataHoraBaixa:
        return None
    start = _parse_iso(item.dataHora)
    end = _parse_iso(item.dataHoraBaixa)
    if not start or not end:
        return None
    delta = (end - start).total_seconds() / 60.0
    return delta if delta >= 0 else None


def totais_from_resumo(
    resumo: ResumoDiaPista | None,
    baixados: list[AbastecimentoRestV1] | tuple[AbastecimentoRestV1, ...] | None = None,
) -> TotaisDiaPista:
    r = resumo or ResumoDiaPista()
    litros = float(r.totalLitros or 0.0)
    fat = float(r.totalValor or 0.0)
    pvm = round(fat / litros, 4) if litros > 0 else 0.0

    valor_cartoes = 0.0
    qtd_cartoes = 0
    alertas_criticos = 0
    valor_critico = 0.0
    for item in baixados or []:
        if not _is_pagamento_cartao(item.formaPagamento):
            continue
        valor_cartoes += float(item.valorTotal or 0.0)
        qtd_cartoes += 1
        mins = _retention_minutes(item)
        if mins is not None and mins > _CRITICAL_RETENTION_MIN:
            alertas_criticos += 1
            valor_critico += float(item.valorTotal or 0.0)

    return TotaisDiaPista(
        faturamentoTotal=round(fat, 2),
        volumetriaTotalLitros=round(litros, 3),
        qtdTotalAbastecimentos=int(r.totalAbastecimentos),
        pvmMedio=pvm,
        valorCartoesDia=round(valor_cartoes, 2),
        qtdCartoesDia=qtd_cartoes,
        alertasCriticosRetencao=alertas_criticos,
        valorCriticoRetencao=round(valor_critico, 2),
    )


def _build_resumo_dia(
    items: list[AbastecimentoRestV1],
    pendentes_extra: list[AbastecimentoRestV1] | None = None,
) -> ResumoDiaPista:
    """Soma litros/valor/contagens sobre o universo completo (não o page slice)."""
    all_items = list(items)
    if pendentes_extra:
        seen = {(i.idEmpresa, i.idAbastecimento) for i in all_items}
        for p in pendentes_extra:
            key = (p.idEmpresa, p.idAbastecimento)
            if key not in seen:
                all_items.append(p)
                seen.add(key)

    by_emp: dict[int, list[AbastecimentoRestV1]] = {}
    for item in all_items:
        by_emp.setdefault(item.idEmpresa, []).append(item)

    por_filial: list[FilialDiaResumo] = []
    for emp in sorted(by_emp.keys()):
        rows = by_emp[emp]
        pend = sum(1 for r in rows if r.status == "PENDENTE")
        baix = sum(1 for r in rows if r.status == "BAIXADO")
        litros = round(sum(r.litros for r in rows), 3)
        valor = round(sum(r.valorTotal for r in rows), 2)
        por_filial.append(
            FilialDiaResumo(
                idEmpresa=emp,
                nomeEmpresa=rows[0].nomeEmpresa or FILIAIS.get(emp, f"Empresa {emp}"),
                totalAbastecimentos=len(rows),
                totalLitros=litros,
                totalValor=valor,
                totalPendentes=pend,
                totalBaixados=baix,
            )
        )

    return ResumoDiaPista(
        totalAbastecimentos=len(all_items),
        totalLitros=round(sum(f.totalLitros for f in por_filial), 3),
        totalValor=round(sum(f.totalValor for f in por_filial), 2),
        totalPendentes=sum(f.totalPendentes for f in por_filial),
        totalBaixados=sum(f.totalBaixados for f in por_filial),
        porFilial=por_filial,
    )


def _rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        for key in ("resultados", "dados", "data", "items"):
            val = data.get(key)
            if isinstance(val, list):
                return [r for r in val if isinstance(r, dict)]
    return []


def _parse_iso(raw: Any) -> datetime | None:
    if not raw:
        return None
    text = str(raw).strip()
    if text.endswith("Z"):
        text = text[:-1]
    if len(text) >= 6 and text[-6] in "+-" and text[-3] == ":":
        text = text[:-6]
    text = text.replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:26], fmt)
        except ValueError:
            continue
    return None


def _fmt_dt(dt: datetime | None) -> str:
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def _bico_numero(row: dict[str, Any]) -> int:
    sf = str(row.get("stringFull") or "")
    if sf:
        parts = sf.split(";")
        if len(parts) > 1:
            try:
                n = int(str(parts[1]).strip())
                if 1 <= n <= 99:
                    return n
            except (TypeError, ValueError):
                pass
    try:
        code = int(row.get("codigoBico") or row.get("bico") or row.get("numeroBico") or 0)
    except (TypeError, ValueError):
        return 0
    return code


def _campo_preenchido(val: Any) -> bool:
    """True se o campo existe e não é vazio/zero (regra visual WebPosto)."""
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val != 0
    if isinstance(val, dict):
        # horaFiscal Quality às vezes vem {hour, minute, second}
        try:
            return any(int(val.get(k) or 0) for k in ("hour", "minute", "second", "hora", "minuto"))
        except (TypeError, ValueError):
            return bool(val)
    text = str(val).strip()
    if not text or text in ("0", "00:00:00", "0000-00-00", "null", "None"):
        return False
    return True


def _tem_cupom_fiscal(row: dict[str, Any]) -> bool:
    return any(
        _campo_preenchido(row.get(k))
        for k in (
            "cupom",
            "cupomFiscal",
            "numeroCupom",
            "notaNumero",
            "numeroNota",
            "documentoFiscal",
            "coo",
            "numeroCoo",
        )
    )


def _tem_hora_fiscal(row: dict[str, Any]) -> bool:
    return _campo_preenchido(row.get("horaFiscal")) or (
        _campo_preenchido(row.get("dataFiscal")) and _campo_preenchido(row.get("horaFiscal"))
    ) or _campo_preenchido(row.get("dataHoraFiscal"))


def _tem_abast_x_venda(row: dict[str, Any]) -> bool:
    """Coluna 'Abast. x Venda' do WebPosto — tempo entre bomba e baixa."""
    return any(
        _campo_preenchido(row.get(k))
        for k in (
            "abastXVenda",
            "abastecimentoXVenda",
            "tempoAbastVenda",
            "tempoAbastecimentoVenda",
            "tempoBaixa",
            "intervaloAbastecimentoVenda",
            "diferencaAbastecimentoVenda",
        )
    )


def _venda_item_codigo(row: dict[str, Any]) -> int:
    try:
        return int(row.get("vendaItemCodigo") or 0)
    except (TypeError, ValueError):
        return 0


def _is_pendente_raw(row: dict[str, Any]) -> bool:
    """Pendente — contrato AbastecimentoRede + regra visual WebPosto.

    Primário (schema RetornoPaginadoAbastecimentoRede):
      vendaItemCodigo == 0  → pendente (ainda sem vínculo de venda)
      vendaItemCodigo  > 0  → baixado/emitido

    Reforço visual (tela desktop):
      sem dataFiscal/horaFiscal (e sem cupom / Abast.×Venda) → pendente
    """
    if row.get("status") in ("PENDENTE", "Pendente", "pendente"):
        return True
    if row.get("baixado") in (False, "N", "n", 0, "0"):
        return True

    vic = _venda_item_codigo(row)
    # Contrato oficial AbastecimentoRede
    if vic > 0:
        return False
    if vic <= 0 and not (
        _tem_cupom_fiscal(row) or _tem_hora_fiscal(row) or _tem_abast_x_venda(row)
    ):
        return True

    # vic==0 mas veio algum vestígio fiscal inconsistente → ainda pendente
    return True


def _uuid_for(emp: int, ab_id: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"webposto:{emp}:{ab_id}"))


def _data_hora_baixa(row: dict[str, Any]) -> str | None:
    data = str(row.get("dataFiscal") or "")[:10]
    hora_raw = row.get("horaFiscal")
    if isinstance(hora_raw, dict):
        try:
            hora = (
                f"{int(hora_raw.get('hour') or 0):02d}:"
                f"{int(hora_raw.get('minute') or 0):02d}:"
                f"{int(hora_raw.get('second') or 0):02d}"
            )
        except (TypeError, ValueError):
            hora = ""
    else:
        hora = str(hora_raw or "").strip()
    if data and hora:
        return f"{data}T{hora[:8]}"
    # fallback: dataHoraAbastecimento se já baixado
    dt = _parse_iso(row.get("dataHoraAbastecimento"))
    return _fmt_dt(dt) if dt else None


class WebPostoPistaService:
    """Serviço de pista com mapeamento REST v1 sobre INTEGRACAO Quality."""

    def __init__(self) -> None:
        self.client = get_webposto_client()

    async def listar_pendentes(
        self,
        id_empresa: int | None = None,
        id_bico: int | None = None,
    ) -> ListaAbastecimentosResponse:
        """Pendentes = AbastecimentoRede com vendaItemCodigo == 0 (modo Todos + filtro local)."""
        hoje = str(date.today())
        try:
            pendentes, _baix, _resumo, observacoes, err = await self.coletar_pista_universo(
                id_empresa=id_empresa,
                data_inicio=hoje,
                data_fim=hoje,
            )
            items = pendentes
            if id_bico is not None:
                items = [i for i in items if i.bico == int(id_bico)]
            if err and not items:
                return ListaAbastecimentosResponse(
                    success=False,
                    status="PENDENTE",
                    error=err,
                    observacoes=observacoes or [err],
                )
            if not items:
                observacoes = list(observacoes or []) + [
                    "Nenhum pendente na INTEGRACAO (AbastecimentoRede: vendaItemCodigo==0 "
                    "e sem dataFiscal/horaFiscal). A tela desktop pode listar PDV local "
                    "que a API cloud ainda não publica."
                ]
            return ListaAbastecimentosResponse(
                success=True,
                synthetic=False,
                fonte=FONTE,
                endpoint=ENDPOINT_REDE,
                status="PENDENTE",
                total=len(items),
                items=items,
                observacoes=observacoes,
            )
        except Exception as exc:
            LOGGER.exception("pista.listar_pendentes falhou: %s", exc)
            return ListaAbastecimentosResponse(
                success=False,
                status="PENDENTE",
                error=str(exc),
                observacoes=[str(exc)],
            )

    async def coletar_pista_universo(
        self,
        id_empresa: int | None = None,
        data_inicio: str | None = None,
        data_fim: str | None = None,
    ) -> tuple[
        list[AbastecimentoRestV1],
        list[AbastecimentoRestV1],
        ResumoDiaPista,
        list[str],
        str | None,
    ]:
        """Uma passagem 'Todos' (como a tela WebPosto) → split pendentes/baixados.

        Pendente: vendaItemCodigo == 0 (contrato AbastecimentoRede).
        Baixado:  vendaItemCodigo  > 0 (+ enriquecimento VENDA/NFCE).
        """
        hoje = str(date.today())
        start = data_inicio or hoje
        end = data_fim or hoje
        observacoes: list[str] = []
        try:
            (
                raw,
                frentistas,
                venda_items,
                pagamentos,
                vendas,
                nfces,
                cartoes,
            ) = await asyncio.gather(
                # Sem filtro status — equivalente ao radio "Todos" da tela
                self._fetch_abastecimentos(start, end, id_empresa, prefer_pendentes=False),
                self._fetch_frentistas(),
                self._fetch_endpoint("venda_item", start, end, id_empresa),
                self._fetch_endpoint("venda_forma_pagamento", start, end, id_empresa),
                self._fetch_endpoint("venda", start, end, id_empresa),
                self._fetch_endpoint("nfce", start, end, id_empresa),
                # TEF detalhado: bandeira / NSU / autorização (JOIN por vendaCodigo)
                self._fetch_endpoint("cartao", start, end, id_empresa),
            )

            vi_map = self._index_venda_items(venda_items)
            pag_map = self._index_pagamentos(pagamentos)
            venda_map = self._index_vendas(vendas)
            nfce_map = self._index_nfce(nfces)
            cartao_map = self._index_cartoes(cartoes)

            pendentes: list[AbastecimentoRestV1] = []
            baixados: list[AbastecimentoRestV1] = []
            qtd_vic_zero = 0

            for row in raw:
                if bool(row.get("afericao")):
                    continue
                if id_empresa is not None:
                    try:
                        if int(row.get("empresaCodigo") or 0) != int(id_empresa):
                            continue
                    except (TypeError, ValueError):
                        continue

                if _is_pendente_raw(row):
                    qtd_vic_zero += 1
                    dto = self._map_row(row, frentistas, status_force="PENDENTE")
                    if dto:
                        pendentes.append(dto)
                    continue

                dto = self._map_row(row, frentistas, status_force="BAIXADO")
                if not dto:
                    continue

                vic = _venda_item_codigo(row)
                vc = vi_map.get(vic) or 0
                emp = dto.idEmpresa
                if vc:
                    dto.idVenda = vc
                    v = venda_map.get((emp, vc)) or venda_map.get((0, vc))
                    if v:
                        dto.cliente = str(
                            v.get("clienteNome")
                            or v.get("nomeCliente")
                            or v.get("razaoSocial")
                            or ""
                        ).strip() or None
                        dto.documentoFiscal = str(
                            v.get("notaNumero") or v.get("numeroNota") or ""
                        ).strip() or None
                        dto.chaveAcesso = str(
                            v.get("notaChave") or v.get("chaveAcesso") or ""
                        ).strip() or None
                    nf = nfce_map.get((emp, vc)) or nfce_map.get((0, vc))
                    if nf:
                        dto.documentoFiscal = dto.documentoFiscal or str(
                            nf.get("numero") or nf.get("notaNumero") or ""
                        ).strip() or None
                        dto.chaveAcesso = dto.chaveAcesso or str(
                            nf.get("chaveAcesso") or nf.get("chave") or ""
                        ).strip() or None
                    pags = pag_map.get((emp, vc)) or pag_map.get((0, vc)) or []
                    if pags:
                        # Prefere forma com nome mais descritivo (evita vazio/genérico)
                        best_pag = max(
                            pags,
                            key=lambda p: len(
                                str(
                                    p.get("nomeFormaPagamento")
                                    or p.get("formaPagamento")
                                    or ""
                                ).strip()
                            ),
                        )
                        dto.formaPagamento = str(
                            best_pag.get("nomeFormaPagamento")
                            or best_pag.get("formaPagamento")
                            or ""
                        ).strip() or None
                    dto.isEspecie = _is_especie(dto.formaPagamento)

                    # JOIN CARTAO (TEF) — bandeira / final / NSU / autorização
                    card = cartao_map.get((emp, vc)) or cartao_map.get((0, vc))
                    if card:
                        admin_desc = str(
                            card.get("adiministradoraDescricao")
                            or card.get("administradoraDescricao")
                            or ""
                        ).strip()
                        dto.cartaoBandeira = _bandeira_from_admin_desc(admin_desc) or None
                        dto.cartaoNsu = str(card.get("nsu") or card.get("nsuTef") or "").strip() or None
                        dto.cartaoAutorizacao = str(card.get("autorizacao") or "").strip() or None
                        dto.cartaoFinal = _final_from_cartao_row(card) or None
                        cpf_raw = str(card.get("clienteCpfCnpj") or "").strip()
                        cpf_digits = "".join(ch for ch in cpf_raw if ch.isdigit())
                        if cpf_digits and set(cpf_digits) != {"0"}:
                            dto.cpfCliente = cpf_raw
                        # Se forma genérica (CARTAO POS), enriquece com bandeira+crédito/débito
                        if dto.formaPagamento and "CARTAO" in dto.formaPagamento.upper():
                            kind = "Crédito" if "CREDITO" in admin_desc.upper() or "CRÉDITO" in admin_desc.upper() else (
                                "Débito" if "DEBITO" in admin_desc.upper() or "DÉBITO" in admin_desc.upper() or "MAESTRO" in admin_desc.upper() else ""
                            )
                            if dto.cartaoBandeira and kind:
                                dto.formaPagamento = f"Cartão {kind}"
                            elif dto.cartaoBandeira:
                                dto.formaPagamento = f"Cartão {dto.cartaoBandeira}"
                        elif not dto.formaPagamento and dto.cartaoBandeira:
                            dto.formaPagamento = f"Cartão {dto.cartaoBandeira}"

                    # Fallbacks sem linha CARTAO: PIX / bandeira embutida na forma
                    forma_u = (dto.formaPagamento or "").upper()
                    if "PIX" in forma_u and not dto.cartaoBandeira:
                        dto.cartaoBandeira = "PIX"
                    elif not dto.cartaoBandeira and dto.formaPagamento:
                        parsed = _bandeira_from_admin_desc(dto.formaPagamento)
                        if parsed:
                            dto.cartaoBandeira = parsed

                    dto.dataHoraBaixa = _data_hora_baixa(row)
                baixados.append(dto)

            pendentes.sort(key=lambda x: x.dataHora or "", reverse=True)
            baixados.sort(key=lambda x: x.dataHora or "", reverse=True)
            # resumo base = só baixados; o cache mescla pendentes em _publish
            resumo = _build_resumo_dia(baixados)

            LOGGER.info(
                "pista.universo periodo=%s..%s raw=%s pendentes=%s (vic0=%s) baixados=%s",
                start,
                end,
                len(raw),
                len(pendentes),
                qtd_vic_zero,
                len(baixados),
            )
            if not pendentes and baixados:
                observacoes.append(
                    f"Universo INTEGRACAO: {len(baixados)} baixados (vendaItemCodigo>0); "
                    "0 pendentes (vendaItemCodigo==0) — se a tela desktop mostra pendentes, "
                    "eles ainda não saíram do PDV local para a API."
                )
            return pendentes, baixados, resumo, observacoes, None
        except Exception as exc:
            LOGGER.exception("pista.coletar_pista_universo falhou: %s", exc)
            return [], [], ResumoDiaPista(), [str(exc)], str(exc)

    async def coletar_baixados_universo(
        self,
        id_empresa: int | None = None,
        data_inicio: str | None = None,
        data_fim: str | None = None,
    ) -> tuple[list[AbastecimentoRestV1], ResumoDiaPista, list[str], str | None]:
        """Baixados do dia — reutiliza split do universo (Todos)."""
        _pend, baixados, resumo, observacoes, err = await self.coletar_pista_universo(
            id_empresa=id_empresa,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        # resumo dos baixados sem inflar com pendentes (KPIs de faturamento = baixados)
        resumo_baix = _build_resumo_dia(baixados)
        return baixados, resumo_baix, observacoes, err

    async def listar_baixados(
        self,
        id_empresa: int | None = None,
        data_inicio: str | None = None,
        data_fim: str | None = None,
        pagina: int = 1,
        limite: int = 100,
    ) -> ListaAbastecimentosResponse:
        pagina = max(1, int(pagina or 1))
        limite = max(1, min(500, int(limite or 100)))
        items, resumo, observacoes, error = await self.coletar_baixados_universo(
            id_empresa=id_empresa,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        if error:
            return ListaAbastecimentosResponse(
                success=False,
                status="BAIXADO",
                error=error,
                observacoes=observacoes or [error],
            )
        offset = (pagina - 1) * limite
        totais = totais_from_resumo(resumo, items)
        return ListaAbastecimentosResponse(
            success=True,
            synthetic=False,
            fonte=FONTE,
            endpoint=ENDPOINT_REDE,
            status="BAIXADO",
            total=len(items),
            pagina=pagina,
            limite=limite,
            items=items[offset : offset + limite],
            resumoDia=resumo,
            totaisDia=totais,
            totalRealDia=totais.qtdTotalAbastecimentos,
            volumetriaTotalDia=totais.volumetriaTotalLitros,
            observacoes=observacoes,
        )

    async def feed_vivo(
        self,
        id_empresa: int | None = None,
        data_inicio: str | None = None,
        data_fim: str | None = None,
        limite_baixados: int = 80,
    ) -> ListaAbastecimentosResponse:
        """Mescla pendentes + últimos baixados para o Cockpit 30s.

        KPIs usam `resumoDia` (universo completo do dia). `items` é só o feed visual.
        """
        pend, baix = await asyncio.gather(
            self.listar_pendentes(id_empresa=id_empresa),
            self.listar_baixados(
                id_empresa=id_empresa,
                data_inicio=data_inicio,
                data_fim=data_fim,
                pagina=1,
                limite=limite_baixados,
            ),
        )
        merged = list(pend.items) + list(baix.items)
        # dedupe por idAbastecimento+empresa (pendente prevalece)
        seen: set[tuple[int, int]] = set()
        unique: list[AbastecimentoRestV1] = []
        for item in sorted(merged, key=lambda x: x.dataHora or "", reverse=True):
            key = (item.idEmpresa, item.idAbastecimento)
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)

        # resumoDia: totais reais do dia (baixados completos + pendentes API)
        resumo = baix.resumoDia or ResumoDiaPista()
        if pend.items:
            resumo = self._merge_pendentes_resumo(resumo, pend.items)

        obs = list(pend.observacoes) + list(baix.observacoes)
        return ListaAbastecimentosResponse(
            success=pend.success or baix.success,
            synthetic=False,
            fonte=FONTE,
            endpoint=f"{ENDPOINT_REDE}+baixados",
            status="MISTO",
            total=resumo.totalAbastecimentos,
            limite=limite_baixados,
            items=unique,
            resumoDia=resumo,
            observacoes=obs,
            error=pend.error or baix.error,
        )

    @staticmethod
    def _merge_pendentes_resumo(
        resumo: ResumoDiaPista,
        pendentes: list[AbastecimentoRestV1],
    ) -> ResumoDiaPista:
        por = {f.idEmpresa: f.model_copy() for f in resumo.porFilial}
        for p in pendentes:
            f = por.get(p.idEmpresa)
            if not f:
                f = FilialDiaResumo(
                    idEmpresa=p.idEmpresa,
                    nomeEmpresa=p.nomeEmpresa or FILIAIS.get(p.idEmpresa, f"Empresa {p.idEmpresa}"),
                )
                por[p.idEmpresa] = f
            f.totalPendentes += 1
            f.totalAbastecimentos += 1
            f.totalLitros = round(f.totalLitros + (p.litros or 0), 3)
            f.totalValor = round(f.totalValor + (p.valorTotal or 0), 2)
        por_filial = sorted(por.values(), key=lambda x: x.idEmpresa)
        return ResumoDiaPista(
            totalAbastecimentos=sum(f.totalAbastecimentos for f in por_filial),
            totalLitros=round(sum(f.totalLitros for f in por_filial), 3),
            totalValor=round(sum(f.totalValor for f in por_filial), 2),
            totalPendentes=sum(f.totalPendentes for f in por_filial),
            totalBaixados=sum(f.totalBaixados for f in por_filial),
            porFilial=por_filial,
        )

    def _map_row(
        self,
        row: dict[str, Any],
        frentistas: dict[int, str],
        status_force: StatusPista | None = None,
    ) -> AbastecimentoRestV1 | None:
        emp = int(row.get("empresaCodigo") or row.get("idEmpresa") or 0)
        if not emp:
            return None

        ab_id = int(
            row.get("abastecimentoCodigo")
            or row.get("idAbastecimento")
            or row.get("codigo")
            or 0
        )
        if not ab_id:
            return None

        litros = float(row.get("quantidade") or row.get("litros") or 0)
        valor = float(row.get("valorTotal") or row.get("valor") or 0)
        if litros <= 0 and valor <= 0:
            return None

        prod_cod_raw = row.get("codigoProduto") or row.get("idProduto") or row.get("produtoCodigo")
        try:
            id_produto = int(prod_cod_raw) if prod_cod_raw not in (None, "") else None
        except (TypeError, ValueError):
            id_produto = None

        prod_cod = str(prod_cod_raw or "")
        descricao = (
            str(row.get("descricaoProduto") or "").strip()
            or (rotulo_combustivel(prod_cod) if prod_cod else "Combustível")
        )
        if descricao in ("Combustível", "—") and prod_cod:
            descricao = f"Produto {prod_cod}"

        fid_raw = row.get("codigoFrentista") or row.get("idFrentista") or row.get("frentistaCodigo")
        try:
            fid = int(fid_raw) if fid_raw not in (None, "", 0, "0") else None
        except (TypeError, ValueError):
            fid = None

        nome = (
            str(row.get("nomeFrentista") or "").strip()
            or (frentistas.get(fid) if fid else None)
            or (f"Frentista {fid}" if fid else "N/I")
        )

        dt = _parse_iso(row.get("dataHora") or row.get("dataHoraAbastecimento"))
        data_hora = _fmt_dt(dt) or str(row.get("dataHoraAbastecimento") or "")[:19]

        status: StatusPista = status_force or (
            "PENDENTE" if _is_pendente_raw(row) else "BAIXADO"
        )

        preco = float(row.get("valorUnitario") or row.get("precoUnitario") or row.get("precoCadastro") or 0)
        if preco <= 0 and litros > 0:
            preco = round(valor / litros, 4)
        preco_tab = float(
            row.get("precoCadastro")
            or row.get("tabelaPrecoA")
            or row.get("precoTabela")
            or preco
            or 0
        )
        litros_r = round(litros, 3)
        preco_r = round(preco, 4)
        desc = 0.0
        if preco_tab > 0 and preco_r > 0 and preco_tab > preco_r + 0.0001 and litros_r > 0:
            desc = round((preco_tab - preco_r) * litros_r, 2)

        tanque = None
        try:
            t = row.get("tanque") or row.get("codigoTanque")
            if t not in (None, ""):
                tanque = int(t)
        except (TypeError, ValueError):
            tanque = None

        bico_n = _bico_numero(row)
        # Heurística de bomba (2 bicos/bomba) quando Quality não envia codigoBomba
        bomba_n = ((max(1, bico_n) - 1) // 2) + 1 if bico_n else None

        return AbastecimentoRestV1(
            idAbastecimento=ab_id,
            uuid=str(row.get("uuid") or _uuid_for(emp, ab_id)),
            dataHora=data_hora,
            bico=bico_n,
            tanque=tanque,
            idProduto=id_produto,
            descricaoProduto=descricao,
            litros=litros_r,
            precoUnitario=preco_r,
            valorTotal=round(valor, 2),
            idFrentista=fid,
            nomeFrentista=nome,
            status=status,
            reservado=bool(row.get("reservado") or row.get("reserva") or False),
            idEmpresa=emp,
            nomeEmpresa=FILIAIS.get(emp, f"Empresa {emp}"),
            precoTabela=round(preco_tab, 4) if preco_tab else None,
            valorDesconto=desc,
            origemDesconto="FIDELIDADE/APP" if desc > 0 else None,
            bomba=bomba_n,
        )

    async def _fetch_abastecimentos(
        self,
        start: str,
        end: str,
        id_empresa: int | None,
        prefer_pendentes: bool = False,
    ) -> list[dict[str, Any]]:
        all_rows: list[dict[str, Any]] = []
        seen: set[int] = set()
        ultimo: Any = None
        endpoint = "abastecimento_rede"

        for _ in range(MAX_PAGES):
            params: dict[str, Any] = {"dataInicial": start, "dataFinal": end}
            if id_empresa:
                params["empresaCodigo"] = id_empresa
            if prefer_pendentes:
                # Tentativas oficiais / compatíveis — Quality pode ignorar
                params["status"] = "PENDENTE"
                params["apenasDisponiveis"] = True
            if ultimo is not None:
                params["ultimoCodigo"] = ultimo

            resp = await self.client.call_endpoint(endpoint, params=params)
            if not resp.success and endpoint == "abastecimento_rede":
                LOGGER.warning(
                    "AbastecimentoRede falhou (%s) — fallback ABASTECIMENTO",
                    resp.error,
                )
                endpoint = "abastecimento"
                # remove params que ABASTECIMENTO não reconhece
                params.pop("apenasDisponiveis", None)
                resp = await self.client.call_endpoint(endpoint, params=params)

            if not resp.success:
                LOGGER.warning(
                    "pista fetch falhou endpoint=%s url/status err=%s empresa=%s",
                    endpoint,
                    resp.error,
                    id_empresa,
                )
                break

            batch = _rows(resp.data)
            if not batch:
                break

            added = 0
            for row in batch:
                code = int(row.get("abastecimentoCodigo") or row.get("codigo") or 0)
                if code and code in seen:
                    continue
                if code:
                    seen.add(code)
                all_rows.append(row)
                added += 1

            new_ultimo = None
            if isinstance(resp.data, dict):
                new_ultimo = resp.data.get("ultimoCodigo")
            if new_ultimo in (None, ""):
                new_ultimo = batch[-1].get("codigo") or batch[-1].get("abastecimentoCodigo")

            if added == 0 or new_ultimo in (None, "", ultimo) or len(batch) < 100:
                break
            ultimo = new_ultimo

        # Segunda passagem sem filtro status (pendentes reais via vic<=0)
        if prefer_pendentes:
            raw2 = await self._cursor_plain(start, end, id_empresa)
            for row in raw2:
                code = int(row.get("abastecimentoCodigo") or row.get("codigo") or 0)
                if code and code in seen:
                    continue
                if code:
                    seen.add(code)
                all_rows.append(row)

        LOGGER.info(
            "pista %s: %d registros periodo=%s..%s empresa=%s",
            endpoint,
            len(all_rows),
            start,
            end,
            id_empresa,
        )
        return all_rows

    async def _cursor_plain(
        self,
        start: str,
        end: str,
        id_empresa: int | None,
    ) -> list[dict[str, Any]]:
        all_rows: list[dict[str, Any]] = []
        seen: set[int] = set()
        ultimo: Any = None
        for _ in range(MAX_PAGES):
            params: dict[str, Any] = {"dataInicial": start, "dataFinal": end}
            if id_empresa:
                params["empresaCodigo"] = id_empresa
            if ultimo is not None:
                params["ultimoCodigo"] = ultimo
            resp = await self.client.call_endpoint("abastecimento", params=params)
            if not resp.success:
                break
            batch = _rows(resp.data)
            if not batch:
                break
            for row in batch:
                code = int(row.get("abastecimentoCodigo") or row.get("codigo") or 0)
                if code and code in seen:
                    continue
                if code:
                    seen.add(code)
                all_rows.append(row)
            new_ultimo = None
            if isinstance(resp.data, dict):
                new_ultimo = resp.data.get("ultimoCodigo")
            if new_ultimo in (None, ""):
                new_ultimo = batch[-1].get("codigo") or batch[-1].get("abastecimentoCodigo")
            if new_ultimo in (None, "", ultimo) or len(batch) < 100:
                break
            ultimo = new_ultimo
        return all_rows

    async def _fetch_endpoint(
        self,
        endpoint: str,
        start: str,
        end: str,
        id_empresa: int | None,
    ) -> list[dict[str, Any]]:
        """Coleta com cursor ultimoCodigo (páginas Quality ~100–200)."""
        all_rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        ultimo: Any = None
        try:
            for _ in range(MAX_PAGES):
                params: dict[str, Any] = {"dataInicial": start, "dataFinal": end}
                if id_empresa:
                    params["empresaCodigo"] = id_empresa
                if ultimo is not None:
                    params["ultimoCodigo"] = ultimo
                resp = await self.client.call_endpoint(endpoint, params=params)
                if not resp.success:
                    LOGGER.warning("pista %s falhou: %s", endpoint, resp.error)
                    break
                batch = _rows(resp.data)
                if not batch:
                    break
                added = 0
                for row in batch:
                    marker = (
                        f"{row.get('codigo')}|{row.get('vendaCodigo')}|"
                        f"{row.get('vendaItemCodigo')}|{row.get('empresaCodigo')}|"
                        f"{row.get('valorPagamento') or row.get('valorTotal')}"
                    )
                    if marker in seen:
                        continue
                    seen.add(marker)
                    all_rows.append(row)
                    added += 1
                new_ultimo = None
                if isinstance(resp.data, dict):
                    new_ultimo = resp.data.get("ultimoCodigo")
                if new_ultimo in (None, ""):
                    new_ultimo = (
                        batch[-1].get("codigo")
                        or batch[-1].get("vendaItemCodigo")
                        or batch[-1].get("vendaCodigo")
                    )
                if added == 0 or new_ultimo in (None, "", ultimo) or len(batch) < 100:
                    break
                ultimo = new_ultimo
        except Exception as exc:
            LOGGER.warning("pista %s exception: %s", endpoint, exc)
        return all_rows

    async def _fetch_frentistas(self) -> dict[int, str]:
        mapping: dict[int, str] = {}
        try:
            resp = await self.client.call_endpoint("funcionario", params={})
            if not resp.success:
                return mapping
            for row in _rows(resp.data):
                try:
                    code = int(
                        row.get("funcionarioCodigo")
                        or row.get("codigo")
                        or row.get("codigoFrentista")
                        or 0
                    )
                except (TypeError, ValueError):
                    continue
                if not code:
                    continue
                nome = str(
                    row.get("nome")
                    or row.get("funcionarioNome")
                    or row.get("nomeCompleto")
                    or ""
                ).strip()
                if nome:
                    mapping[code] = nome
        except Exception as exc:
            LOGGER.warning("pista funcionario lookup falhou: %s", exc)
        return mapping

    @staticmethod
    def _index_venda_items(rows: list[dict[str, Any]]) -> dict[int, int]:
        out: dict[int, int] = {}
        for r in rows:
            vic = int(r.get("vendaItemCodigo") or r.get("codigo") or 0)
            vc = int(r.get("vendaCodigo") or 0)
            if vic and vc:
                out[vic] = vc
        return out

    @staticmethod
    def _index_pagamentos(
        rows: list[dict[str, Any]],
    ) -> dict[tuple[int, int], list[dict[str, Any]]]:
        out: dict[tuple[int, int], list[dict[str, Any]]] = {}
        for r in rows:
            vc = int(r.get("vendaCodigo") or 0)
            emp = int(r.get("empresaCodigo") or 0)
            if not vc:
                continue
            out.setdefault((emp, vc), []).append(r)
        return out

    @staticmethod
    def _index_cartoes(
        rows: list[dict[str, Any]],
    ) -> dict[tuple[int, int], dict[str, Any]]:
        """Indexa CARTAO por (empresa, vendaCodigo) — 1º registro da venda."""
        out: dict[tuple[int, int], dict[str, Any]] = {}
        for r in rows:
            try:
                vc = int(r.get("vendaCodigo") or 0)
                emp = int(r.get("empresaCodigo") or 0)
            except (TypeError, ValueError):
                continue
            if not vc:
                continue
            key = (emp, vc)
            if key not in out:
                out[key] = r
        return out

    @staticmethod
    def _index_vendas(
        rows: list[dict[str, Any]],
    ) -> dict[tuple[int, int], dict[str, Any]]:
        out: dict[tuple[int, int], dict[str, Any]] = {}
        for r in rows:
            vc = int(r.get("vendaCodigo") or r.get("codigo") or 0)
            emp = int(r.get("empresaCodigo") or 0)
            if vc:
                out[(emp, vc)] = r
        return out

    @staticmethod
    def _index_nfce(
        rows: list[dict[str, Any]],
    ) -> dict[tuple[int, int], dict[str, Any]]:
        out: dict[tuple[int, int], dict[str, Any]] = {}
        for r in rows:
            vc = int(r.get("vendaCodigo") or 0)
            emp = int(r.get("empresaCodigo") or 0)
            if vc:
                out[(emp, vc)] = r
        return out


_service: WebPostoPistaService | None = None


def get_pista_service() -> WebPostoPistaService:
    global _service
    if _service is None:
        _service = WebPostoPistaService()
    return _service
