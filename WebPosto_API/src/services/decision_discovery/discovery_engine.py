"""
Decision Discovery Engine — Discovery Engine

Orquestrador principal do sistema de descoberta de decisões.

Executa múltiplos detectores, compara resultados e escolhe
automaticamente a decisão mais importante para o proprietário.

Princípio 19: O LOGOS deve encontrar primeiro a decisão mais valiosa
antes de aumentar a quantidade de decisões apresentadas.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import List, Optional, Dict, Any

from src.services.decision_discovery.base_detector import BaseDetector
from src.services.decision_discovery.models import (
    DecisionCandidate,
    DiscoveryResult,
    TenantAnalysisRecord,
)
from src.services.owner_analysis_models import TenantProgressCallback
from src.services.tenant_discovery_service import DiscoveredTenant
from src.services.decision_discovery.priority_calculator import PriorityScoreCalculator


class DecisionDiscoveryEngine:
    """
    Motor de descoberta de decisões.
    
    Responsabilidades:
    1. Executar detectores registrados
    2. Validar candidatos
    3. Calcular Priority Score
    4. Ordenar por prioridade
    5. Retornar Top N decisões
    6. Registrar log completo
    
    Filosofia:
    - Detectores competem entre si
    - Melhor decisão vence automaticamente
    - Nenhuma decisão fraca é apresentada
    - Transparência total no processo
    """
    
    def __init__(self):
        """Inicializa o Discovery Engine."""
        self._detectors: List[BaseDetector] = []
        self._priority_calculator = PriorityScoreCalculator()
        self._execution_log: List[Dict[str, Any]] = []
    
    def register_detector(self, detector: BaseDetector) -> None:
        """
        Registra um detector no engine.
        
        Args:
            detector: Instância de detector que implementa BaseDetector
        """
        self._detectors.append(detector)
        self._log(f"Detector registered: {detector.detector_name}")
    
    async def discover(
        self,
        tenant_code: str,
        data_inicial: str,
        data_final: str,
        top_n: int = 1,
        **kwargs: Any
    ) -> DiscoveryResult:
        """
        Executa o processo de descoberta de decisões.
        
        Fluxo:
        1. Executar todos os detectores (em paralelo)
        2. Coletar candidatos válidos
        3. Calcular Priority Score para cada
        4. Ordenar por Priority Score
        5. Retornar Top N
        
        Args:
            tenant_code: Código do tenant (empresa)
            data_inicial: Data inicial (YYYY-MM-DD)
            data_final: Data final (YYYY-MM-DD)
            top_n: Quantidade de decisões a retornar (padrão: 1)
            **kwargs: Argumentos adicionais
        
        Returns:
            DiscoveryResult com decisões encontradas e metadados
        """
        start_time = time.time()
        self._clear_log()
        
        self._log(f"Discovery started: tenant={tenant_code}, period={data_inicial} to {data_final}, top_n={top_n}")
        
        # 1. Executar todos os detectores (em paralelo)
        candidates = await self._execute_detectors(
            tenant_code=tenant_code,
            data_inicial=data_inicial,
            data_final=data_final,
            **kwargs
        )
        
        self._log(f"Candidates collected: {len(candidates)} total")
        
        # 2. Validar candidatos
        valid_candidates, rejected = self._validate_candidates(candidates)
        
        self._log(f"Candidates validated: {len(valid_candidates)} valid, {len(rejected)} rejected")
        
        # 3. Calcular Priority Score para candidatos válidos
        scored_candidates = self._score_candidates(valid_candidates)
        
        # 4. Ordenar por Priority Score (decrescente)
        sorted_candidates = sorted(
            scored_candidates,
            key=lambda c: c.priority_value,
            reverse=True
        )
        
        self._log(f"Candidates scored and sorted: top priority={sorted_candidates[0].priority_value if sorted_candidates else 0}")
        
        # 5. Selecionar Top N
        top_candidates = sorted_candidates[:top_n]
        
        # 6. Criar resultado
        execution_time_ms = (time.time() - start_time) * 1000
        
        result = DiscoveryResult(
            top_decision=top_candidates[0] if top_candidates else None,
            all_candidates=top_candidates,
            rejected_candidates=rejected,
            execution_time_ms=execution_time_ms,
            detectors_executed=[d.detector_name for d in self._detectors],
            message="" if top_candidates else "Hoje não encontramos nenhuma decisão com impacto e confiança suficientes para recomendar uma ação."
        )
        
        self._log(f"Discovery completed in {execution_time_ms:.2f}ms")
        
        return result

    async def discover_all_tenants(
        self,
        tenants: List[DiscoveredTenant],
        data_inicial: str,
        data_final: str,
        top_n: int = 5,
        on_tenant_progress: TenantProgressCallback | None = None,
        **kwargs: Any,
    ) -> DiscoveryResult:
        """Executa detectores para cada tenant descoberto e agrega candidatos globalmente."""
        start_time = time.time()
        self._clear_log()

        if not tenants:
            return DiscoveryResult(
                execution_time_ms=(time.time() - start_time) * 1000,
                message="Nenhum tenant disponível para análise.",
            )

        all_valid: List[DecisionCandidate] = []
        all_rejected: List[Dict[str, Any]] = []
        tenant_records: List[TenantAnalysisRecord] = []
        tenant_ids: List[str] = [t.tenant_id for t in tenants]
        tenants_total = len(tenants)
        tenants_completed = 0
        progress_lock = asyncio.Lock()
        max_concurrency = max(1, int(os.getenv("OWNER_ANALYSIS_MAX_CONCURRENCY", "1")))

        async def _analyze_tenant(
            tenant: DiscoveredTenant,
        ) -> tuple[TenantAnalysisRecord, List[DecisionCandidate], List[Dict[str, Any]]]:
            tenant_start = time.time()
            tenant_kwargs = {
                **kwargs,
                "tenant_name": tenant.tenant_name,
                "credential_alias": tenant.credential_alias,
                "webposto_api_key": self._resolve_tenant_api_key(tenant),
                "analysis_id": kwargs.get("analysis_id"),
            }

            self._log(
                f"Tenant analysis started: tenant={tenant.tenant_id}, "
                f"credential={tenant.credential_alias}"
            )

            try:
                candidates = await self._execute_detectors(
                    tenant_code=tenant.tenant_id,
                    data_inicial=data_inicial,
                    data_final=data_final,
                    **tenant_kwargs,
                )
                valid, rejected = self._validate_candidates(candidates)

                record = TenantAnalysisRecord(
                    tenant_id=tenant.tenant_id,
                    tenant_name=tenant.tenant_name,
                    empresa_codigo=str(tenant.empresa_codigo),
                    credential_alias=tenant.credential_alias,
                    status="ANALYZED",
                    detectors_executed=[d.detector_name for d in self._detectors],
                    candidates_found=len(candidates),
                    decisions_found=len(valid),
                    observations_found=len(rejected),
                    requests_count=2 * len(self._detectors),
                    execution_time_ms=int((time.time() - tenant_start) * 1000),
                    period_start=data_inicial,
                    period_end=data_final,
                )
                return record, valid, rejected
            except Exception as exc:
                self._log(
                    f"Tenant analysis failed: tenant={tenant.tenant_id} error={exc}",
                    level="error",
                )
                record = TenantAnalysisRecord(
                    tenant_id=tenant.tenant_id,
                    tenant_name=tenant.tenant_name,
                    empresa_codigo=str(tenant.empresa_codigo),
                    credential_alias=tenant.credential_alias,
                    status="FAILED",
                    execution_time_ms=int((time.time() - tenant_start) * 1000),
                    period_start=data_inicial,
                    period_end=data_final,
                    error=str(exc)[:220],
                )
                return record, [], []

        async def _run_with_progress(tenant: DiscoveredTenant) -> None:
            nonlocal tenants_completed
            record, valid, rejected = await _analyze_tenant(tenant)
            async with progress_lock:
                all_valid.extend(valid)
                all_rejected.extend(rejected)
                tenant_records.append(record)
                tenants_completed += 1
                if on_tenant_progress is not None:
                    await on_tenant_progress(record, tenants_completed, tenants_total)

        if max_concurrency <= 1:
            for tenant in tenants:
                await _run_with_progress(tenant)
        else:
            sem = asyncio.Semaphore(max_concurrency)

            async def _bounded(tenant: DiscoveredTenant) -> None:
                async with sem:
                    await _run_with_progress(tenant)

            await asyncio.gather(*[_bounded(t) for t in tenants])

        tenant_records.sort(key=lambda r: tenant_ids.index(r.tenant_id))

        scored_candidates = self._score_candidates(all_valid)
        sorted_candidates = sorted(
            scored_candidates,
            key=lambda c: c.priority_value,
            reverse=True,
        )
        top_candidates = sorted_candidates[:top_n]
        execution_time_ms = (time.time() - start_time) * 1000

        return DiscoveryResult(
            top_decision=top_candidates[0] if top_candidates else None,
            all_candidates=top_candidates,
            rejected_candidates=all_rejected,
            execution_time_ms=execution_time_ms,
            detectors_executed=[d.detector_name for d in self._detectors],
            tenant_records=tenant_records,
            tenant_ids=tenant_ids,
            message=(
                ""
                if top_candidates
                else "Hoje não encontramos nenhuma decisão com impacto e confiança suficientes para recomendar uma ação."
            ),
        )

    @staticmethod
    def _resolve_tenant_api_key(tenant: DiscoveredTenant) -> str | None:
        from src.core.webposto_credentials import list_webposto_credentials

        for credential in list_webposto_credentials():
            if credential.env_key == tenant.credential_alias:
                return credential.api_key
        return None
    
    async def _execute_detectors(
        self,
        tenant_code: str,
        data_inicial: str,
        data_final: str,
        **kwargs: Any
    ) -> List[DecisionCandidate]:
        """
        Executa todos os detectores em paralelo.
        
        Args:
            tenant_code: Código do tenant
            data_inicial: Data inicial
            data_final: Data final
            **kwargs: Argumentos adicionais
        
        Returns:
            Lista de candidatos (incluindo None para detectores que não encontraram nada)
        """
        if not self._detectors:
            self._log("No detectors registered", level="warning")
            return []
        
        # Executar detectores em paralelo
        tasks = [
            detector.detect(
                tenant_code=tenant_code,
                data_inicial=data_inicial,
                data_final=data_final,
                **kwargs
            )
            for detector in self._detectors
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filtrar resultados válidos (não None, não exceção)
        candidates = []
        for i, result in enumerate(results):
            detector_name = self._detectors[i].detector_name
            
            if isinstance(result, Exception):
                self._log(f"Detector {detector_name} failed: {str(result)}", level="error")
            elif result is None:
                self._log(f"Detector {detector_name} found no opportunity")
            elif isinstance(result, DecisionCandidate):
                self._log(f"Detector {detector_name} found candidate: {result.title}")
                candidates.append(result)
            elif isinstance(result, list):
                for item in result:
                    if isinstance(item, DecisionCandidate):
                        self._log(f"Detector {detector_name} found candidate: {item.title}")
                        candidates.append(item)
            else:
                self._log(f"Detector {detector_name} returned invalid type: {type(result)}", level="error")
        
        return candidates
    
    def _validate_candidates(
        self,
        candidates: List[DecisionCandidate]
    ) -> tuple[List[DecisionCandidate], List[Dict[str, Any]]]:
        """
        Valida candidatos usando critérios mínimos.
        
        Critérios:
        - Confidence >= 80%
        - Money Found > 0
        - Título não vazio
        - Ações recomendadas não vazias
        
        Args:
            candidates: Lista de candidatos
        
        Returns:
            Tupla (válidos, rejeitados)
        """
        valid = []
        rejected = []
        
        for candidate in candidates:
            if not candidate.is_valid():
                rejection_reason = self._get_rejection_reason(candidate)
                rejected.append({
                    "candidate": candidate.to_dict(),
                    "detector": candidate.detector_name,
                    "title": candidate.title,
                    "reason": rejection_reason,
                    "discard_reason": rejection_reason,
                    "observation_reason": self._get_observation_reason(rejection_reason),
                    "confidence": candidate.confidence,
                    "money_found": candidate.money_found.total_impact(),
                    "confidence_threshold": DecisionCandidate.MIN_DECISION_CONFIDENCE,
                    "financial_impact_threshold": DecisionCandidate.MIN_DECISION_IMPACT_BRL,
                })
                self._log(f"Candidate rejected: {candidate.title} - {rejection_reason}")
            else:
                valid.append(candidate)
        
        return valid, rejected
    
    def _get_rejection_reason(self, candidate: DecisionCandidate) -> str:
        """
        Identifica motivo de rejeição de um candidato.
        
        Args:
            candidate: Candidato rejeitado
        
        Returns:
            Motivo da rejeição
        """
        if candidate.confidence < DecisionCandidate.MIN_DECISION_CONFIDENCE:
            return (
                f"Confidence insuficiente: {candidate.confidence:.0%} "
                f"< {DecisionCandidate.MIN_DECISION_CONFIDENCE:.0%}"
            )
        elif candidate.money_found.total_impact() < DecisionCandidate.MIN_DECISION_IMPACT_BRL:
            impact = candidate.money_found.total_impact()
            return (
                f"Impacto financeiro abaixo do limite de prioridade: "
                f"R$ {impact:,.2f} < R$ {DecisionCandidate.MIN_DECISION_IMPACT_BRL:,.0f}"
            )
        elif candidate.money_found.total_impact() <= 0:
            return "No financial impact (Money Found = 0)"
        elif len(candidate.title) == 0:
            return "No title"
        elif len(candidate.recommended_actions) == 0:
            return "No recommended actions"
        else:
            return "Unknown reason"

    def _get_observation_reason(self, rejection_reason: str) -> str:
        """Mapeia motivo de rejeição para linguagem de observação (BUILD-03A)."""
        lower = rejection_reason.lower()
        if "confidence" in lower:
            return "Confidence ainda insuficiente para recomendar ação."
        if "impacto financeiro" in lower or "financial impact" in lower:
            return "Impacto financeiro abaixo do limite de prioridade."
        return rejection_reason
    
    def _score_candidates(
        self,
        candidates: List[DecisionCandidate]
    ) -> List[DecisionCandidate]:
        """
        Calcula Priority Score para todos os candidatos.
        
        Args:
            candidates: Lista de candidatos válidos
        
        Returns:
            Lista de candidatos com Priority Score calculado
        """
        for candidate in candidates:
            priority_score, priority_value = self._priority_calculator.calculate(candidate)
            candidate.priority_score = priority_score
            candidate.priority_value = priority_value
            
            self._log(f"Candidate scored: {candidate.title} - Priority={priority_value:.2f}")
        
        return candidates
    
    def _log(self, message: str, level: str = "info") -> None:
        """
        Registra evento no log de execução.
        
        Args:
            message: Mensagem
            level: Nível (info, warning, error)
        """
        self._execution_log.append({
            "level": level,
            "message": message,
        })
    
    def _clear_log(self) -> None:
        """Limpa o log de execução."""
        self._execution_log.clear()
    
    def get_execution_log(self) -> List[Dict[str, Any]]:
        """
        Retorna log de execução completo.
        
        Útil para debugging e auditoria.
        """
        return self._execution_log.copy()
