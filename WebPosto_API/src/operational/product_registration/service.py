"""Serviço central orquestrador — FASES 3-10."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from .body_builder import create_registration_request, get_default_bono_template
from .checkpoint_store import CheckpointStore
from .duplicate_checker import DuplicateChecker
from .fiscal_resolver import FiscalResolver
from .post_verifier import PostVerifier
from .registration_executor import RegistrationExecutor
from .report_exporter import ReportExporter
from .schemas import ExecutionState, ProductAnalysis, ProductRow
from .spreadsheet_reader import read_products_sheet

logger = logging.getLogger(__name__)


class ProductRegistrationService:
    """Orquestrador do cadastro automático de produtos (FASES 3-10)."""

    def __init__(
        self,
        xlsx_path: Path | str,
        base_url: str = "https://web.qualityautomacao.com.br",
        chave: str | None = None,
        output_dir: Path | str = "reports/product_registration",
        checkpoint_dir: Path | str = "data/product_registration/executions",
    ):
        self.xlsx_path = Path(xlsx_path)
        self.base_url = base_url.rstrip("/")
        self.chave = chave
        self.output_dir = Path(output_dir)
        self.checkpoint_dir = Path(checkpoint_dir)

        self.checkpoint_store = CheckpointStore(checkpoint_dir)
        self.report_exporter = ReportExporter(output_dir)
        self.duplicate_checker = DuplicateChecker()
        self.fiscal_resolver = FiscalResolver()
        self.registration_executor = RegistrationExecutor(
            base_url=base_url,
            chave=chave,
        )
        self.post_verifier = PostVerifier(base_url=base_url, chave=chave)

        self.products: list[ProductRow] = []
        self.analyses: list[ProductAnalysis] = []
        self.metadata: dict[str, Any] = {}
        self.execution_id: str | None = None
        self.execution_state: ExecutionState | None = None

    # ========== FASE 3: Consolidar Pipeline ==========

    async def load_and_validate_spreadsheet(self) -> dict[str, Any]:
        """
        FASE 3 — Ler e validar planilha.
        
        Retorna metadata com hash SHA-256 e contagem.
        """
        logger.info(f"[FASE 3] Lendo planilha: {self.xlsx_path}")

        self.products, self.metadata = read_products_sheet(self.xlsx_path)

        logger.info(
            f"[FASE 3] Planilha carregada: {len(self.products)} produtos, "
            f"hash={self.metadata['file_hash'][:8]}..."
        )

        return self.metadata

    # ========== FASE 5: Pré-Voo Read-Only ==========

    async def analyze_all_products(self) -> list[ProductAnalysis]:
        """
        FASE 5 — Análise preflight de todos os produtos (read-only).
        
        Valida EAN, duplicidade, descrição, preço, NCM, grupo, modelo fiscal, etc.
        """
        logger.info(f"[FASE 5] Analisando {len(self.products)} produtos...")

        self.analyses = []

        for product_row in self.products:
            analysis = ProductAnalysis(
                ean=product_row.ean,
                descricao=product_row.descricao,
                preco_venda=product_row.preco_venda,
                gate="UNKNOWN",
                status="READY_TO_CREATE",
                confidence="HIGH",
                risk_level="BAIXO_RISCO",
                grupo_api_codigo=product_row.grupo_api_codigo,
                centro_api_codigo=product_row.centro_api_codigo,
                ncm=product_row.ncm,
                cest=product_row.cest,
            )

            # 1. Validar EAN
            from .ean_service import validate_ean_strict

            ean_result = validate_ean_strict(product_row.ean)
            if not ean_result["ok"]:
                analysis.status = "BLOCKED"
                analysis.gate = ean_result["gate"]
                analysis.validation_issues.extend(ean_result["issues"])
                analysis.risk_level = "ALTO_RISCO"
            else:
                analysis.ean = ean_result["ean"]
                analysis.field_provenance["ean"] = {
                    "source": "VALIDATED_GTIN",
                    "confidence": "CONFIRMED",
                }

            # 2. Duplicidade (se EAN válido)
            if analysis.gate != "BLOCKED_INVALID_EAN":
                analysis = self.duplicate_checker.check_and_update_analysis(analysis)

            # 3. Validar descrição
            if not analysis.descricao or len(str(analysis.descricao).strip()) < 3:
                analysis.status = "BLOCKED"
                analysis.gate = "BLOCKED_INVALID_DESCRIPTION"
                analysis.validation_issues.append("Descrição inválida ou vazia")
                analysis.risk_level = "ALTO_RISCO"

            # 4. Validar preço
            if analysis.preco_venda is None or analysis.preco_venda <= 0:
                analysis.status = "BLOCKED"
                analysis.gate = "BLOCKED_INVALID_PRICE"
                analysis.validation_issues.append("Preço de venda <= 0")
                analysis.risk_level = "ALTO_RISCO"

            # 5. Resolver modelo fiscal
            if analysis.status == "READY_TO_CREATE":
                analysis = self.fiscal_resolver.resolve(
                    analysis,
                    ncm=analysis.ncm,
                    description=analysis.descricao,
                )

            # 6. Grupo e centro obrigatórios
            if analysis.status == "READY_TO_CREATE":
                if not analysis.grupo_api_codigo or not analysis.centro_api_codigo:
                    analysis.status = "REVIEW_REQUIRED"
                    analysis.validation_issues.append(
                        f"Grupo={analysis.grupo_api_codigo}, "
                        f"Centro={analysis.centro_api_codigo} — informação incompleta"
                    )
                    analysis.risk_level = "MÉDIO_RISCO"

            self.analyses.append(analysis)

        # Contar por status
        by_status = {}
        for a in self.analyses:
            if a.status not in by_status:
                by_status[a.status] = 0
            by_status[a.status] += 1

        logger.info(f"[FASE 5] Análise concluída:")
        for status, count in by_status.items():
            logger.info(f"  {status}: {count}")

        return self.analyses

    # ========== FASE 6: Resumo Pré-Voo ==========

    def print_preflight_summary(self) -> None:
        """FASE 6 — Imprime resumo pré-voo."""
        
        by_status = {}
        for a in self.analyses:
            if a.status not in by_status:
                by_status[a.status] = 0
            by_status[a.status] += 1

        by_risk = {}
        for a in self.analyses:
            if a.risk_level not in by_risk:
                by_risk[a.risk_level] = 0
            by_risk[a.risk_level] += 1

        summary_text = (
            "\n"
            + "=" * 80 + "\n"
            + "PRODUCT BULK REGISTRATION — PRÉ-VOO REPORT\n"
            + "=" * 80 + "\n"
            + f"\nEmpresa: 118508 — CONVENIENCIA 24 HORAS"
            + f"\nPlanilha: {self.xlsx_path.name}"
            + f"\nHash: {self.metadata.get('file_hash', 'N/A')[:16]}...\n"
            + f"TOTAL: {len(self.analyses)}\n"
            + f"READY_TO_CREATE: {by_status.get('READY_TO_CREATE', 0)}\n"
            + f"BLOCKED: {by_status.get('BLOCKED', 0)}\n"
            + f"REVIEW_REQUIRED: {by_status.get('REVIEW_REQUIRED', 0)}\n"
            + f"CREATED_AND_VERIFIED: {by_status.get('CREATED_AND_VERIFIED', 0)}\n"
            + f"\nRISK LEVELS:\n"
            + f"BAIXO_RISCO: {by_risk.get('BAIXO_RISCO', 0)}\n"
            + f"MÉDIO_RISCO: {by_risk.get('MÉDIO_RISCO', 0)}\n"
            + f"ALTO_RISCO: {by_risk.get('ALTO_RISCO', 0)}\n"
            + "=" * 80 + "\n"
            + "Prosseguindo com execução automática...\n"
            + "=" * 80 + "\n"
        )
        print(summary_text)

    # ========== FASES 7-9: Execução ==========

    async def execute_ready_products(self) -> dict[str, Any]:
        """
        FASES 7-9 — Executar produtos READY_TO_CREATE.
        
        POST sequencial, verificação GET, tratamento de RET codes.
        """
        
        self.execution_id = self.checkpoint_store.create_execution_id()
        self.execution_state = ExecutionState(
            execution_id=self.execution_id,
            started_at=datetime.now(),
        )

        if not self.checkpoint_store.create_lock(self.execution_id):
            raise RuntimeError(f"Execução já em andamento: {self.execution_id}")

        logger.info(f"[EXECUÇÃO] Iniciada: execution_id={self.execution_id}")

        # Filtrar READY_TO_CREATE com risco BAIXO
        ready_products = [
            a for a in self.analyses
            if a.status == "READY_TO_CREATE" and a.risk_level == "BAIXO_RISCO"
        ]

        logger.info(f"[EXECUÇÃO] {len(ready_products)} produtos READY para executar")

        # Listas de resultado
        created_verified: list[dict[str, Any]] = []
        created_not_verified: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        result_unknown: list[dict[str, Any]] = []
        audit_records: list[dict[str, Any]] = []

        bono_template = get_default_bono_template()

        async with httpx.AsyncClient(timeout=120) as client:
            for idx, analysis in enumerate(ready_products):
                self.execution_state.checkpoint_index = idx

                try:
                    # FASE 7: Montar body e POST
                    registration_request = create_registration_request(
                        analysis,
                        template=bono_template,
                    )

                    logger.info(
                        f"[FASE 7] POST {idx+1}/{len(ready_products)}: "
                        f"EAN={analysis.ean}, body_hash={registration_request.body_hash[:8]}..."
                    )

                    post_result = await self.registration_executor.execute_post(
                        body=registration_request.body,
                        body_hash=registration_request.body_hash,
                        ean=analysis.ean,
                        client=client,
                    )

                    http_status = post_result.get("http_status")
                    ret = post_result.get("ret")
                    men = post_result.get("men")
                    cod_produto = post_result.get("cod_produto")

                    if not post_result.get("executed"):
                        logger.error(
                            f"[ERRO] EAN {analysis.ean}: {post_result.get('error')}"
                        )
                        self.execution_state.failed_count += 1
                        result_unknown.append({
                            "ean": analysis.ean,
                            "descricao": analysis.descricao,
                            "http_status": None,
                            "ret": None,
                            "men": post_result.get("error"),
                            "cod_produto": None,
                            "body_hash": registration_request.body_hash,
                            "created_at": datetime.now().isoformat(),
                        })
                        continue

                    # Analisar resposta
                    handler_result = self.registration_executor.handle_ret_code(
                        ret or "0",
                        http_status or 0,
                    )

                    if handler_result["should_pause"]:
                        logger.warning(
                            f"[PAUSA] EAN {analysis.ean}: {handler_result['reason']}"
                        )
                        self.execution_state.paused_reason = handler_result["reason"]
                        self.execution_state.paused_at = datetime.now()
                        self.checkpoint_store.save_checkpoint(self.execution_state)
                        break

                    # FASE 8: Verificar via GET
                    if http_status in (200, 201):
                        verify_result = await self.post_verifier.verify_product_created(
                            ean=analysis.ean,
                            client=client,
                        )

                        if verify_result["found"]:
                            logger.info(
                                f"[VERIFIED] EAN {analysis.ean}: "
                                f"codProduto={cod_produto}"
                            )
                            self.execution_state.success_count += 1
                            created_verified.append({
                                "ean": analysis.ean,
                                "descricao": analysis.descricao,
                                "http_status": http_status,
                                "ret": ret,
                                "men": men,
                                "cod_produto": cod_produto,
                                "body_hash": registration_request.body_hash,
                                "created_at": datetime.now().isoformat(),
                            })
                        else:
                            logger.warning(
                                f"[NOT_VERIFIED] EAN {analysis.ean}: "
                                f"{verify_result['verification_status']}"
                            )
                            created_not_verified.append({
                                "ean": analysis.ean,
                                "descricao": analysis.descricao,
                                "http_status": http_status,
                                "ret": ret,
                                "men": men,
                                "cod_produto": cod_produto,
                                "body_hash": registration_request.body_hash,
                                "created_at": datetime.now().isoformat(),
                            })
                    else:
                        rejected.append({
                            "ean": analysis.ean,
                            "descricao": analysis.descricao,
                            "http_status": http_status,
                            "ret": ret,
                            "men": men,
                            "cod_produto": None,
                            "body_hash": registration_request.body_hash,
                            "created_at": datetime.now().isoformat(),
                        })
                        self.execution_state.failed_count += 1

                    # Registrar auditoria
                    audit_records.append({
                        "ean": analysis.ean,
                        "status": handler_result.get("final_status"),
                        "http": http_status,
                        "ret": ret,
                        "cod_produto": cod_produto,
                        "body_hash": registration_request.body_hash,
                        "created_at": datetime.now().isoformat(),
                    })

                    self.execution_state.products_processed += 1

                except Exception as e:
                    logger.error(f"[EXCEPTION] EAN {analysis.ean}: {e}")
                    self.execution_state.failed_count += 1
                    result_unknown.append({
                        "ean": analysis.ean,
                        "descricao": analysis.descricao,
                        "http_status": None,
                        "ret": None,
                        "men": str(e),
                        "cod_produto": None,
                        "body_hash": "",
                        "created_at": datetime.now().isoformat(),
                    })

        # Salvar checkpoint final
        self.execution_state.paused_at = datetime.now()
        self.checkpoint_store.save_checkpoint(self.execution_state)

        execution_result = {
            "execution_id": self.execution_id,
            "created_verified": created_verified,
            "created_not_verified": created_not_verified,
            "rejected": rejected,
            "result_unknown": result_unknown,
            "audit_records": audit_records,
        }

        logger.info(
            f"[EXECUÇÃO] Concluída: "
            f"sucesso={len(created_verified)}, "
            f"não_verificados={len(created_not_verified)}, "
            f"rejeitados={len(rejected)}, "
            f"erro={len(result_unknown)}"
        )

        return execution_result

    # ========== FASE 10: Relatório Final ==========

    async def export_final_reports(
        self,
        execution_result: dict[str, Any] | None = None,
    ) -> dict[str, Path]:
        """FASE 10 — Gera todos os relatórios finais."""
        
        if execution_result is None:
            execution_result = {
                "created_verified": [],
                "created_not_verified": [],
                "rejected": [],
                "result_unknown": [],
                "audit_records": [],
            }

        execution_id = self.execution_id or self.checkpoint_store.create_execution_id()

        # XLSX Pré-voo
        preflight_path = self.report_exporter.export_preflight_xlsx(
            self.analyses,
            self.metadata.get("file_hash", ""),
            execution_id,
        )

        # XLSX Execução
        execution_path = self.report_exporter.export_execution_xlsx(
            execution_result.get("created_verified", []),
            execution_result.get("created_not_verified", []),
            execution_result.get("rejected", []),
            execution_result.get("result_unknown", []),
            execution_id,
        )

        # Relatório JSON
        summary = {
            "empresa": "118508",
            "empresa_nome": "CONVENIENCIA 24 HORAS",
            "planilha": self.xlsx_path.name,
            "hash_planilha": self.metadata.get("file_hash", ""),
            "total": len(self.analyses),
            "ready_to_create": len([a for a in self.analyses if a.status == "READY_TO_CREATE"]),
            "created_and_verified": len(execution_result.get("created_verified", [])),
            "created_but_not_verified": len(execution_result.get("created_not_verified", [])),
            "rejected": len(execution_result.get("rejected", [])),
            "result_unknown": len(execution_result.get("result_unknown", [])),
            "blocked": len([a for a in self.analyses if a.status == "BLOCKED"]),
            "review_required": len([a for a in self.analyses if a.status == "REVIEW_REQUIRED"]),
            "api_endpoint": "POST /INTEGRACAO/INCLUIR_PRODUTO",
            "execution_id": execution_id,
            "started_at": self.execution_state.started_at.isoformat() if self.execution_state else None,
            "finished_at": datetime.now().isoformat(),
            "rollback": "NOT_PERFORMED",
            "status": "COMPLETED",
        }

        report_path = self.report_exporter.export_relatorio_json(summary, execution_id)

        # Auditoria JSONL
        audit_path = self.report_exporter.export_auditoria_jsonl(
            execution_result.get("audit_records", []),
            execution_id,
        )

        return {
            "preflight": preflight_path,
            "execution": execution_path,
            "report": report_path,
            "audit": audit_path,
        }

    # ========== Helper: Run Full Pipeline ==========

    async def run_full_pipeline(self) -> dict[str, Any]:
        """Executa FASES 3-10 sequencialmente."""
        
        # FASE 3
        await self.load_and_validate_spreadsheet()

        # FASE 5
        await self.analyze_all_products()

        # FASE 6
        self.print_preflight_summary()

        # FASES 7-9
        execution_result = await self.execute_ready_products()

        # FASE 10
        report_paths = await self.export_final_reports(execution_result)

        return {
            "execution_id": self.execution_id,
            "metadata": self.metadata,
            "analyses": self.analyses,
            "execution_result": execution_result,
            "report_paths": report_paths,
        }
