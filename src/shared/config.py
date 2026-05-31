"""
Configuração centralizada para sistema multi-tenant.
Responsabilidade: Gerenciar variáveis de ambiente e configurações por tenant.
"""

from pydantic_settings import BaseSettings
from typing import Optional, Dict, List
import os
from functools import lru_cache


class TenantConfig:
    """Configuração por tenant (empresa)."""
    
    def __init__(self, 
                 empresa_id: str,
                 nome_empresa: str,
                 webposto_token: str,
                 mongodb_url: str,
                 redis_url: str,
                 rate_limit: Dict[str, int] = None):
        self.empresa_id = empresa_id
        self.nome_empresa = nome_empresa
        self.webposto_token = webposto_token
        self.mongodb_url = mongodb_url
        self.redis_url = redis_url
        self.rate_limit = rate_limit or {
            "requests_per_hour": 1000,
            "requests_per_minute": 100,
            "concurrent_max": 10
        }


class GlobalSettings(BaseSettings):
    """Configurações globais do sistema."""
    
    # Ambiente
    ENV: str = os.getenv("ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # MongoDB Global (admin database)
    MONGODB_ADMIN_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_ADMIN_DB: str = os.getenv("MONGODB_DB", "webposto_admin")
    
    # Redis/Valkey
    REDIS_MASTER_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_CLUSTER_URLS: List[str] = os.getenv(
        "REDIS_CLUSTER", 
        "redis://localhost:6380,redis://localhost:6381,redis://localhost:6382"
    ).split(",")
    
    # Prometheus
    PROMETHEUS_PORT: int = int(os.getenv("PROMETHEUS_PORT", "9091"))
    
    # Multi-tenant
    MULTI_TENANT_ENABLED: bool = True
    TENANTS_CONFIG_FILE: str = os.getenv("TENANTS_CONFIG_FILE", "./config/tenants.json")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_global_settings() -> GlobalSettings:
    """Retorna instância singleton de configurações globais."""
    return GlobalSettings()


class TenantRegistry:
    """Registrador centralizado de tenants (empresas)."""
    
    def __init__(self):
        self._tenants: Dict[str, TenantConfig] = {}
    
    def register_tenant(self, config: TenantConfig) -> None:
        """Registra um novo tenant."""
        self._tenants[config.empresa_id] = config
    
    def get_tenant(self, empresa_id: str) -> Optional[TenantConfig]:
        """Recupera configuração de um tenant."""
        return self._tenants.get(empresa_id)
    
    def list_tenants(self) -> List[str]:
        """Lista todos os IDs de tenants registrados."""
        return list(self._tenants.keys())
    
    def remove_tenant(self, empresa_id: str) -> bool:
        """Remove um tenant do registro."""
        if empresa_id in self._tenants:
            del self._tenants[empresa_id]
            return True
        return False


# Singleton global
tenant_registry = TenantRegistry()
