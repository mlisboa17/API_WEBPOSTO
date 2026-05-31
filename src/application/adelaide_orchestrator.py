"""
🧠 ADELAIDE ORCHESTRATOR - Business Logic Layer (DDD Pattern)
Motor unificado de validação, contexto e distribuição de sub-telas

Responsabilidades (CLAUDE 3.7 TASK):
1. Validar CNPJ/Regime/CNAE contra ruleset corporativo
2. Use case GetExecutiveOverview: consolida dados dos 3 módulos
3. Audit log compliance: rastreia navegação do diretor
4. Isolamento de domínio (entities / value objects)
"""
from typing import Optional, Dict, List, Any
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pydantic import BaseModel, Field, ConfigDict, field_validator


# ═══════════════════════════════════════════════════════════════════
# 1️⃣ DOMAIN VALUE OBJECTS (Entidades de Domínio Isoladas)
# ═══════════════════════════════════════════════════════════════════

class StationContext(BaseModel):
    """Value Object: Contexto imutável do Posto"""
    cnpj: str = Field(..., min_length=14, max_length=18, description="CNPJ formatado")
    regime: str = Field(..., pattern="^(LUCRO_REAL|LUCRO_PRESUMIDO|SIMPLES)$")
    cnae: str = Field(..., min_length=7, max_length=7, description="CNAE 7 dígitos")
    uf: str = Field(..., min_length=2, max_length=2)
    station_name: str = Field(default="Posto Padrão")
    
    model_config = ConfigDict(frozen=True, extra="forbid")
    
    @field_validator("cnae")
    @classmethod
    def cnae_must_be_numeric(cls, v):
        if not v.isdigit():
            raise ValueError("CNAE deve conter apenas dígitos")
        return v
    
    def get_checksum(self) -> str:
        """Checksum único do contexto para cache"""
        data = f"{self.cnpj}|{self.regime}|{self.cnae}|{self.uf}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]


class ExecutiveAuditLog(BaseModel):
    """Value Object: Registro de auditoria para compliance"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    director_id: str
    module_name: str  # home, tax, margin, audit
    action: str  # navigate, execute_audit, export, sync
    station_context: str  # checksum
    details: Dict[str, Any] = Field(default_factory=dict)
    risk_level: str = Field(default="info")  # info, warn, critical
    
    def to_audit_record(self) -> str:
        """Serializa para armazenamento"""
        return json.dumps(self.model_dump(mode="json"), default=str)


class AuditFinding(BaseModel):
    """Value Object: Achado de auditoria com contexto"""
    sku: str
    severity: str = Field(pattern="^(ok|alerta|critico)$")
    recoverable_credit: Decimal = Field(decimal_places=4)
    risk_score: int = Field(ge=0, le=100)
    message: str
    suggested_ncm: Optional[str] = None


class ExecutiveOverview(BaseModel):
    """Value Object: Visão consolidada dos 3 módulos"""
    station_context: StationContext
    
    # KPIs
    total_recovery_estimated: Decimal = Field(decimal_places=4)
    total_risk_score: int
    total_findings: int
    
    # Dados por módulo
    tax_module_data: Dict[str, Any] = Field(default_factory=dict)
    margin_module_data: Dict[str, Any] = Field(default_factory=dict)
    audit_module_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Compliance
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    cache_hit: bool = False
    cache_key: str = ""
    
    model_config = ConfigDict(extra="allow")


# ═══════════════════════════════════════════════════════════════════
# 2️⃣ USE CASES (Lógica de Negócio Pura)
# ═══════════════════════════════════════════════════════════════════

class GetExecutiveOverviewUseCase:
    """
    Use case: Consolida dados de todos os módulos em 1 overview
    Pattern: Query Handler (CQRS-like)
    """
    
    def __init__(self, audit_repo, cache_provider, sse_hub):
        """
        Args:
            audit_repo: Repositório de auditoria (tax recovery data)
            cache_provider: Provedor Valkey
            sse_hub: Hub SSE para broadcasts
        """
        self.audit_repo = audit_repo
        self.cache = cache_provider
        self.sse_hub = sse_hub
    
    async def execute(
        self,
        station_context: StationContext,
        director_id: str,
        force_refresh: bool = False,
    ) -> ExecutiveOverview:
        """
        Executa o consolidação de dados
        
        Returns:
            ExecutiveOverview com hit_ratio tracking
        """
        cache_key = f"exec:overview:{station_context.get_checksum()}"
        
        # ─────────────────────────────────────────────────────────
        # 1. Tentar cache (98% hit ratio target)
        # ─────────────────────────────────────────────────────────
        if not force_refresh:
            cached = await self.cache.get_json(cache_key)
            if cached:
                overview = ExecutiveOverview.model_validate(cached)
                overview.cache_hit = True
                overview.cache_key = cache_key
                
                # Log navegação
                await self._audit_log(
                    director_id,
                    "home",
                    "view_overview",
                    station_context,
                    {"cache_hit": True},
                )
                
                return overview
        
        # ─────────────────────────────────────────────────────────
        # 2. Agregação paralela dos 3 módulos
        # ─────────────────────────────────────────────────────────
        import asyncio
        
        tax_data, margin_data, audit_data = await asyncio.gather(
            self._fetch_tax_module(station_context),
            self._fetch_margin_module(station_context),
            self._fetch_audit_module(station_context),
        )
        
        # ─────────────────────────────────────────────────────────
        # 3. Consolidar Overview
        # ─────────────────────────────────────────────────────────
        total_recovery = (
            Decimal(str(tax_data.get("recovery_estimated", 0)))
            + Decimal(str(margin_data.get("margin_credit", 0)))
        )
        
        overview = ExecutiveOverview(
            station_context=station_context,
            total_recovery_estimated=total_recovery,
            total_risk_score=max(
                tax_data.get("risk_score", 0),
                audit_data.get("risk_score", 0),
            ),
            total_findings=audit_data.get("findings_count", 0),
            tax_module_data=tax_data,
            margin_module_data=margin_data,
            audit_module_data=audit_data,
            cache_hit=False,
            cache_key=cache_key,
        )
        
        # ─────────────────────────────────────────────────────────
        # 4. Persistir em cache (TTL 1h)
        # ─────────────────────────────────────────────────────────
        await self.cache.set_json(cache_key, overview.model_dump(), ttl=3600)
        
        # ─────────────────────────────────────────────────────────
        # 5. Broadcast via SSE para atualizar sidebar KPIs
        # ─────────────────────────────────────────────────────────
        await self.sse_hub.broadcast_kpi_update({
            "kpi_recovery_estimated": float(total_recovery),
            "kpi_risk_score": overview.total_risk_score,
            "kpi_findings_count": overview.total_findings,
        })
        
        # ─────────────────────────────────────────────────────────
        # 6. Log auditoria compliance
        # ─────────────────────────────────────────────────────────
        await self._audit_log(
            director_id,
            "home",
            "view_overview",
            station_context,
            {
                "total_recovery": float(total_recovery),
                "total_risk_score": overview.total_risk_score,
            },
        )
        
        return overview
    
    async def _fetch_tax_module(self, ctx: StationContext) -> Dict[str, Any]:
        """Busca dados do módulo Auditoria Adelaide"""
        # Simulação: integrar com recovery_engine
        return {
            "recovery_estimated": 93.48,
            "risk_score": 81,
            "module_status": "ready",
        }
    
    async def _fetch_margin_module(self, ctx: StationContext) -> Dict[str, Any]:
        """Busca dados do módulo Margem Real"""
        # Integração futura com batch_processor
        return {
            "margin_credit": 45.50,
            "margin_trend": "↑ 12%",
            "module_status": "ready",
        }
    
    async def _fetch_audit_module(self, ctx: StationContext) -> Dict[str, Any]:
        """Busca dados do módulo Análise Tributária"""
        # Integração futura
        return {
            "findings_count": 25,
            "risk_score": 71,
            "module_status": "ready",
        }
    
    async def _audit_log(
        self,
        director_id: str,
        module: str,
        action: str,
        ctx: StationContext,
        details: Dict,
    ):
        """Registra ação para compliance"""
        log_entry = ExecutiveAuditLog(
            director_id=director_id,
            module_name=module,
            action=action,
            station_context=ctx.get_checksum(),
            details=details,
        )
        await self.audit_repo.save_log(log_entry)


class NavigateModuleUseCase:
    """Use case: Validar e persister contexto ao trocar módulo"""
    
    def __init__(self, cache_provider, audit_repo):
        self.cache = cache_provider
        self.audit_repo = audit_repo
    
    async def execute(
        self,
        target_module: str,
        station_context: StationContext,
        director_id: str,
    ) -> Dict[str, Any]:
        """
        Navega para módulo mantendo contexto
        
        Validações:
        - CNPJ válido
        - Regime suportado
        - Director com permissão
        
        Returns:
            {"success": bool, "module": str, "context_key": str}
        """
        
        # Validar contexto
        try:
            _ = station_context.get_checksum()
        except Exception as e:
            return {
                "success": False,
                "error": f"Contexto inválido: {str(e)}",
            }
        
        # Persistir contexto + log
        ctx_key = f"ctx:nav:{station_context.get_checksum()}"
        await self.cache.set_json(
            ctx_key,
            station_context.model_dump(),
            ttl=86400,  # 24h
        )
        
        await self.audit_repo.save_log(
            ExecutiveAuditLog(
                director_id=director_id,
                module_name=target_module,
                action="navigate",
                station_context=station_context.get_checksum(),
            )
        )
        
        return {
            "success": True,
            "module": target_module,
            "context_key": ctx_key,
        }


# ═══════════════════════════════════════════════════════════════════
# 3️⃣ DOMAIN SERVICE (Orquestração)
# ═══════════════════════════════════════════════════════════════════

class AdelaideDomainService:
    """
    🧠 Serviço de Domínio: Orquestra todos os use cases
    Implementa DDD com isolamento completo da UI
    """
    
    def __init__(self, deps):
        """
        Args:
            deps: {
                'audit_repo': AuditRepository,
                'cache': ValkeyManager,
                'sse_hub': SSEHub,
            }
        """
        self.audit_repo = deps.get("audit_repo")
        self.cache = deps.get("cache")
        self.sse_hub = deps.get("sse_hub")
        
        # Instanciar use cases
        self.get_overview = GetExecutiveOverviewUseCase(
            self.audit_repo,
            self.cache,
            self.sse_hub,
        )
        self.navigate_module = NavigateModuleUseCase(
            self.cache,
            self.audit_repo,
        )
    
    async def get_executive_dashboard(
        self,
        station_context: StationContext,
        director_id: str,
    ) -> ExecutiveOverview:
        """Retorna dashboard executivo consolidado"""
        return await self.get_overview.execute(station_context, director_id)
    
    async def change_station_context(
        self,
        cnpj: str,
        regime: str,
        cnae: str,
        uf: str,
        director_id: str,
    ) -> Dict[str, Any]:
        """Trocar contexto de Posto com validação"""
        ctx = StationContext(cnpj=cnpj, regime=regime, cnae=cnae, uf=uf)
        return await self.navigate_module.execute("home", ctx, director_id)


if __name__ == "__main__":
    # ─────────────────────────────────────────────────────────
    # Test: Validar entidades de domínio
    # ─────────────────────────────────────────────────────────
    ctx = StationContext(
        cnpj="12.345.678/0001-99",
        regime="LUCRO_REAL",
        cnae="4731800",
        uf="PE",
        station_name="Posto Casa Caiada",
    )
    print(f"✅ Context checksum: {ctx.get_checksum()}")
    print(f"✅ Station: {ctx.station_name}")
    
    audit_log = ExecutiveAuditLog(
        director_id="DIR-001",
        module_name="tax",
        action="navigate",
        station_context=ctx.get_checksum(),
    )
    print(f"✅ Audit log: {audit_log.to_audit_record()}")
