"""
Integrity Verification: SHA-256 hashing for sync records.

Garantiza integridade dos registros de sincronização.
"""

import hashlib
import logging
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class IntegrityVerifier:
    """
    Verificador de integridade usando SHA-256.
    
    Features:
    - Hash de registros de sincronização
    - Verificação de alterações (mutabilidade)
    - Cadeia de integridade (blockchain-like)
    """
    
    ALGORITHM = "sha256"
    
    @staticmethod
    def calcular_hash(data: Dict[str, Any]) -> str:
        """
        Calcular SHA-256 hash de dados.
        
        Args:
            data: Dicionário de dados
        
        Returns:
            Hash SHA-256 em hexadecimal
        """
        # Serializar dados em JSON canonicalizad (sorted keys)
        json_str = json.dumps(data, sort_keys=True, default=str)
        
        # Calcular SHA-256
        hash_obj = hashlib.sha256(json_str.encode())
        hash_hex = hash_obj.hexdigest()
        
        logger.debug(f"Calculated hash: {hash_hex}")
        
        return hash_hex
    
    @staticmethod
    def verificar_integridade(
        data: Dict[str, Any],
        hash_esperado: str
    ) -> bool:
        """
        Verificar integridade de dados.
        
        Args:
            data: Dados a verificar
            hash_esperado: Hash esperado
        
        Returns:
            True se íntegro, False se alterado
        """
        hash_calculado = IntegrityVerifier.calcular_hash(data)
        
        if hash_calculado == hash_esperado:
            logger.info("Integrity check: OK")
            return True
        else:
            logger.error(
                f"Integrity check failed: "
                f"expected {hash_esperado}, got {hash_calculado}"
            )
            return False
    
    @staticmethod
    def gerar_cadeia_integridade(
        records: list[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Gerar cadeia de integridade (blockchain-like).
        
        Args:
            records: Lista de registros
        
        Returns:
            Dicionário com cadeia
        """
        cadeia = []
        hash_anterior = None
        
        for i, record in enumerate(records):
            # Adicionar hash anterior ao record
            if hash_anterior:
                record["hash_anterior"] = hash_anterior
            
            # Calcular hash do record
            hash_atual = IntegrityVerifier.calcular_hash(record)
            
            cadeia.append({
                "index": i,
                "timestamp": datetime.utcnow().isoformat(),
                "hash": hash_atual,
                "hash_anterior": hash_anterior,
                "dados": record
            })
            
            hash_anterior = hash_atual
        
        logger.info(f"Generated integrity chain with {len(cadeia)} records")
        
        return {
            "total_records": len(cadeia),
            "primeiro_hash": cadeia[0]["hash"] if cadeia else None,
            "ultimo_hash": cadeia[-1]["hash"] if cadeia else None,
            "cadeia": cadeia
        }
    
    @staticmethod
    def validar_cadeia_integridade(
        cadeia: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validar cadeia de integridade.
        
        Args:
            cadeia: Dicionário com cadeia
        
        Returns:
            (válido, mensagem_erro)
        """
        registros = cadeia.get("cadeia", [])
        
        if not registros:
            return True, None  # Cadeia vazia é válida
        
        # Verificar primeiro registro (sem hash_anterior)
        primeiro = registros[0]
        primeiro_hash = IntegrityVerifier.calcular_hash(primeiro["dados"])
        
        if primeiro_hash != primeiro["hash"]:
            msg = f"Primeiro registro corrompido: hash mismatch"
            logger.error(msg)
            return False, msg
        
        # Verificar sequência de hashes
        for i in range(1, len(registros)):
            registro = registros[i]
            registro_anterior = registros[i - 1]
            
            # Hash anterior deve ser igual ao hash do registro anterior
            if registro["hash_anterior"] != registro_anterior["hash"]:
                msg = f"Cadeia quebrada no registro {i}: hash anterior mismatch"
                logger.error(msg)
                return False, msg
            
            # Recalcular hash do registro
            hash_calculado = IntegrityVerifier.calcular_hash(registro["dados"])
            
            if hash_calculado != registro["hash"]:
                msg = f"Registro {i} corrompido: hash mismatch"
                logger.error(msg)
                return False, msg
        
        logger.info(f"Integrity chain validation: OK ({len(registros)} records)")
        return True, None

