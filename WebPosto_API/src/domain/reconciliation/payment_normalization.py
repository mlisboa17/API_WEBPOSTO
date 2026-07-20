"""D02 — Taxonomia de natureza financeira e origem de captura (POS/TEF)."""
from __future__ import annotations

import re
from typing import Any

from src.domain.reconciliation.models import (
    CaptureOrigin,
    ExpectedDestination,
    PaymentNatureCode,
)

NATURE_FIELD_MAP: dict[PaymentNatureCode, dict[str, str]] = {
    PaymentNatureCode.DINHEIRO: {
        "apresentado": "dinheiroApresentado",
        "apurado": "dinheiroApurado",
        "diferenca": "dinheiroDiferenca",
        "label": "Dinheiro",
        "category": "CASH",
    },
    PaymentNatureCode.NOTAS: {
        "apresentado": "notaPrazoApresentado",
        "apurado": "notaPrazoApurado",
        "diferenca": "notaPrazoDiferenca",
        "label": "Notas",
        "category": "CREDIT_NOTE",
    },
    PaymentNatureCode.CHEQUE_VISTA: {
        "apresentado": "chequeApresentado",
        "apurado": "chequeApurado",
        "diferenca": "chequeDiferenca",
        "label": "Cheque à Vista",
        "category": "CHECK",
    },
    PaymentNatureCode.CHEQUE_PRE: {
        "apresentado": "chequePreApresentado",
        "apurado": "chequePreApurado",
        "diferenca": "chequePreDiferenca",
        "label": "Cheque Pré",
        "category": "CHECK",
    },
    PaymentNatureCode.CARTAO: {
        "apresentado": "cartaoApresentado",
        "apurado": "cartaoApurado",
        "diferenca": "cartaoDiferenca",
        "label": "Cartão",
        "category": "CARD",
    },
    PaymentNatureCode.CARTA_FRETE: {
        "apresentado": "cartaFreteApresentado",
        "apurado": "cartaFreteApurado",
        "diferenca": "cartaFreteDiferenca",
        "label": "Carta Frete",
        "category": "FREIGHT",
    },
    PaymentNatureCode.VALE_CLIENTE: {
        "apresentado": "valeClienteApresentado",
        "apurado": "valeClienteApurado",
        "diferenca": "valeClienteDiferenca",
        "label": "Vale Cliente",
        "category": "CUSTOMER",
    },
    PaymentNatureCode.DESPESA: {
        "apresentado": "despesaApresentado",
        "apurado": "despesaApurado",
        "diferenca": "despesaDiferenca",
        "label": "Despesa",
        "category": "EXPENSE",
    },
    PaymentNatureCode.EMPRESTIMO: {
        "apresentado": "emprestimoApresentado",
        "apurado": "emprestimoApurado",
        "diferenca": "emprestimoDiferenca",
        "label": "Empréstimo",
        "category": "LOAN",
    },
    PaymentNatureCode.PRE_PAGO: {
        "apresentado": "prePagApresentado",
        "apurado": "prePagApurado",
        "diferenca": "prePagDiferenca",
        "label": "Pré-pago",
        "category": "PREPAID",
    },
    PaymentNatureCode.VALE_FUNCIONARIO: {
        "apresentado": "valeFunApresentado",
        "apurado": "valeFunApurado",
        "diferenca": "valeFunDiferenca",
        "label": "Vale Funcionário",
        "category": "EMPLOYEE",
    },
    PaymentNatureCode.TRANSFERENCIA_CREDITO: {
        "apresentado": "transfBancApresentado",
        "apurado": "transfBancApurado",
        "diferenca": "transfBancDiferenca",
        "label": "Transferência Crédito",
        "category": "TRANSFER",
    },
    PaymentNatureCode.TRANSFERENCIA_DEBITO: {
        "apresentado": "transfDebApresentado",
        "apurado": "transfDebApurado",
        "diferenca": "transfDebDiferenca",
        "label": "Transferência Débito",
        "category": "TRANSFER",
    },
    PaymentNatureCode.CHEQUE_PAGAR: {
        "apresentado": "chequePagarApresentado",
        "apurado": "chequePagarApurado",
        "diferenca": "chequePagarDiferenca",
        "label": "Cheque Pagar",
        "category": "CHECK",
    },
    PaymentNatureCode.FUNDO_CAIXA_DEBITO: {
        "apresentado": "fundoCxDebApresentado",
        "apurado": "fundoCxDebApurado",
        "diferenca": "fundoCxDebDiferenca",
        "label": "Fundo de Caixa Débito",
        "category": "CASH_FUND",
    },
}

EXPECTED_DESTINATION: dict[PaymentNatureCode, ExpectedDestination] = {
    PaymentNatureCode.DINHEIRO: ExpectedDestination.CASH,
    PaymentNatureCode.NOTAS: ExpectedDestination.CUSTOMER_BALANCE,
    PaymentNatureCode.CHEQUE_VISTA: ExpectedDestination.BANK_ACCOUNT,
    PaymentNatureCode.CHEQUE_PRE: ExpectedDestination.BANK_ACCOUNT,
    PaymentNatureCode.CARTAO: ExpectedDestination.ACQUIRER_RECEIVABLE,
    PaymentNatureCode.CARTA_FRETE: ExpectedDestination.CUSTOMER_BALANCE,
    PaymentNatureCode.VALE_CLIENTE: ExpectedDestination.CUSTOMER_BALANCE,
    PaymentNatureCode.DESPESA: ExpectedDestination.EXPENSE_LEDGER,
    PaymentNatureCode.EMPRESTIMO: ExpectedDestination.EMPLOYEE_BALANCE,
    PaymentNatureCode.PRE_PAGO: ExpectedDestination.CUSTOMER_BALANCE,
    PaymentNatureCode.VALE_FUNCIONARIO: ExpectedDestination.EMPLOYEE_BALANCE,
    PaymentNatureCode.TRANSFERENCIA_CREDITO: ExpectedDestination.BANK_ACCOUNT,
    PaymentNatureCode.TRANSFERENCIA_DEBITO: ExpectedDestination.BANK_ACCOUNT,
    PaymentNatureCode.CHEQUE_PAGAR: ExpectedDestination.BANK_ACCOUNT,
    PaymentNatureCode.FUNDO_CAIXA_DEBITO: ExpectedDestination.CASH,
}

POS_MARKERS = ("POS", "MANUAL", "LANCAMENTO MANUAL", "LANÇAMENTO MANUAL")
TEF_MARKERS = ("TEF", "PINPAD", "CAPTURA TEF")
CARD_MARKERS = ("CREDITO", "CRÉDITO", "DEBITO", "DÉBITO", "CARTAO", "CARTÃO")


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").upper().strip())


def infer_capture_origin(
    forma_label: str | None = None,
    tipo_forma: str | None = None,
) -> CaptureOrigin:
    """POS/TEF são origem de captura — nunca natureza financeira."""
    blob = _norm(f"{forma_label or ''} {tipo_forma or ''}")
    if any(m in blob for m in TEF_MARKERS):
        return CaptureOrigin.TEF
    if any(m in blob for m in POS_MARKERS):
        return CaptureOrigin.POS_MANUAL
    if "TRANSF" in blob or "PIX" in blob or "TED" in blob:
        return CaptureOrigin.BANK_TRANSFER
    if "CAIXA" in blob or blob.startswith("DINHEIRO"):
        return CaptureOrigin.CASH_REGISTER
    if blob:
        return CaptureOrigin.INTERNAL
    return CaptureOrigin.UNKNOWN


def infer_card_method(label: str) -> str:
    blob = _norm(label)
    if "DEBIT" in blob or "DEBITO" in blob or "DÉBITO" in blob or "ELECTRON" in blob or "MAESTRO" in blob:
        return "DEBIT"
    if "CREDIT" in blob or "CREDITO" in blob or "CRÉDITO" in blob:
        return "CREDIT"
    if any(x in blob for x in CARD_MARKERS):
        return "CARD"
    return "UNKNOWN"


def infer_card_brand(label: str) -> str:
    blob = _norm(label)
    brands = (
        ("AMERICAN EXPRESS", "AMEX"),
        ("MASTERCARD", "MASTERCARD"),
        ("MAESTRO", "MAESTRO"),
        ("VISA", "VISA"),
        ("ELO", "ELO"),
        ("HIPERCARD", "HIPERCARD"),
        ("DINERS", "DINERS"),
    )
    for needle, brand in brands:
        if needle in blob:
            return brand
    return "UNKNOWN"


def infer_acquirer(label: str, administradora_codigo: Any = None) -> str:
    """Nunca inventar adquirente — UNKNOWN quando sem evidência."""
    blob = _norm(label)
    if administradora_codigo not in (None, "", 0, "0"):
        return f"ADM_{administradora_codigo}"
    bank_hints = ("ITAU", "ITAÚ", "BRADESCO", "SANTANDER", "CIELO", "REDE", "GETNET", "STONE")
    for hint in bank_hints:
        if hint in blob:
            return hint.replace("ITAÚ", "ITAU")
    return "UNKNOWN"


def map_vfp_to_payment_nature(row: dict[str, Any]) -> PaymentNatureCode | None:
    """Mapeia VFP para natureza real — POS/TEF ficam em captureOrigin."""
    label = _norm(row.get("nomeFormaPagamento") or row.get("formaPagamento") or "")
    tipo = _norm(row.get("tipoFormaPagamento") or "")
    blob = f"{label} {tipo}"
    if "DINHEIRO" in blob:
        return PaymentNatureCode.DINHEIRO
    if "NOTA" in blob and "PRAZO" in blob:
        return PaymentNatureCode.NOTAS
    if "CHEQUE" in blob and "PRE" in blob:
        return PaymentNatureCode.CHEQUE_PRE
    if "CHEQUE" in blob and "PAGAR" in blob:
        return PaymentNatureCode.CHEQUE_PAGAR
    if "CHEQUE" in blob:
        return PaymentNatureCode.CHEQUE_VISTA
    if any(x in blob for x in ("CARTAO", "CARTÃO", "CREDITO", "CRÉDITO", "DEBITO", "DÉBITO", "VISA", "MASTER", "ELO")):
        return PaymentNatureCode.CARTAO
    if "FRETE" in blob:
        return PaymentNatureCode.CARTA_FRETE
    if "VALE" in blob and "FUNC" in blob:
        return PaymentNatureCode.VALE_FUNCIONARIO
    if "VALE" in blob and "CLIENT" in blob:
        return PaymentNatureCode.VALE_CLIENTE
    if "DESPESA" in blob:
        return PaymentNatureCode.DESPESA
    if "EMPREST" in blob:
        return PaymentNatureCode.EMPRESTIMO
    if "PRE" in blob and "PAG" in blob:
        return PaymentNatureCode.PRE_PAGO
    if "TRANSF" in blob and "DEB" in blob:
        return PaymentNatureCode.TRANSFERENCIA_DEBITO
    if "TRANSF" in blob or "PIX" in blob:
        return PaymentNatureCode.TRANSFERENCIA_CREDITO
    if "FUNDO" in blob and "DEB" in blob:
        return PaymentNatureCode.FUNDO_CAIXA_DEBITO
    return None
