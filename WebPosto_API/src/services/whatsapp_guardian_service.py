"""Guardião WhatsApp — dispatcher de alertas críticos anti-fraude (Sprint 6).

Gatilhos (RAM, pós-refresh do FraudDetectionEngine):
  - Score == 100 (Cartão Curinga)
  - Retenção crítica com cartão/PIX/TEF > 30 min

Env:
  WHATSAPP_ALERTS_ENABLED=true|false
  WHATSAPP_WEBHOOK_URL=https://...
  WHATSAPP_FRONTEND_BASE_URL=http://localhost:3000
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from src.infrastructure.config.settings import settings
from src.services.fraud_detection_engine import OcorrenciaFraudeDTO

LOGGER = logging.getLogger(__name__)

FILIAIS = {
    5555: "Casa Caiada",
    11495: "VIP",
    74014: "Real Doze",
}

# Dedup em RAM: idOcorrencia → monotonic ts do último envio
_SENT: dict[str, float] = {}
_DEDUP_TTL_S = 6 * 3600.0  # 6h — evita flood no mesmo ciclo/dia


def _is_eletronico_ocorrencia(o: OcorrenciaFraudeDTO) -> bool:
    blob = f"{o.formaPagamento} {o.meioPagamento} {o.cartaoBandeira}".upper()
    if o.isEspecie:
        return False
    return any(
        x in blob
        for x in (
            "CART",
            "TEF",
            "PIX",
            "DEBIT",
            "DÉBIT",
            "CREDIT",
            "CRÉDIT",
            "FROTA",
            "MAESTRO",
            "VISA",
            "ELO",
        )
    ) or bool(o.cartaoFinal or o.cartaoNsu)


def _should_alert(o: OcorrenciaFraudeDTO, retencao_critica_min: int = 30) -> tuple[bool, str]:
    if int(o.scoreGravidade or 0) >= 100 or bool(o.cartaoRepetido):
        return True, "CARTAO_REPETIDO"
    if (
        _is_eletronico_ocorrencia(o)
        and int(o.tempoRetencaoMinutos or 0) > retencao_critica_min
    ):
        return True, "RETENCAO_CRITICA"
    return False, ""


def _alerta_titulo(kind: str) -> str:
    if kind == "CARTAO_REPETIDO":
        return "🚨 CARTÃO REPETIDO DETECTADO"
    return "⚠️ RETENÇÃO CRÍTICA"


def _bico_principal(o: OcorrenciaFraudeDTO) -> str:
    dets = o.abastecimentosAgrupados or o.detalhes or []
    if not dets:
        return "—"
    d = dets[0]
    bico = int(d.bico or 0)
    bomba = int(d.bomba or ((max(1, bico) - 1) // 2) + 1)
    return f"Bico {bico:02d} / Bomba {bomba:02d}"


def build_whatsapp_payload(
    o: OcorrenciaFraudeDTO,
    *,
    kind: str,
    frontend_base: str,
) -> dict[str, Any]:
    emp = int(o.empresaCodigo or o.postoUnidade or 0)
    filial = FILIAIS.get(emp, o.postoNome or o.empresaNome or f"Filial {emp}")
    oid = o.idOcorrencia or o.id
    base = (frontend_base or "http://localhost:3000").rstrip("/")
    link = f"{base}/executive/data-audit?tab=anti-fraude&ocorrencia={oid}"
    frentista = o.funcionarioNome or o.frentistaNome or "N/I"
    valor = float(o.valorTotal or o.valorTotalCartao or 0)
    texto = (
        f"{_alerta_titulo(kind)}\n"
        f"Filial: {filial} ({emp})\n"
        f"Frentista: {frentista}\n"
        f"Valor: R$ {valor:,.2f}\n"
        f"Bico: {_bico_principal(o)}\n"
        f"Retenção: {o.tempoRetencaoMinutos} min\n"
        f"Score: {o.scoreGravidade}/100\n"
        f"Dossiê: {link}"
    )
    return {
        "event": "LOGOS_GUARDIAN_ALERT",
        "channel": "whatsapp",
        "provider": "evolution_or_zapi",
        "alerta": _alerta_titulo(kind),
        "tipo": kind,
        "filial": filial,
        "empresaCodigo": emp,
        "frentista": frentista,
        "frentistaId": o.frentistaId or o.funcionarioId,
        "valor": round(valor, 2),
        "valorFormatado": f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "bico": _bico_principal(o),
        "tempoRetencaoMinutos": int(o.tempoRetencaoMinutos or 0),
        "score": int(o.scoreGravidade or 0),
        "cartaoRepetido": bool(o.cartaoRepetido),
        "quantidadeUsoCartao": int(o.quantidadeUsoCartao or 0),
        "ocorrenciaId": oid,
        "linkDossie": link,
        "message": texto,
        # Evolution / Z-API style helpers
        "text": texto,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }


class WhatsAppGuardianService:
    """Despacha webhooks WhatsApp para ocorrências críticas (idempotente 6h)."""

    def __init__(self) -> None:
        self.enabled = bool(getattr(settings, "whatsapp_alerts_enabled", False))
        self.webhook_url = (getattr(settings, "whatsapp_webhook_url", None) or "").strip()
        self.frontend_base = (
            getattr(settings, "whatsapp_frontend_base_url", None)
            or "http://localhost:3000"
        ).strip()

    def _purge_dedup(self) -> None:
        now = time.monotonic()
        dead = [k for k, ts in _SENT.items() if now - ts > _DEDUP_TTL_S]
        for k in dead:
            _SENT.pop(k, None)

    async def dispatch_from_ocorrencias(
        self,
        ocorrencias: list[OcorrenciaFraudeDTO],
        *,
        retencao_critica_min: int = 30,
    ) -> dict[str, Any]:
        self._purge_dedup()
        if not self.enabled:
            return {"enabled": False, "sent": 0, "skipped": "WHATSAPP_ALERTS_ENABLED=false"}
        if not self.webhook_url:
            LOGGER.warning(
                "Guardião WhatsApp habilitado sem WHATSAPP_WEBHOOK_URL — alertas ignorados"
            )
            return {"enabled": True, "sent": 0, "skipped": "webhook_url_vazio"}

        candidates: list[tuple[OcorrenciaFraudeDTO, str]] = []
        for o in ocorrencias:
            ok, kind = _should_alert(o, retencao_critica_min)
            if not ok:
                continue
            oid = o.idOcorrencia or o.id
            if oid in _SENT:
                continue
            candidates.append((o, kind))

        sent = 0
        errors = 0
        async with httpx.AsyncClient(timeout=12.0) as client:
            for o, kind in candidates:
                payload = build_whatsapp_payload(
                    o, kind=kind, frontend_base=self.frontend_base
                )
                oid = payload["ocorrenciaId"]
                try:
                    resp = await client.post(self.webhook_url, json=payload)
                    if resp.status_code >= 400:
                        LOGGER.error(
                            "Guardião WhatsApp HTTP %s oid=%s body=%s",
                            resp.status_code,
                            oid,
                            (resp.text or "")[:200],
                        )
                        errors += 1
                        continue
                    _SENT[oid] = time.monotonic()
                    sent += 1
                    LOGGER.info(
                        "Guardião WhatsApp enviado tipo=%s filial=%s oid=%s score=%s",
                        kind,
                        payload.get("filial"),
                        oid,
                        payload.get("score"),
                    )
                except Exception as exc:
                    errors += 1
                    LOGGER.exception(
                        "Guardião WhatsApp falhou oid=%s: %s", oid, exc
                    )

        return {
            "enabled": True,
            "candidates": len(candidates),
            "sent": sent,
            "errors": errors,
            "dedupCached": len(_SENT),
        }


_guardian: WhatsAppGuardianService | None = None


def get_whatsapp_guardian() -> WhatsAppGuardianService:
    global _guardian
    if _guardian is None:
        _guardian = WhatsAppGuardianService()
    return _guardian
