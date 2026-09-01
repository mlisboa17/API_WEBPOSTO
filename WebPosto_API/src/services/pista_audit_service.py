"""Serviço de Auditoria de Pista — Detecção de Fraudes e Anomalias.

Implementa regras para identificar:
- Abastecimentos pendentes (sem baixa no PDV por mais de 15 minutos)
- Divergência de meio de pagamento (troca de dinheiro por cartão)
- Abastecimentos em aberto que podem indicar giro fraudulento de caixa

Sprint 57-E: Auditoria de Pista contra Fraude de Giro de Caixa
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

LOGGER = logging.getLogger(__name__)

FILIAIS = {
    5555: "AP CASA CAIADA",
    6666: "POSTO VIP",
    7777: "POSTO REAL / DOZE",
    11495: "POSTO VIP",
    5558: "POSTO REAL",
}

ALERTA_RETENCAO_MINUTOS = 15
ALERTA_DIVERGENCIA_TEF_MINUTOS = 20


class AbastecimentoPendente(BaseModel):
    """Abastecimento que não recebeu baixa no PDV."""
    
    id: int
    data: str
    hora: str
    bico: int
    produto: str
    litros: Decimal
    valor: Decimal
    empresa_codigo: int
    empresa_nome: str
    frentista_codigo: int | None = None
    frentista_nome: str | None = None
    turno: str | None = None
    minutos_pendente: int
    status_nfce: str
    alerta_tipo: str


class DivergenciaPagamento(BaseModel):
    """Divergência entre horário de abastecimento e autorização TEF."""
    
    abastecimento_id: int
    data: str
    hora_abastecimento: str
    hora_autorizacao_tef: str | None
    meio_pagamento: str
    valor: Decimal
    diferenca_minutos: int
    empresa_codigo: int
    empresa_nome: str
    frentista_nome: str | None = None
    alerta_tipo: str


class ResumoPendentes(BaseModel):
    """Resumo de abastecimentos pendentes por filial."""
    
    empresa_codigo: int
    empresa_nome: str
    total_pendentes: int
    litros_pendentes: Decimal
    valor_pendente: Decimal


class ResumoAnomaliasPista(BaseModel):
    """Resumo consolidado de anomalias de pista."""
    
    total_abastecimentos: int
    total_pendentes: int
    litros_pendentes: Decimal
    valor_pendente: Decimal
    alertas_retencao: int
    alertas_divergencia_tef: int
    por_filial: list[ResumoPendentes]
    por_frentista: list[dict[str, Any]]
    por_bico: list[dict[str, Any]]
    por_turno: list[dict[str, Any]]


class PistaAuditResult(BaseModel):
    """Resultado completo da auditoria de pista."""
    
    periodo: dict[str, str]
    resumo: ResumoAnomaliasPista
    pendentes: list[AbastecimentoPendente]
    divergencias_pagamento: list[DivergenciaPagamento]


class PistaAuditService:
    """Serviço de auditoria de pista para detecção de fraudes."""

    @staticmethod
    def _parse_datetime(data: str, hora: str) -> datetime | None:
        """Converte data e hora para datetime."""
        try:
            data_str = str(data).split("T")[0] if "T" in str(data) else str(data)
            hora_str = str(hora)[:8] if len(str(hora)) > 8 else str(hora)
            return datetime.strptime(f"{data_str} {hora_str}", "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _classificar_turno(hora: str) -> str:
        """Classifica o turno baseado no horário."""
        try:
            h = int(str(hora)[:2])
            if 6 <= h < 14:
                return "MANHÃ"
            elif 14 <= h < 22:
                return "TARDE"
            else:
                return "NOITE"
        except (ValueError, TypeError):
            return "INDEFINIDO"

    @staticmethod
    def _dec(value: Any) -> Decimal:
        """Converte valor para Decimal."""
        try:
            return Decimal(str(value or 0))
        except Exception:
            return Decimal("0")

    def auditar_abastecimentos(
        self,
        abastecimentos: list[dict[str, Any]],
        pagamentos: list[dict[str, Any]] | None = None,
        agora: datetime | None = None,
    ) -> PistaAuditResult:
        """
        Executa auditoria completa de abastecimentos.
        
        Args:
            abastecimentos: Lista de abastecimentos do período
            pagamentos: Lista de pagamentos TEF/cartão para cruzamento
            agora: Timestamp atual (para testes)
        
        Returns:
            PistaAuditResult com anomalias detectadas
        """
        agora = agora or datetime.now()
        
        pendentes: list[AbastecimentoPendente] = []
        divergencias: list[DivergenciaPagamento] = []
        
        pagamentos_map: dict[str, dict[str, Any]] = {}
        if pagamentos:
            for pag in pagamentos:
                key = f"{pag.get('abastecimento_codigo', '')}_{pag.get('venda_codigo', '')}"
                if key and key != "_":
                    pagamentos_map[key] = pag

        for abast in abastecimentos:
            abast_id = int(abast.get("codigo") or abast.get("id") or 0)
            data = str(abast.get("data") or "")
            hora = str(abast.get("hora") or "")
            litros = self._dec(abast.get("quantidadeLitros") or abast.get("litros") or 0)
            valor = self._dec(abast.get("valorVenda") or abast.get("valor") or 0)
            empresa_codigo = int(abast.get("empresaCodigo") or 0)
            empresa_nome = str(abast.get("empresaNome") or FILIAIS.get(empresa_codigo, ""))
            bico = int(abast.get("bico") or abast.get("numeroBico") or 0)
            produto = str(abast.get("produtoDescricao") or abast.get("produto") or "N/D")
            
            frentista_codigo = abast.get("frentistaCodigo") or abast.get("funcionarioCodigo")
            frentista_nome = str(abast.get("frentistaNome") or abast.get("funcionarioNome") or "N/I")
            
            status_nfce = str(abast.get("statusNfce") or abast.get("status") or "PENDENTE").upper()
            turno = self._classificar_turno(hora)
            
            abast_dt = self._parse_datetime(data, hora)
            
            if status_nfce in ("PENDENTE", "EM_ABERTO", "NAO_EMITIDA", ""):
                minutos_pendente = 0
                if abast_dt:
                    delta = agora - abast_dt
                    minutos_pendente = int(delta.total_seconds() / 60)
                
                alerta_tipo = "NORMAL"
                if minutos_pendente > ALERTA_RETENCAO_MINUTOS:
                    alerta_tipo = "ALERTA_RETENCAO"
                
                pendentes.append(AbastecimentoPendente(
                    id=abast_id,
                    data=data,
                    hora=hora,
                    bico=bico,
                    produto=produto,
                    litros=litros,
                    valor=valor,
                    empresa_codigo=empresa_codigo,
                    empresa_nome=empresa_nome,
                    frentista_codigo=frentista_codigo,
                    frentista_nome=frentista_nome,
                    turno=turno,
                    minutos_pendente=minutos_pendente,
                    status_nfce=status_nfce,
                    alerta_tipo=alerta_tipo,
                ))
            
            pag_key = f"{abast_id}_"
            if pag_key in pagamentos_map or any(k.startswith(pag_key) for k in pagamentos_map):
                for key, pag in pagamentos_map.items():
                    if not key.startswith(pag_key):
                        continue
                    
                    meio = str(pag.get("formaPagamento") or pag.get("tipo") or "").upper()
                    if meio not in ("CARTAO", "TEF", "DEBITO", "CREDITO"):
                        continue
                    
                    hora_tef = str(pag.get("horaAutorizacao") or pag.get("hora") or "")
                    pag_dt = self._parse_datetime(data, hora_tef) if hora_tef else None
                    
                    diferenca = 0
                    if abast_dt and pag_dt:
                        diferenca = abs(int((pag_dt - abast_dt).total_seconds() / 60))
                    
                    alerta = "NORMAL"
                    if diferenca > ALERTA_DIVERGENCIA_TEF_MINUTOS:
                        alerta = "ALERTA_DIVERGENCIA_TEF"
                        divergencias.append(DivergenciaPagamento(
                            abastecimento_id=abast_id,
                            data=data,
                            hora_abastecimento=hora,
                            hora_autorizacao_tef=hora_tef or None,
                            meio_pagamento=meio,
                            valor=valor,
                            diferenca_minutos=diferenca,
                            empresa_codigo=empresa_codigo,
                            empresa_nome=empresa_nome,
                            frentista_nome=frentista_nome,
                            alerta_tipo=alerta,
                        ))
        
        resumo = self._build_resumo(abastecimentos, pendentes, divergencias)
        
        periodo = {"inicio": "", "fim": ""}
        if abastecimentos:
            datas = [str(a.get("data", ""))[:10] for a in abastecimentos if a.get("data")]
            if datas:
                periodo = {"inicio": min(datas), "fim": max(datas)}
        
        return PistaAuditResult(
            periodo=periodo,
            resumo=resumo,
            pendentes=pendentes,
            divergencias_pagamento=divergencias,
        )

    def _build_resumo(
        self,
        abastecimentos: list[dict[str, Any]],
        pendentes: list[AbastecimentoPendente],
        divergencias: list[DivergenciaPagamento],
    ) -> ResumoAnomaliasPista:
        """Constrói resumo consolidado de anomalias."""
        
        por_filial: dict[int, ResumoPendentes] = {}
        por_frentista: dict[str, dict[str, Any]] = {}
        por_bico: dict[str, dict[str, Any]] = {}
        por_turno: dict[str, dict[str, Any]] = {}
        
        total_litros = Decimal("0")
        total_valor = Decimal("0")
        alertas_retencao = 0
        
        for p in pendentes:
            total_litros += p.litros
            total_valor += p.valor
            
            if p.alerta_tipo == "ALERTA_RETENCAO":
                alertas_retencao += 1
            
            if p.empresa_codigo not in por_filial:
                por_filial[p.empresa_codigo] = ResumoPendentes(
                    empresa_codigo=p.empresa_codigo,
                    empresa_nome=p.empresa_nome,
                    total_pendentes=0,
                    litros_pendentes=Decimal("0"),
                    valor_pendente=Decimal("0"),
                )
            por_filial[p.empresa_codigo].total_pendentes += 1
            por_filial[p.empresa_codigo].litros_pendentes += p.litros
            por_filial[p.empresa_codigo].valor_pendente += p.valor
            
            frentista_key = p.frentista_nome or "N/I"
            if frentista_key not in por_frentista:
                por_frentista[frentista_key] = {
                    "frentista": frentista_key,
                    "total_pendentes": 0,
                    "litros": Decimal("0"),
                    "valor": Decimal("0"),
                    "alertas": 0,
                }
            por_frentista[frentista_key]["total_pendentes"] += 1
            por_frentista[frentista_key]["litros"] += p.litros
            por_frentista[frentista_key]["valor"] += p.valor
            if p.alerta_tipo == "ALERTA_RETENCAO":
                por_frentista[frentista_key]["alertas"] += 1
            
            bico_key = f"Bico {p.bico} - {p.empresa_nome}"
            if bico_key not in por_bico:
                por_bico[bico_key] = {
                    "bico": p.bico,
                    "filial": p.empresa_nome,
                    "total_pendentes": 0,
                    "litros": Decimal("0"),
                    "valor": Decimal("0"),
                }
            por_bico[bico_key]["total_pendentes"] += 1
            por_bico[bico_key]["litros"] += p.litros
            por_bico[bico_key]["valor"] += p.valor
            
            turno_key = p.turno or "INDEFINIDO"
            if turno_key not in por_turno:
                por_turno[turno_key] = {
                    "turno": turno_key,
                    "total_pendentes": 0,
                    "litros": Decimal("0"),
                    "valor": Decimal("0"),
                    "alertas": 0,
                }
            por_turno[turno_key]["total_pendentes"] += 1
            por_turno[turno_key]["litros"] += p.litros
            por_turno[turno_key]["valor"] += p.valor
            if p.alerta_tipo == "ALERTA_RETENCAO":
                por_turno[turno_key]["alertas"] += 1
        
        return ResumoAnomaliasPista(
            total_abastecimentos=len(abastecimentos),
            total_pendentes=len(pendentes),
            litros_pendentes=total_litros,
            valor_pendente=total_valor,
            alertas_retencao=alertas_retencao,
            alertas_divergencia_tef=len(divergencias),
            por_filial=list(por_filial.values()),
            por_frentista=sorted(
                [self._serialize_decimal(v) for v in por_frentista.values()],
                key=lambda x: x["total_pendentes"],
                reverse=True,
            ),
            por_bico=sorted(
                [self._serialize_decimal(v) for v in por_bico.values()],
                key=lambda x: x["total_pendentes"],
                reverse=True,
            ),
            por_turno=sorted(
                [self._serialize_decimal(v) for v in por_turno.values()],
                key=lambda x: x["total_pendentes"],
                reverse=True,
            ),
        )

    @staticmethod
    def _serialize_decimal(data: dict[str, Any]) -> dict[str, Any]:
        """Converte Decimals para float para serialização."""
        return {
            k: float(v) if isinstance(v, Decimal) else v
            for k, v in data.items()
        }
