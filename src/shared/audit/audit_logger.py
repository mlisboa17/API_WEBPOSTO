"""Immutable Audit Logging: Record all security events."""

import logging
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from enum import Enum
from pathlib import Path
import hashlib


class AuditEventType(str, Enum):
    """Tipos de eventos de auditoria."""

    # Auth events
    TOKEN_CREATED = "token.created"
    TOKEN_VERIFIED = "token.verified"
    TOKEN_EXPIRED = "token.expired"
    TOKEN_INVALID = "token.invalid"
    AUTH_FAILED = "auth.failed"
    AUTH_SUCCESS = "auth.success"

    # Integrity events
    HASH_CALCULATED = "hash.calculated"
    HASH_VERIFIED = "hash.verified"
    HASH_MISMATCH = "hash.mismatch"
    INTEGRITY_FAILED = "integrity.failed"

    # Anomaly events
    ANOMALY_DETECTED = "anomaly.detected"
    ANOMALY_RESOLVED = "anomaly.resolved"
    ANOMALY_HIGH_RISK = "anomaly.high_risk"

    # Data events
    RATEIO_CREATED = "rateio.created"
    RATEIO_MODIFIED = "rateio.modified"
    RATEIO_DELETED = "rateio.deleted"
    SYNC_STARTED = "sync.started"
    SYNC_COMPLETED = "sync.completed"
    SYNC_FAILED = "sync.failed"

    # System events
    CONFIG_CHANGED = "config.changed"
    KEY_ROTATED = "key.rotated"
    BACKUP_CREATED = "backup.created"


class AuditEvent:
    """Event de auditoria imutavel."""

    def __init__(
        self,
        event_type: AuditEventType,
        usuario_id: str,
        empresa_id: str,
        recurso_id: Optional[str] = None,
        recurso_tipo: Optional[str] = None,
        descricao: str = "",
        dados: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Criar evento de auditoria."""
        self.event_id = self._gerar_event_id()
        self.event_type = event_type
        self.usuario_id = usuario_id
        self.empresa_id = empresa_id
        self.recurso_id = recurso_id
        self.recurso_tipo = recurso_tipo
        self.descricao = descricao
        self.dados = dados or {}
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.timestamp = datetime.utcnow()

    def _gerar_event_id(self) -> str:
        """Gerar ID unico do evento."""
        import uuid
        return str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """Converter para dicionario."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "usuario_id": self.usuario_id,
            "empresa_id": self.empresa_id,
            "recurso_id": self.recurso_id,
            "recurso_tipo": self.recurso_tipo,
            "descricao": self.descricao,
            "dados": self.dados,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_json(self) -> str:
        """Converter para JSON."""
        return json.dumps(self.to_dict(), default=str)


class AuditLogger:
    """Logger de auditoria imutavel (append-only)."""

    def __init__(self, log_dir: Path = Path("./audit_logs")):
        """Inicializar audit logger."""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"audit_{datetime.utcnow().date()}.jsonl"
        self.logger = logging.getLogger("audit")

    def registrar_evento(self, event: AuditEvent) -> bool:
        """Registrar evento de auditoria (append-only)."""
        try:
            event_dict = event.to_dict()
            event_json = json.dumps(event_dict, sort_keys=True, default=str)
            hash_evento = hashlib.sha256(event_json.encode()).hexdigest()
            event_dict["hash"] = hash_evento

            with open(self.log_file, "a") as f:
                f.write(json.dumps(event_dict) + "\n")

            self.logger.info(f"Audit event: {event.event_type.value}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to log audit event: {e}")
            return False

    def consultar_eventos(
        self,
        empresa_id: Optional[str] = None,
        usuario_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        desde: Optional[datetime] = None,
        ate: Optional[datetime] = None,
        limite: int = 100,
    ) -> List[Dict[str, Any]]:
        """Consultar eventos de auditoria."""
        eventos = []

        try:
            with open(self.log_file, "r") as f:
                for linha in f:
                    evento = json.loads(linha)

                    if empresa_id and evento["empresa_id"] != empresa_id:
                        continue
                    if usuario_id and evento["usuario_id"] != usuario_id:
                        continue
                    if event_type and evento["event_type"] != event_type.value:
                        continue

                    timestamp = datetime.fromisoformat(evento["timestamp"])
                    if desde and timestamp < desde:
                        continue
                    if ate and timestamp > ate:
                        continue

                    eventos.append(evento)
                    if len(eventos) >= limite:
                        break
        except FileNotFoundError:
            self.logger.warning(f"Audit log file not found: {self.log_file}")

        return eventos

    def validar_integridade(self) -> Tuple[bool, List[str]]:
        """Validar integridade do audit log."""
        erros = []

        try:
            with open(self.log_file, "r") as f:
                linhas = f.readlines()

                for i, linha in enumerate(linhas):
                    try:
                        evento = json.loads(linha)
                        hash_armazenado = evento.pop("hash")
                        evento_str = json.dumps(evento, sort_keys=True, default=str)
                        hash_calculado = hashlib.sha256(evento_str.encode()).hexdigest()

                        if hash_calculado != hash_armazenado:
                            erros.append(f"Linha {i + 1}: Hash mismatch")
                    except json.JSONDecodeError as e:
                        erros.append(f"Linha {i + 1}: JSON error - {e}")
        except FileNotFoundError:
            self.logger.warning(f"Audit log file not found: {self.log_file}")

        valido = len(erros) == 0

        if valido:
            self.logger.info(f"Audit log integrity: OK ({len(linhas)} records)")
        else:
            self.logger.error(f"Audit log integrity failed: {len(erros)} errors")

        return valido, erros
