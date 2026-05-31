"""
Domain Service: ValidadorRateio

Responsabilidades:
- Validar soma de percentuais = 100%
- Validar soma de valores = total
- Detectar CCs ausentes
- Aplicar regras customizadas por empresa
"""

from typing import Optional, Tuple
from decimal import Decimal
from src.domain.entities.empresa import (
    Rateio,
    Empresa,
    RateiConfiguracao,
    DomainException
)


class ValidadorRateio:
    """
    Domain Service: Validador de Rateios.
    
    Encapsula a lógica de validação de rateios conforme
    as regras de negócio da empresa.
    """
    
    def __init__(self, config: RateiConfiguracao):
        """
        Inicializar validador com configuração da empresa.
        
        Args:
            config: RateiConfiguracao com regras da empresa
        """
        self.config = config
    
    def validar(self, rateio: Rateio, empresa: Empresa) -> Tuple[bool, Optional[str]]:
        """
        Validar integridade completa do rateio.
        
        Passos:
        1. Validar soma de valores (value.valor == total)
        2. Validar soma de percentuais (se configurado)
        3. Verificar CCs existem na empresa
        4. Aplicar regras customizadas por tipo
        
        Args:
            rateio: Rateio a validar
            empresa: Empresa proprietária do rateio
            
        Returns:
            (valido: bool, erro: Optional[str])
        """
        try:
            # 1. Validar soma de valores
            resultado_soma, erro_soma = self._validar_soma_valores(rateio)
            if not resultado_soma:
                return (False, erro_soma)
            
            # 2. Validar soma de percentuais (se configurado)
            if self.config.validar_soma_100:
                resultado_pct, erro_pct = self._validar_soma_percentuais(rateio)
                if not resultado_pct:
                    return (False, erro_pct)
            
            # 3. Verificar CCs existem na empresa
            resultado_ccs, erro_ccs = self._validar_centros_custo(rateio, empresa)
            if not resultado_ccs:
                return (False, erro_ccs)
            
            # 4. Aplicar regras customizadas
            resultado_custom, erro_custom = self._validar_regras_customizadas(rateio)
            if not resultado_custom:
                return (False, erro_custom)
            
            return (True, None)
            
        except DomainException as e:
            return (False, f"Erro de domínio: {str(e)}")
        except Exception as e:
            return (False, f"Erro inesperado na validação: {str(e)}")
    
    def _validar_soma_valores(self, rateio: Rateio) -> Tuple[bool, Optional[str]]:
        """Validar que soma de valores = valor_total."""
        try:
            if not rateio.centros_custo:
                return (False, "Rateio deve ter pelo menos um centro de custo")
            
            soma_valores = sum(
                Decimal(str(r.valor.valor)) 
                for r in rateio.centros_custo
            )
            valor_total = Decimal(str(rateio.valor_total.valor))
            
            # Permitir margem de erro (centavos por arredondamento)
            diferenca = abs(soma_valores - valor_total)
            if diferenca > Decimal('0.01'):
                return (False, 
                    f"Soma de valores ({soma_valores:.2f}) ≠ total ({valor_total:.2f})")
            
            return (True, None)
        except Exception as e:
            return (False, f"Erro ao validar soma de valores: {str(e)}")
    
    def _validar_soma_percentuais(self, rateio: Rateio) -> Tuple[bool, Optional[str]]:
        """Validar que soma de percentuais = 100%."""
        try:
            soma_percentuais = sum(
                Decimal(str(r.percentual)) 
                for r in rateio.centros_custo
            )
            
            diferenca = abs(soma_percentuais - Decimal('100'))
            if diferenca > Decimal('0.01'):
                return (False,
                    f"Soma de percentuais ({soma_percentuais:.2f}%) ≠ 100%")
            
            return (True, None)
        except Exception as e:
            return (False, f"Erro ao validar soma de percentuais: {str(e)}")
    
    def _validar_centros_custo(self, rateio: Rateio, 
                               empresa: Empresa) -> Tuple[bool, Optional[str]]:
        """Validar que todos os CCs do rateio existem na empresa."""
        try:
            ccs_empresa_ids = {
                cc.centro_custo_id.valor 
                for cc in empresa.centros_custo
            }
            ccs_rateio_ids = {
                cc.centro_custo_id.valor 
                for cc in rateio.centros_custo
            }
            
            ccs_ausentes = ccs_rateio_ids - ccs_empresa_ids
            
            if ccs_ausentes:
                if not self.config.permitir_centros_ausentes:
                    ccs_str = ", ".join(sorted(ccs_ausentes))
                    return (False, f"CCs não existem na empresa: {ccs_str}")
            
            return (True, None)
        except Exception as e:
            return (False, f"Erro ao validar CCs: {str(e)}")
    
    def _validar_regras_customizadas(self, rateio: Rateio) -> Tuple[bool, Optional[str]]:
        """Aplicar regras de rateio customizadas por empresa."""
        try:
            if self.config.tipo_rateio == "uniforme":
                # Todos os CCs devem ter mesmo percentual
                percentuais = [cc.percentual for cc in rateio.centros_custo]
                if percentuais and not all(p == percentuais[0] for p in percentuais):
                    return (False, 
                        "Rateio uniforme: todos os CCs devem ter percentuais iguais")
            
            elif self.config.tipo_rateio == "proporcional":
                # Percentuais podem variar (apenas verificar soma = 100)
                pass
            
            elif self.config.tipo_rateio == "customizado":
                # Aplicar regras específicas se houver
                pass
            
            return (True, None)
        except Exception as e:
            return (False, f"Erro ao validar regras customizadas: {str(e)}")
    
    def validar_lote(self, rateios: list[Rateio], 
                    empresa: Empresa) -> dict:
        """
        Validar múltiplos rateios em lote.
        
        Args:
            rateios: Lista de rateios a validar
            empresa: Empresa proprietária
            
        Returns:
            Dict com resultado consolidado
        """
        resultados = []
        validos = 0
        invalidos = 0
        erros = []
        
        for rateio in rateios:
            resultado, erro = self.validar(rateio, empresa)
            
            if resultado:
                validos += 1
                resultados.append({
                    'rateio_id': rateio.rateio_id.valor,
                    'valido': True,
                    'erro': None
                })
            else:
                invalidos += 1
                erros.append(erro)
                resultados.append({
                    'rateio_id': rateio.rateio_id.valor,
                    'valido': False,
                    'erro': erro
                })
        
        return {
            'total': len(rateios),
            'validos': validos,
            'invalidos': invalidos,
            'resultados': resultados,
            'erros': erros,
            'sucesso': invalidos == 0
        }
