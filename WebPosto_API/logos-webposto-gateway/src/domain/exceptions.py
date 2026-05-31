from typing import Optional


class LogosDomainException(Exception):
    """Base exception for domain errors."""
    pass


class PostoNaoConfiguradoException(LogosDomainException):
    """Levantada quando um Posto não possui credenciais configuradas no SQLite local"""
    
    def __init__(self, posto_id: str):
        self.posto_id = posto_id
        super().__init__(f"Posto '{posto_id}' não configurado no banco de dados local")


class PostoInativoException(LogosDomainException):
    """Levantada quando um Posto tem status 'inativo' nas credenciais"""
    
    def __init__(self, posto_id: str):
        self.posto_id = posto_id
        super().__init__(f"Posto '{posto_id}' está inativo")


class WebPostoIntegracaoException(LogosDomainException):
    """Raised when WebPosto integration fails."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class CacheException(LogosDomainException):
    """Levantada quando há erro no sistema de cache"""
    
    def __init__(self, message: str):
        super().__init__(message)


class DadosInvalidosException(LogosDomainException):
    """Levantada quando os dados recebidos não passam na validação de domínio"""
    
    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"Validação falhou no campo '{field}': {message}")
