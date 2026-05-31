from __future__ import annotations

from enum import Enum


class PaymentMethod(str, Enum):
    DINHEIRO = "DINHEIRO"
    CARTAO_CREDITO = "CARTAO_CREDITO"
    CARTAO_DEBITO = "CARTAO_DEBITO"
    PIX = "PIX"
    PRAZO = "PRAZO"
    OUTRO = "OUTRO"

    @classmethod
    def from_raw(cls, raw: str | None) -> "PaymentMethod":
        if not raw:
            return cls.OUTRO
        u = raw.upper()
        if "DINH" in u or "CASH" in u:
            return cls.DINHEIRO
        if "PIX" in u:
            return cls.PIX
        if "DEB" in u:
            return cls.CARTAO_DEBITO
        if "CRED" in u or "CART" in u:
            return cls.CARTAO_CREDITO
        if "PRAZ" in u:
            return cls.PRAZO
        return cls.OUTRO
