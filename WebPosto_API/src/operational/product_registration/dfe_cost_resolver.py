"""Resolve preco de custo exclusivamente a partir das NF-e de entrada do DF-e.

Regra do dominio: custo de produto novo nunca vem de digitacao, de template, de produto
semelhante nem do preco de venda. Vem da NF-e de entrada autorizada mais recente que
contenha o EAN exato. Se nao houver essa nota, o produto e bloqueado.

O modulo reutiliza o store oficial em src.operational.dfe.store e nao reimplementa
parser de NF-e: o XML e lido apenas para os totais do documento, que sao necessarios
para ratear frete, seguro, outras despesas e desconto.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from src.operational.dfe import store

COST_DECIMALS = 4

# CST de IPI sem valor a recolher: nao entram no custo.
IPI_NON_TAXED_CST = frozenset({"51", "52", "53", "54", "55", "99"})

MATCH_EXACT_EAN = "EXACT_EAN"
MATCH_MAPPED_CODE = "MAPPED_EXTERNAL_CODE"
MATCH_DESCRIPTION = "DESCRIPTION_ONLY"

STATUS_RESOLVED = "COST_RESOLVED_FROM_DFE"
STATUS_NOT_FOUND = "BLOCKED_DFE_COST_NOT_FOUND"
STATUS_REVIEW_DESCRIPTION_ONLY = "REVIEW_REQUIRED_DESCRIPTION_ONLY_MATCH"
STATUS_REVIEW_UNIT = "REVIEW_REQUIRED_UNIT_NORMALIZATION"

# Unidades comerciais que já representam a unidade de venda no varejo.
ATOMIC_UNITS = frozenset(
    {"UN", "UNI", "UN1", "UND", "UNID", "UNIDADE", "PC", "PÇ", "PECA", "PEÇA", "GF", "LA", "LT1"}
)


def is_atomic_unit(unit: Any) -> bool:
    """Indica se a unidade comercial da NF-e equivale à unidade de venda.

    Caixa, fardo, display, pacote e unidades de peso agrupam vários itens: dividir o
    valor pela quantidade de embalagens produziria um custo várias vezes maior que o
    real. Sem fator de conversão confiável no documento, o custo não é derivável.
    """
    if unit is None:
        return False
    return str(unit).strip().upper() in ATOMIC_UNITS


QUANTITY_FROM_COMMERCIAL = "uCom"
QUANTITY_FROM_TAXABLE = "uTrib"


def resolve_sale_unit_quantity(item: dict[str, Any]) -> tuple[Decimal, str | None]:
    """Quantidade de unidades de venda contidas no item da NF-e.

    Quando a unidade comercial é a de venda, a própria quantidade comercial responde.
    Quando é embalagem, a nota ainda pode declarar a quantidade tributável em unidades,
    e esse é um fator de conversão do próprio documento — não uma suposição. Só quando
    nenhuma das duas unidades é de venda o custo unitário fica indeterminado.
    """
    q_com = _dec(item.get("q_com"))
    if is_atomic_unit(item.get("u_com")):
        return q_com, QUANTITY_FROM_COMMERCIAL
    q_trib = _dec(item.get("q_trib"))
    if is_atomic_unit(item.get("u_trib")) and q_trib > 0:
        return q_trib, QUANTITY_FROM_TAXABLE
    from src.operational.dfe_sync.packaging_conversion import (  # noqa: I001
        PackagingConversionResolver,
    )

    resolved = PackagingConversionResolver().resolve(item, supplier_cnpj=item.get("supplier_cnpj"))
    factor = resolved.get("factor")
    if resolved.get("ok") and factor:
        return q_com * factor, "packaging_conversion"
    return Decimal("0"), None


class DfeCostError(Exception):
    """Falha ao resolver custo pelo DF-e."""


@dataclass(frozen=True)
class InvoiceTotals:
    """Totais do documento, usados para ratear despesas acessorias."""

    produtos: Decimal = Decimal("0")
    frete: Decimal = Decimal("0")
    seguro: Decimal = Decimal("0")
    outras: Decimal = Decimal("0")
    desconto: Decimal = Decimal("0")
    ipi: Decimal = Decimal("0")

    @property
    def has_allocations(self) -> bool:
        return any(v > 0 for v in (self.frete, self.seguro, self.outras, self.desconto))


@dataclass
class CostEvidence:
    """Evidencia auditavel do custo unitario de um produto."""

    status: str
    ean: str
    match_type: str | None = None
    document_id: str | None = None
    access_key_masked: str | None = None
    numero: str | None = None
    serie: str | None = None
    emissao: str | None = None
    fornecedor: str | None = None
    fornecedor_cnpj: str | None = None
    destinatario_cnpj: str | None = None
    protocolo_cstat: str | None = None
    cancelada: bool | None = None
    item_line: int | None = None
    item_descricao: str | None = None
    item_ncm: str | None = None
    item_cest: str | None = None
    item_cfop: str | None = None
    unidade_comercial: str | None = None
    quantidade: Decimal | None = None
    quantidade_normalizada: Decimal | None = None
    valor_produto: Decimal | None = None
    desconto_item: Decimal = Decimal("0")
    frete_rateado: Decimal = Decimal("0")
    seguro_rateado: Decimal = Decimal("0")
    outras_rateadas: Decimal = Decimal("0")
    ipi_nao_recuperavel: Decimal = Decimal("0")
    icms_st_cobrado: Decimal = Decimal("0")
    valor_liquido_item: Decimal | None = None
    preco_custo: Decimal | None = None
    calculo: str | None = None
    candidatos_avaliados: int = 0
    notas_descartadas: list[dict[str, Any]] = field(default_factory=list)
    unidade_atomica: bool | None = None
    quantidade_origem: str | None = None
    reason: str | None = None

    @property
    def resolved(self) -> bool:
        return self.status == STATUS_RESOLVED and self.preco_custo is not None


def _dec(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _xml_bytes_for_document(document_id: str) -> bytes:
    xml_path = store.store_root() / "documents" / f"{document_id}.xml"
    if xml_path.is_file():
        return xml_path.read_bytes()
    document = store.load_document(document_id) or {}
    ref = str(document.get("xml_storage_reference") or "")
    if ref.startswith("dfe_sec_"):
        from src.operational.dfe.vault import get_vault

        return get_vault().get_secret(ref)
    raise DfeCostError(f"XML ausente para documento {document_id}")


def read_invoice_totals(document_id: str) -> InvoiceTotals:
    """Le os totais em ICMSTot direto do XML arquivado.

    Os totais nao estao no documento normalizado, e sao obrigatorios para saber se
    existe rateio a aplicar. Sem eles, assumir zero seria fallback silencioso.
    """
    root = ET.fromstring(_xml_bytes_for_document(document_id))
    totals: dict[str, str] = {}
    for node in root.iter():
        if _strip_ns(node.tag) != "ICMSTot":
            continue
        for child in node:
            totals[_strip_ns(child.tag)] = (child.text or "").strip()
        break

    if not totals:
        raise DfeCostError(f"ICMSTot ausente no XML do documento {document_id}")

    return InvoiceTotals(
        produtos=_dec(totals.get("vProd")),
        frete=_dec(totals.get("vFrete")),
        seguro=_dec(totals.get("vSeg")),
        outras=_dec(totals.get("vOutro")),
        desconto=_dec(totals.get("vDesc")),
        ipi=_dec(totals.get("vIPI")),
    )


def item_ipi_non_recoverable(item: dict[str, Any]) -> Decimal:
    """IPI que integra o custo.

    A empresa 118508 e comercio, portanto nao credita IPI: quando destacado, ele e
    custo. CST de IPI nao tributado nao gera valor.
    """
    ipi = item.get("ipi") or {}
    cst = str(ipi.get("IPI.CST") or "").strip()
    if cst in IPI_NON_TAXED_CST:
        return Decimal("0")
    return _dec(ipi.get("IPI.vIPI"))


def item_icms_st_cost(item: dict[str, Any]) -> Decimal:
    """ICMS-ST cobrado na nota de entrada, que integra o custo de aquisição.

    Em CST 10 e 30 o fornecedor cobra a ST do adquirente. Como a saída da mercadoria
    sai sem débito de ICMS, esse valor não é recuperável e compõe o custo. Em CST 60 a
    ST já foi retida antes na cadeia e não é cobrada de novo nesta nota.
    """
    icms = item.get("icms") or {}
    return _dec(icms.get("ICMS.vICMSST"))


def allocate(share_base: Decimal, total_base: Decimal, amount: Decimal) -> Decimal:
    """Rateia `amount` proporcionalmente ao peso do item na nota."""
    if amount == 0:
        return Decimal("0")
    if total_base <= 0:
        raise DfeCostError("Base de rateio invalida: total de produtos zerado")
    return (amount * share_base / total_base).quantize(Decimal("0.000001"))


def compute_unit_cost(item: dict[str, Any], totals: InvoiceTotals) -> dict[str, Decimal | str]:
    """Calcula o custo unitario do item conforme a politica de custo do DF-e."""
    valor_produto = _dec(item.get("v_prod"))
    quantidade, quantidade_origem = resolve_sale_unit_quantity(item)
    if quantidade <= 0:
        # Sem unidade de venda identificável o custo por unidade não é derivável; segue o
        # cálculo pela quantidade comercial apenas para o relatório, e quem consome marca
        # o item como pendente de conversão.
        quantidade = _dec(item.get("q_com"))
        quantidade_origem = None
    if quantidade <= 0:
        raise DfeCostError("Quantidade comercial invalida (zero ou negativa)")
    if valor_produto <= 0:
        raise DfeCostError("Valor do produto invalido (zero ou negativo)")

    desconto_item = _dec(item.get("v_desc"))
    frete_item = _dec(item.get("v_frete"))
    seguro_item = _dec(item.get("v_seg"))
    outras_item = _dec(item.get("v_outro"))

    # Quando a despesa nao vem no item, rateia pelo total do documento.
    frete = frete_item or allocate(valor_produto, totals.produtos, totals.frete)
    seguro = seguro_item or allocate(valor_produto, totals.produtos, totals.seguro)
    outras = outras_item or allocate(valor_produto, totals.produtos, totals.outras)
    desconto = desconto_item or allocate(valor_produto, totals.produtos, totals.desconto)
    ipi = item_ipi_non_recoverable(item)
    icms_st = item_icms_st_cost(item)

    valor_liquido = valor_produto - desconto + frete + seguro + outras + ipi + icms_st
    preco_custo = (valor_liquido / quantidade).quantize(Decimal(10) ** -COST_DECIMALS)

    return {
        "quantidade": quantidade,
        "quantidade_origem": quantidade_origem,
        "valor_produto": valor_produto,
        "desconto_item": desconto,
        "frete_rateado": frete,
        "seguro_rateado": seguro,
        "outras_rateadas": outras,
        "ipi_nao_recuperavel": ipi,
        "icms_st_cobrado": icms_st,
        "valor_liquido_item": valor_liquido,
        "preco_custo": preco_custo,
        "calculo": (
            f"({valor_produto} - {desconto} + {frete} + {seguro} + {outras} + {ipi}"
            f" + {icms_st}) / {quantidade} = {preco_custo}"
        ),
    }


def _authorized(document: dict[str, Any]) -> tuple[bool, str]:
    protocol = document.get("protocol") or {}
    if protocol.get("cancelled") is True:
        return False, "CANCELADA"
    cstat = str(protocol.get("cStat") or "").strip()
    if cstat != "100":
        return False, f"NAO_AUTORIZADA_cStat_{cstat or 'AUSENTE'}"
    return True, "AUTORIZADA"


def normalize_description(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", (value or "").upper()).strip()


def find_cost_evidence(
    ean: str,
    company_code: int,
    *,
    mapped_codes: tuple[str, ...] = (),
    description: str | None = None,
) -> CostEvidence:
    """Localiza a NF-e de entrada autorizada mais recente com o EAN exato."""
    documents = store.list_documents(company_code)
    discarded: list[dict[str, Any]] = []
    exact: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    mapped: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    description_only: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    evaluated = 0

    normalized_target = normalize_description(description or "")

    for document in documents:
        ok, motive = _authorized(document)
        for raw_item in store.load_items(document["id"]):
            item = raw_item.get("normalized_json") or {}
            codes = {str(item.get("c_ean") or ""), str(item.get("c_ean_trib") or "")}
            item_matches_ean = ean in codes
            item_matches_mapped = bool(mapped_codes) and bool(codes & set(mapped_codes))
            item_matches_description = bool(normalized_target) and normalize_description(
                item.get("x_prod") or ""
            ) == normalized_target

            if not (item_matches_ean or item_matches_mapped or item_matches_description):
                continue

            evaluated += 1
            if not ok:
                discarded.append(
                    {
                        "documentId": document["id"],
                        "accessKeyMasked": document.get("access_key_masked"),
                        "reason": motive,
                    }
                )
                continue

            if item_matches_ean:
                exact.append((document["issued_at"] or "", document, raw_item))
            elif item_matches_mapped:
                mapped.append((document["issued_at"] or "", document, raw_item))
            else:
                description_only.append((document["issued_at"] or "", document, raw_item))

    for bucket, match_type in ((exact, MATCH_EXACT_EAN), (mapped, MATCH_MAPPED_CODE)):
        if not bucket:
            continue
        bucket.sort(key=lambda row: row[0], reverse=True)
        _, document, raw_item = bucket[0]
        return _build_evidence(ean, match_type, document, raw_item, evaluated, discarded)

    if description_only:
        description_only.sort(key=lambda row: row[0], reverse=True)
        _, document, raw_item = description_only[0]
        evidence = _build_evidence(
            ean, MATCH_DESCRIPTION, document, raw_item, evaluated, discarded
        )
        evidence.status = STATUS_REVIEW_DESCRIPTION_ONLY
        evidence.reason = (
            "Correspondencia apenas por descricao normalizada: exige revisao humana e "
            "nao autoriza cadastro automatico"
        )
        return evidence

    return CostEvidence(
        status=STATUS_NOT_FOUND,
        ean=ean,
        candidatos_avaliados=evaluated,
        notas_descartadas=discarded,
        reason=(
            "Nenhuma NF-e de entrada autorizada da empresa contem o EAN exato"
            if not discarded
            else "Notas encontradas foram descartadas por cancelamento ou falta de autorizacao"
        ),
    )


def build_authorized_index(company_code: int) -> dict[str, tuple[str, dict[str, Any], dict[str, Any]]]:
    """Indexa EAN -> NF-e autorizada mais recente que contem o item.

    Evita varrer todos os documentos uma vez por produto quando o lote e grande.
    Notas canceladas ou nao autorizadas nunca entram no indice.
    """
    index: dict[str, tuple[str, dict[str, Any], dict[str, Any]]] = {}
    for document in store.list_documents(company_code):
        authorized, _ = _authorized(document)
        if not authorized:
            continue
        issued_at = document.get("issued_at") or ""
        for raw_item in store.load_items(document["id"]):
            item = raw_item.get("normalized_json") or {}
            for code in {str(item.get("c_ean") or ""), str(item.get("c_ean_trib") or "")}:
                if not code or code == "None":
                    continue
                current = index.get(code)
                if current is None or issued_at > current[0]:
                    index[code] = (issued_at, document, raw_item)
    return index


def cost_from_index(
    ean: str, index: dict[str, tuple[str, dict[str, Any], dict[str, Any]]]
) -> CostEvidence:
    """Resolve o custo usando o indice pre-construido."""
    hit = index.get(ean)
    if hit is None:
        return CostEvidence(
            status=STATUS_NOT_FOUND,
            ean=ean,
            reason="Nenhuma NF-e de entrada autorizada da empresa contem o EAN exato",
        )
    _, document, raw_item = hit
    return _build_evidence(ean, MATCH_EXACT_EAN, document, raw_item, 1, [])


def _build_evidence(
    ean: str,
    match_type: str,
    document: dict[str, Any],
    raw_item: dict[str, Any],
    evaluated: int,
    discarded: list[dict[str, Any]],
) -> CostEvidence:
    item = raw_item.get("normalized_json") or {}
    totals = read_invoice_totals(document["id"])
    computed = compute_unit_cost(item, totals)
    protocol = document.get("protocol") or {}
    quantity_source = computed.get("quantidade_origem")
    unit_atomic = quantity_source is not None

    return CostEvidence(
        status=STATUS_RESOLVED if unit_atomic else STATUS_REVIEW_UNIT,
        ean=ean,
        match_type=match_type,
        document_id=document["id"],
        access_key_masked=document.get("access_key_masked"),
        numero=document.get("nNF"),
        serie=document.get("serie"),
        emissao=document.get("issued_at"),
        fornecedor=document.get("issuer_name"),
        fornecedor_cnpj=document.get("issuer_cnpj"),
        destinatario_cnpj=document.get("recipient_cnpj"),
        protocolo_cstat=str(protocol.get("cStat") or ""),
        cancelada=bool(protocol.get("cancelled")),
        item_line=raw_item.get("line_number"),
        item_descricao=item.get("x_prod"),
        item_ncm=item.get("ncm"),
        item_cest=item.get("cest"),
        item_cfop=item.get("cfop"),
        unidade_comercial=item.get("u_com"),
        quantidade=computed["quantidade"],
        quantidade_normalizada=computed["quantidade"],
        valor_produto=computed["valor_produto"],
        desconto_item=computed["desconto_item"],
        frete_rateado=computed["frete_rateado"],
        seguro_rateado=computed["seguro_rateado"],
        outras_rateadas=computed["outras_rateadas"],
        ipi_nao_recuperavel=computed["ipi_nao_recuperavel"],
        icms_st_cobrado=computed["icms_st_cobrado"],
        valor_liquido_item=computed["valor_liquido_item"],
        preco_custo=computed["preco_custo"],
        calculo=computed["calculo"],
        candidatos_avaliados=evaluated,
        notas_descartadas=discarded,
        unidade_atomica=unit_atomic,
        quantidade_origem=quantity_source,
        reason=(
            f"Unidade comercial '{item.get('u_com')}' agrupa múltiplos itens e a nota "
            f"declara a quantidade tributável em '{item.get('u_trib')}': custo por "
            f"unidade obtido de qTrib={item.get('q_trib')}"
        )
        if quantity_source == QUANTITY_FROM_TAXABLE
        else None
        if unit_atomic
        else (
            f"Unidade comercial '{item.get('u_com')}' agrupa múltiplos itens "
            f"(uTrib={item.get('u_trib')}, qTrib={item.get('q_trib')}): o custo por "
            f"unidade de venda exige fator de conversão que a NF-e não fornece"
        ),
    )


def evidence_to_dict(evidence: CostEvidence) -> dict[str, Any]:
    """Serializa a evidencia sem expor a chave completa da NF-e."""

    def convert(value: Any) -> Any:
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, list):
            return [convert(v) for v in value]
        return value

    payload = {key: convert(value) for key, value in vars(evidence).items()}
    payload["resolved"] = evidence.resolved
    return payload


def resolve_required_cost(ean: str, company_code: int) -> CostEvidence:
    """Versao fail-closed: levanta erro quando o custo nao pode ser comprovado."""
    evidence = find_cost_evidence(ean, company_code)
    if not evidence.resolved:
        raise DfeCostError(f"{evidence.status}: EAN {ean} sem custo comprovado no DF-e")
    return evidence
