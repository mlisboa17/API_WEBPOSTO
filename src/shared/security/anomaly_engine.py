"""
Anomaly Engine: Z-Score based detection for rate allocations.

Detecta desvios estatísticos em rateios de centros de custo.
"""

import math
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass
class AnomalyScore:
    """Score de anomalia para um rateio."""
    rateio_id: str
    empresa_id: str
    z_score: float
    is_anomaly: bool
    severity: str  # "low", "medium", "high"
    reason: str


class AnomalyDetector:
    """
    Detector de anomalias usando Z-Score.
    
    Features:
    - Detecta desvios em rateios (soma != 100%)
    - Identificacentros de custo com percentuais inconsistentes
    - Score de severidade baseado em desvio padrão
    """
    
    def __init__(self, z_score_threshold: float = 2.0):
        """
        Inicializar detector.
        
        Args:
            z_score_threshold: Limiar de Z-Score para anomalia
                              (2.0 = ~95% confiança)
        """
        self.z_score_threshold = z_score_threshold
    
    def detectar_soma_percentuais(
        self,
        rateio_id: str,
        empresa_id: str,
        percentuais: List[Decimal],
        esperado: Decimal = Decimal("100.00")
    ) -> AnomalyScore:
        """
        Detectar anomalia em soma de percentuais.
        
        Args:
            rateio_id: ID do rateio
            empresa_id: ID da empresa
            percentuais: Lista de percentuais
            esperado: Soma esperada (padrão 100%)
        
        Returns:
            AnomalyScore com resultado da detecção
        """
        soma = sum(percentuais)
        desvio = abs(soma - esperado)
        
        # Calcular Z-Score (baseado em desvio percentual)
        if len(percentuais) > 1:
            media = soma / len(percentuais)
            variancia = sum((p - media) ** 2 for p in percentuais) / len(percentuais)
            desvio_padrao = math.sqrt(float(variancia))
            
            if desvio_padrao > 0:
                z_score = float(desvio) / desvio_padrao
            else:
                z_score = 0.0
        else:
            z_score = float(desvio)
        
        # Determinar severidade
        if desvio == Decimal("0"):
            severity = "ok"
            is_anomaly = False
            reason = "Soma de percentuais correta"
        
        elif desvio <= Decimal("1"):
            severity = "low"
            is_anomaly = z_score > self.z_score_threshold
            reason = f"Soma = {soma}% (desvio: {desvio}%)"
        
        elif desvio <= Decimal("5"):
            severity = "medium"
            is_anomaly = True
            reason = f"Soma = {soma}% (desvio: {desvio}%) - Medium"
        
        else:
            severity = "high"
            is_anomaly = True
            reason = f"Soma = {soma}% (desvio: {desvio}%) - High risk!"
        
        logger.info(
            f"Rateio {rateio_id}: Z-Score={z_score:.2f}, "
            f"Soma={soma}%, Severidade={severity}"
        )
        
        return AnomalyScore(
            rateio_id=rateio_id,
            empresa_id=empresa_id,
            z_score=z_score,
            is_anomaly=is_anomaly,
            severity=severity,
            reason=reason
        )
    
    def detectar_desvios_centros(
        self,
        rateio_id: str,
        empresa_id: str,
        centros_com_percentuais: Dict[str, Decimal]
    ) -> List[AnomalyScore]:
        """
        Detectar desvios em centros de custo individuais.
        
        Args:
            rateio_id: ID do rateio
            empresa_id: ID da empresa
            centros_com_percentuais: Dict {centro_id: percentual}
        
        Returns:
            Lista de AnomalyScores para cada desvio
        """
        anomalias = []
        
        percentuais = list(centros_com_percentuais.values())
        media = sum(percentuais) / len(percentuais) if percentuais else Decimal("0")
        
        # Calcular desvio padrão
        if len(percentuais) > 1:
            variancia = sum((p - media) ** 2 for p in percentuais) / len(percentuais)
            desvio_padrao = math.sqrt(float(variancia))
        else:
            desvio_padrao = 0.0
        
        # Analisar cada centro
        for centro_id, percentual in centros_com_percentuais.items():
            if desvio_padrao > 0:
                z_score = abs(float(percentual - media)) / desvio_padrao
            else:
                z_score = 0.0
            
            is_anomaly = z_score > self.z_score_threshold
            
            if is_anomaly:
                severity = "high" if z_score > 3.0 else "medium"
                
                anomalia = AnomalyScore(
                    rateio_id=rateio_id,
                    empresa_id=empresa_id,
                    z_score=z_score,
                    is_anomaly=True,
                    severity=severity,
                    reason=f"Centro {centro_id}: {percentual}% (Z-Score: {z_score:.2f})"
                )
                
                anomalias.append(anomalia)
                logger.warning(f"Anomalia detectada: {anomalia.reason}")
        
        return anomalias
    
    def validar_regras_negocio(
        self,
        rateio_id: str,
        empresa_id: str,
        soma_percentuais: Decimal,
        valor_total: Decimal,
        centros_rateio: List[Dict]
    ) -> Tuple[bool, List[str]]:
        """
        Validar regras de negócio para segurança.
        
        Args:
            rateio_id: ID do rateio
            empresa_id: ID da empresa
            soma_percentuais: Soma dos percentuais
            valor_total: Valor total do rateio
            centros_rateio: Lista de centros com dados
        
        Returns:
            (válido, lista_de_erros)
        """
        erros = []
        
        # Regra 1: Soma percentuais = 100%
        if soma_percentuais != Decimal("100"):
            erros.append(
                f"Soma de percentuais deve ser 100% (encontrado: {soma_percentuais}%)"
            )
        
        # Regra 2: Valor total > 0
        if valor_total <= Decimal("0"):
            erros.append("Valor total deve ser positivo")
        
        # Regra 3: Número de centros >= 1
        if len(centros_rateio) < 1:
            erros.append("Rateio deve ter pelo menos 1 centro de custo")
        
        # Regra 4: Cada centro tem valor > 0
        for centro in centros_rateio:
            if centro.get("valor", Decimal("0")) <= Decimal("0"):
                erros.append(
                    f"Centro {centro.get('id')}: valor deve ser positivo"
                )
        
        # Regra 5: Percentuais válidos (0-100)
        for centro in centros_rateio:
            pct = centro.get("percentual", Decimal("0"))
            if pct < Decimal("0") or pct > Decimal("100"):
                erros.append(
                    f"Centro {centro.get('id')}: percentual deve estar entre 0-100%"
                )
        
        valido = len(erros) == 0
        
        if not valido:
            logger.error(f"Rateio {rateio_id} falhou validação: {erros}")
        
        return valido, erros
