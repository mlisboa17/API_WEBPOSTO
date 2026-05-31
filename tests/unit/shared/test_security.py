"""
Tests for GROK 4 Security & Audit Layer.

Validate anomaly detection, JWT auth, and audit logging.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from pathlib import Path

from src.shared.security import (
    AnomalyDetector,
    AnomalyScore,
    JWTAuthenticator,
    IntegrityVerifier
)
from src.shared.audit import AuditLogger, AuditEvent, AuditEventType


class TestAnomalyDetector:
    """Test anomaly detection engine."""
    
    def test_detectar_soma_percentuais_valida(self):
        """Testar detecção com soma válida."""
        detector = AnomalyDetector()
        
        score = detector.detectar_soma_percentuais(
            rateio_id="rateio_001",
            empresa_id="emp_001",
            percentuais=[Decimal("50"), Decimal("50")]
        )
        
        assert score.z_score >= 0
        assert score.is_anomaly == False
        assert score.severity == "ok"
        assert "correta" in score.reason
    
    def test_detectar_soma_percentuais_invalida(self):
        """Testar detecção com soma inválida."""
        detector = AnomalyDetector(z_score_threshold=2.0)
        
        score = detector.detectar_soma_percentuais(
            rateio_id="rateio_002",
            empresa_id="emp_001",
            percentuais=[Decimal("30"), Decimal("40"), Decimal("35")]  # Sum = 105%
        )
        
        assert score.is_anomaly == True
        assert score.severity in ["medium", "high"]
    
    def test_detectar_desvios_centros(self):
        """Testar detecção de desvios em centros."""
        detector = AnomalyDetector(z_score_threshold=1.5)
        
        centros = {
            "cc_001": Decimal("20"),
            "cc_002": Decimal("20"),
            "cc_003": Decimal("20"),
            "cc_004": Decimal("100")  # Clear outlier
        }
        
        anomalias = detector.detectar_desvios_centros(
            rateio_id="rateio_003",
            empresa_id="emp_001",
            centros_com_percentuais=centros
        )
        
        # Should detect cc_004 as anomaly
        assert len(anomalias) >= 1
        assert any("cc_004" in a.reason for a in anomalias)
    
    def test_validar_regras_negocio(self):
        """Testar validação de regras de negócio."""
        detector = AnomalyDetector()
        
        valido, erros = detector.validar_regras_negocio(
            rateio_id="rateio_004",
            empresa_id="emp_001",
            soma_percentuais=Decimal("100"),
            valor_total=Decimal("1000.00"),
            centros_rateio=[
                {"id": "cc_001", "percentual": Decimal("100"), "valor": Decimal("1000.00")}
            ]
        )
        
        assert valido == True
        assert len(erros) == 0
    
    def test_validar_regras_negocio_soma_invalida(self):
        """Testar validação com soma inválida."""
        detector = AnomalyDetector()
        
        valido, erros = detector.validar_regras_negocio(
            rateio_id="rateio_005",
            empresa_id="emp_001",
            soma_percentuais=Decimal("95"),  # Invalid
            valor_total=Decimal("1000.00"),
            centros_rateio=[]
        )
        
        assert valido == False
        assert len(erros) > 0


class TestJWTAuthenticator:
    """Test JWT authentication."""
    
    def test_create_and_verify_token(self, tmp_path):
        """Testar criação e verificação de token."""
        auth = JWTAuthenticator(
            private_key_path=tmp_path / "private.pem",
            public_key_path=tmp_path / "public.pem"
        )
        
        # Create token
        token = auth.create_token(
            subject="user_123",
            empresa_id="emp_001",
            roles=["admin"]
        )
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token
        payload = auth.verify_token(token)
        
        assert payload is not None
        assert payload.sub == "user_123"
        assert payload.empresa_id == "emp_001"
        assert "admin" in payload.roles
    
    def test_verify_invalid_token(self, tmp_path):
        """Testar verificação de token inválido."""
        auth = JWTAuthenticator(
            private_key_path=tmp_path / "private.pem",
            public_key_path=tmp_path / "public.pem"
        )
        
        # Try to verify invalid token
        payload = auth.verify_token("invalid.token.here")
        
        assert payload is None


class TestIntegrityVerifier:
    """Test integrity verification."""
    
    def test_calcular_hash(self):
        """Testar cálculo de hash."""
        data = {"empresa_id": "emp_001", "rateio_id": "rateio_001"}
        
        hash1 = IntegrityVerifier.calcular_hash(data)
        hash2 = IntegrityVerifier.calcular_hash(data)
        
        # Same data should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 is 64 hex chars
    
    def test_verificar_integridade_valida(self):
        """Testar verificação de integridade válida."""
        data = {"valor": "teste"}
        hash_esperado = IntegrityVerifier.calcular_hash(data)
        
        valido = IntegrityVerifier.verificar_integridade(data, hash_esperado)
        
        assert valido == True
    
    def test_verificar_integridade_invalida(self):
        """Testar verificação de integridade inválida."""
        data = {"valor": "teste"}
        hash_invalido = "invalid_hash_here_0000000000000000"
        
        valido = IntegrityVerifier.verificar_integridade(data, hash_invalido)
        
        assert valido == False
    
    def test_gerar_cadeia_integridade(self):
        """Testar geração de cadeia de integridade."""
        records = [
            {"id": 1, "valor": "a"},
            {"id": 2, "valor": "b"},
            {"id": 3, "valor": "c"}
        ]
        
        cadeia = IntegrityVerifier.gerar_cadeia_integridade(records)
        
        assert cadeia["total_records"] == 3
        assert len(cadeia["cadeia"]) == 3
        assert cadeia["primeiro_hash"] is not None
        assert cadeia["ultimo_hash"] is not None
    
    def test_validar_cadeia_integridade(self):
        """Testar validação de cadeia."""
        records = [
            {"id": 1, "valor": "a"},
            {"id": 2, "valor": "b"}
        ]
        
        cadeia = IntegrityVerifier.gerar_cadeia_integridade(records)
        
        valido, erro = IntegrityVerifier.validar_cadeia_integridade(cadeia)
        
        assert valido == True
        assert erro is None


class TestAuditLogger:
    """Test audit logging."""
    
    def test_registrar_evento(self, tmp_path):
        """Testar registro de evento."""
        audit = AuditLogger(log_dir=tmp_path)
        
        event = AuditEvent(
            event_type=AuditEventType.RATEIO_CREATED,
            usuario_id="user_1",
            empresa_id="emp_001",
            recurso_id="rateio_001",
            descricao="Test event"
        )
        
        resultado = audit.registrar_evento(event)
        
        assert resultado == True
        
        # Verify file was created
        assert audit.log_file.exists()
    
    def test_consultar_eventos(self, tmp_path):
        """Testar consulta de eventos."""
        audit = AuditLogger(log_dir=tmp_path)
        
        # Register multiple events
        for i in range(3):
            event = AuditEvent(
                event_type=AuditEventType.RATEIO_CREATED,
                usuario_id=f"user_{i}",
                empresa_id="emp_001",
                recurso_id=f"rateio_{i:03d}",
                descricao=f"Event {i}"
            )
            audit.registrar_evento(event)
        
        # Query events
        eventos = audit.consultar_eventos(
            empresa_id="emp_001",
            limite=10
        )
        
        assert len(eventos) == 3
    
    def test_validar_integridade_audit_log(self, tmp_path):
        """Testar validação de integridade do audit log."""
        audit = AuditLogger(log_dir=tmp_path)
        
        # Register event
        event = AuditEvent(
            event_type=AuditEventType.ANOMALY_DETECTED,
            usuario_id="system",
            empresa_id="emp_001",
            descricao="Anomaly detected"
        )
        audit.registrar_evento(event)
        
        # Validate integrity
        valido, erros = audit.validar_integridade()
        
        assert valido == True
        assert len(erros) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
