"""
EXECUÇÃO REAL — CADASTRO DOS 35 READY_TO_CREATE

Autorização: Explícita
Empresa: 118508 — CONVENIENCIA 24 HORAS
Endpoint: POST /INTEGRACAO/INCLUIR_PRODUTO (legado, CHAVE_ONLY)

FASE 1: Primeiro produto de baixo risco (biscoito grupo 55446)
FASE 2: Se bem-sucedido, continuar automaticamente com os outros 34

NÃO CADASTRAR:
- BONO (EAN 7891000376928) — já existe (codProduto 2481160)
- 431 REVIEW_REQUIRED
- 18 INVALID_EAN
- Combustíveis
- Duplicados
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.operational.product_registration.company_credentials import (  # noqa: E402
    HttpProductReader,
    require_company_guard,
)
from src.operational.product_registration.engine_schemas import ProductRegistrationRequest  # noqa: E402
from src.operational.product_registration.registration_body import RegistrationBodyBuilder  # noqa: E402
from src.operational.product_registration.registration_engine import ProductRegistrationService  # noqa: E402

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("execute_ready_products_118508.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Carregar .env
load_dotenv()

# Constantes
COMPANY_CODE = 118508
COMPANY_NAME = "CONVENIENCIA 24 HORAS"
CENTER_CODE = 24886
BONO_EAN = "7891000376928"  # Já cadastrado, não repetir
# Produto 2481344: criado com credencial errada, vinculado a 11495. Nunca reenviar
# enquanto o incidente nao for resolvido.
INCIDENT_EAN = "7891962076317"
PERMANENTLY_EXCLUDED_EANS = {
    BONO_EAN: "BONO_ALREADY_REGISTERED",
    INCIDENT_EAN: "INCIDENT_PRODUCT_2481344",
}
BASE_URL = "https://web.qualityautomacao.com.br"
LEGACY_ENDPOINT = "/INTEGRACAO/INCLUIR_PRODUTO"
V1_ENDPOINT = "/INTEGRACAO/V1/PRODUTOS"

# Diretórios
DATA_DIR = project_root / "data" / "product_registration" / "execution"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CHECKPOINT_FILE = DATA_DIR / "checkpoint_118508.json"
EXECUTION_LOG_FILE = DATA_DIR / "execution_log_118508.jsonl"
REPORT_FILE = DATA_DIR / "execution_report_118508.json"

# Estados que impedem novo POST numa retomada. RESULT_UNKNOWN e POST_SENT entram aqui
# porque o produto pode ter sido gravado sem confirmacao: reenviar duplicaria.
TERMINAL_CHECKPOINT_STATES = frozenset(
    {
        "CREATED_AND_VERIFIED",
        "REJECTED",
        "ALREADY_REGISTERED",
        "RESULT_UNKNOWN",
        "POST_SENT",
        "CREATED_IN_WRONG_COMPANY",
        "SKIPPED",
    }
)


class ProductRegistrationExecutor:
    """Executor para cadastro sequencial de produtos."""

    def __init__(self):
        self.client = httpx.Client(timeout=30.0)
        self.reader = HttpProductReader(self.client, BASE_URL)
        self._catalog_by_ean: dict[str, list[dict[str, Any]]] | None = None
        self.credential = self._resolve_credential()
        self.api_key = self.credential.key
        self.execution_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.checkpoint = self._load_checkpoint()
        self.results = {
            "execution_id": self.execution_id,
            "company": COMPANY_CODE,
            "company_name": COMPANY_NAME,
            "endpoint": LEGACY_ENDPOINT,
            "routing": "CHAVE_ONLY",
            "empresaCodigo": "OMITTED",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
            "planned": 0,
            "first_probe": {},
            "posts_sent": 0,
            "created_and_verified": 0,
            "rejected": 0,
            "result_unknown": 0,
            "already_registered": 0,
            "skipped": 0,
            "pending": 0,
            "blocked_models": [],
            "created_products": [],
            "center_sent": CENTER_CODE,
            "center_verified": 0,
            "checkpoint_file": str(CHECKPOINT_FILE),
            "execution_log": str(EXECUTION_LOG_FILE),
            "report_file": str(REPORT_FILE),
            "rollback": "NOT_PERFORMED",
            "status": "IN_PROGRESS",
        }

    def _resolve_credential(self):
        """Resolve a credencial da empresa e exige o guard de empresa antes de qualquer escrita.

        O incidente 2481344 gravou na filial 11495 porque a resolucao caiu em
        WEBPOSTO_API_KEY. O guard confirma por leitura, via produto sentinel, que a
        chave responde pela empresa esperada.
        """
        credential = require_company_guard(COMPANY_CODE, HttpProductReader(self.client))
        logger.info(
            "Credencial confirmada: empresa=%s variavel=%s fingerprint=%s",
            credential.empresa_codigo,
            credential.variable_name,
            credential.fingerprint,
        )
        return credential

    def _load_checkpoint(self) -> dict[str, Any]:
        """Carrega checkpoint se existir."""
        if CHECKPOINT_FILE.exists():
            with open(CHECKPOINT_FILE, encoding="utf-8") as f:
                checkpoint = json.load(f)
            logger.info(f"✓ Checkpoint carregado: {len(checkpoint)} produtos")
            return checkpoint
        return {}

    def _save_checkpoint(self):
        """Salva checkpoint atual."""
        with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
            json.dump(self.checkpoint, f, indent=2, ensure_ascii=False)
        logger.info(f"✓ Checkpoint salvo: {len(self.checkpoint)} produtos")

    def _log_execution(self, product_ean: str, event: dict[str, Any]):
        """Adiciona evento ao log de execução (JSONL)."""
        event["timestamp"] = datetime.now(timezone.utc).isoformat()
        event["execution_id"] = self.execution_id
        event["ean"] = product_ean
        with open(EXECUTION_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _sanitize_url(self, url: str) -> str:
        """Sanitiza URL removendo a chave."""
        if "CHAVE=" in url:
            return url.split("CHAVE=")[0] + "CHAVE=***REDACTED***"
        return url

    def load_ready_products(self, json_file: Path) -> list[dict[str, Any]]:
        """
        Carrega produtos READY_TO_CREATE e remove os EANs permanentemente excluídos
        (BONO já cadastrado e produto 2481344 do incidente).
        """
        with open(json_file, encoding="utf-8") as f:
            all_products = json.load(f)

        ready = []
        for p in all_products:
            if p.get("classificacao_fase6") != "READY_TO_CREATE":
                continue
            reason = PERMANENTLY_EXCLUDED_EANS.get(p["ean"])
            if reason:
                logger.info("Excluido permanentemente EAN %s: %s", p["ean"], reason)
                continue
            ready.append(p)

        logger.info(
            "%s produtos READY_TO_CREATE (excluindo %s)",
            len(ready),
            ", ".join(PERMANENTLY_EXCLUDED_EANS.values()),
        )
        return ready

    def rebuild_body(self, product_data: dict[str, Any]) -> dict[str, Any]:
        """
        Reconstrói body pela fachada permanente, sem herdar BONO.
        Garante inclusão de codigoExterno, utilizaCodigoBarras, Tributação Monofásica.
        """
        excluded = PERMANENTLY_EXCLUDED_EANS.get(product_data.get("ean"))
        if excluded:
            raise ValueError(
                f"EAN {product_data.get('ean')} está permanentemente excluído: {excluded}"
            )
        if product_data.get("tax_basis_status") != "APPROVED":
            raise ValueError(
                f"Base fiscal não aprovada para EAN {product_data.get('ean')}: "
                f"status={product_data.get('tax_basis_status', 'MISSING')}"
            )
        required_tax_fields = ("ncm", "cest", "tributoIcms", "tributoPisCofins")
        missing = [field for field in required_tax_fields if not product_data.get(field)]
        if missing:
            raise ValueError(
                f"Base fiscal incompleta para EAN {product_data.get('ean')}: {', '.join(missing)}"
            )

        # Politica de custo: somente NF-e de entrada do DF-e. Custo digitado, herdado de
        # template ou copiado de produto semelhante nao pode virar cadastro.
        if product_data.get("cost_source") != "DFE":
            raise ValueError(
                f"Custo sem origem DF-e para EAN {product_data.get('ean')}: "
                f"cost_source={product_data.get('cost_source', 'MISSING')}"
            )
        if not product_data.get("dfe_cost_evidence"):
            raise ValueError(
                f"Evidência DF-e ausente para EAN {product_data.get('ean')}"
            )
        cost = product_data.get("preco_custo") or (product_data.get("body_preparado") or {}).get(
            "precoCusto"
        )
        if not cost or float(cost) <= 0:
            raise ValueError(f"Preço de custo inválido para EAN {product_data.get('ean')}")

        request = ProductRegistrationRequest(
            empresa=COMPANY_CODE,
            centro=CENTER_CODE,
            ean=product_data["ean"],
            descricao=product_data["descricao"],
            preco_venda=float(product_data["preco_venda"]),
            ncm=str(product_data["ncm"]),
            cest=product_data.get("cest"),
            grupo_codigo=(
                int(product_data["grupo_codigo_api"])
                if product_data.get("grupo_codigo_api")
                else None
            ),
            custo=float(cost),
            cost_source="DFE",
            cost_evidence=dict(product_data.get("dfe_cost_evidence") or {}),
            perfil_fiscal={
                "tributo_icms": product_data["tributoIcms"],
                "tributo_pis_cofins": product_data["tributoPisCofins"],
                "cfop_entrada": product_data.get("cfop_entrada"),
                "cfop_saida": product_data.get("cfop_saida"),
                "tributacao_monofasica": product_data.get("tributacao_monofasica", 0),
            },
        )
        return RegistrationBodyBuilder().build(request)

    def select_first_candidate(self, products: list[dict[str, Any]]) -> dict[str, Any] | None:
        """
        Seleciona produto de menor risco para primeiro POST:
        - Biscoito (grupo 55446)
        - NCM 19053100
        - CEST 1705300
        - Preço razoável
        """
        candidates = []
        for p in products:
            if (
                p.get("grupo_codigo_api") == 55446
                and p.get("ncm") == "19053100"
                and p.get("cest") == "1705300"
            ):
                candidates.append(p)

        if not candidates:
            # Fallback: qualquer produto do grupo 55446
            candidates = [p for p in products if p.get("grupo_codigo_api") == 55446]

        if not candidates:
            # Fallback final: primeiro produto
            return products[0] if products else None

        # Escolher o de menor preço (menor risco financeiro)
        candidates.sort(key=lambda x: x.get("preco_venda", 999))
        selected = candidates[0]
        logger.info(
            f"✓ Primeiro candidato selecionado: {selected['ean']} - {selected['descricao'][:50]}"
        )
        return selected

    def _scan_catalog_by_ean(self, page_size: int = 200) -> dict[str, list[dict[str, Any]]]:
        """Varre o catalogo inteiro por cursor e indexa por codigo de barras.

        O endpoint legado ignora filtros de codigo de barras e pagina por cursor
        `ultimoCodigo`, entao a unica checagem confiavel de duplicidade e varrer tudo
        e comparar EAN exato. O indice e reaproveitado entre produtos da fila.
        """
        if self._catalog_by_ean is not None:
            return self._catalog_by_ean

        logger.info("Indexando catalogo por codigo de barras (varredura por cursor)...")
        index: dict[str, list[dict[str, Any]]] = {}
        cursor = 0
        pages = 0

        while True:
            items = self.reader.get_catalog(self.api_key, cursor, page_size)
            if not items:
                break

            pages += 1
            max_code = cursor
            for item in items:
                code = item.get("produtoCodigo")
                if isinstance(code, int):
                    max_code = max(max_code, code)
                entry = {
                    "produtoCodigo": code,
                    "nome": item.get("nome"),
                    "referenciaCodigo": item.get("referenciaCodigo"),
                    "ativo": item.get("ativo"),
                    "grupoCodigo": item.get("grupoCodigo"),
                    "combustivel": item.get("combustivel"),
                }
                for barcode in self._barcodes(item):
                    index.setdefault(barcode, []).append(entry)

            if max_code <= cursor:
                break
            cursor = max_code

        logger.info(f"Catalogo indexado: {pages} paginas, {len(index)} codigos de barras")
        self._catalog_by_ean = index
        return index

    @staticmethod
    def _barcodes(item: dict[str, Any]) -> set[str]:
        found: set[str] = set()
        for entry in item.get("produtoCodigoBarra") or []:
            if isinstance(entry, dict) and entry.get("codigoBarra") is not None:
                found.add(str(entry["codigoBarra"]).strip())
        externo = item.get("produtoCodigoExterno")
        if externo:
            found.add(str(externo).strip())
        return found

    def check_duplicate(self, ean: str) -> dict[str, Any]:
        """Verifica se o EAN ja existe no catalogo, por comparacao exata."""
        logger.info(f"Verificando duplicidade: EAN {ean}")

        try:
            index = self._scan_catalog_by_ean()
            hits = index.get(ean, [])
            if hits:
                logger.warning(
                    f"EAN {ean} JA EXISTE (codProduto {[h['produtoCodigo'] for h in hits]})"
                )
                return {"duplicate": True, "hits": hits, "produtoCodigo": hits[0]["produtoCodigo"]}

            logger.info(f"EAN {ean} nao encontrado - CLEAR para cadastro")
            return {"duplicate": False}

        except Exception as e:
            logger.error(f"✗ Erro ao verificar duplicidade: {e}")
            return {"duplicate": None, "error": str(e)}

    def post_product(self, body: dict[str, Any]) -> dict[str, Any]:
        """Executa POST somente pela fachada ProductRegistrationService."""
        ean = str(body.get("codigoBarras") or body.get("codigoExterno") or "")
        logger.info("POST via ProductRegistrationService")
        logger.debug(f"Body: {json.dumps(body, indent=2, ensure_ascii=False)}")

        try:
            service = ProductRegistrationService(CHECKPOINT_FILE)
            outcome, resp, recovered, err = service.post_product(
                self.client,
                self.reader,
                self.api_key,
                body,
                ean=ean,
                from_code=0,
            )
            if recovered is not None and resp is None:
                code = recovered.get("produtoCodigo")
                logger.info("POST recuperado apos timeout: codProduto %s", code)
                return {
                    "http_status": 200,
                    "response": {"codProduto": code, "recoveredAfterTimeout": True},
                    "success": True,
                    "codProduto": code,
                }
            if resp is None:
                return {"success": False, "error": err or outcome}

            result = {
                "http_status": resp.status_code,
                "response": (
                    resp.json()
                    if resp.headers.get("content-type", "").startswith("application/json")
                    else resp.text
                ),
            }

            if resp.status_code in (200, 201):
                cod_produto = result["response"].get("codProduto") if isinstance(result["response"], dict) else None
                if cod_produto:
                    logger.info(f"✓ POST bem-sucedido: codProduto {cod_produto}")
                    result["success"] = True
                    result["codProduto"] = cod_produto
                else:
                    logger.warning(f"⚠ HTTP {resp.status_code} mas sem codProduto")
                    result["success"] = False
            elif resp.status_code == 203:
                payload = result["response"] if isinstance(result["response"], dict) else {}
                ret = payload.get("RET")
                men = payload.get("MEN")
                logger.error(f"✗ HTTP 203 RET={ret} MEN={men}")
                result["success"] = False
                result["ret"] = ret
                result["men"] = men
            else:
                logger.error(f"✗ HTTP {resp.status_code}: {result['response']}")
                result["success"] = False

            return result

        except Exception as e:
            logger.error(f"✗ Exceção no POST: {e}")
            return {"success": False, "error": str(e)}

    def verify_product(self, ean: str, expected_cod: int | None = None) -> dict[str, Any]:
        """Confirma o produto por GET e exige o vinculo com a empresa 118508.

        Posiciona o cursor logo abaixo do codigo criado, evitando varrer o catalogo.
        A confirmacao do vinculo em PRODUTO_EMPRESA e obrigatoria: o POST retorna
        codProduto mesmo quando grava em outra filial (incidente 2481344).
        """
        logger.info(f"Verificando produto cadastrado: EAN {ean}, codProduto {expected_cod}")

        if not expected_cod:
            return {"verified": False, "reason": "codProduto ausente na resposta do POST"}

        cursor = expected_cod - 1

        try:
            catalog_hit = None
            for item in self.reader.get_catalog(self.api_key, cursor, 50):
                if item.get("produtoCodigo") != expected_cod:
                    continue
                if ean not in self._barcodes(item):
                    logger.error(f"codProduto {expected_cod} existe mas o EAN {ean} nao confere")
                    return {"verified": False, "reason": "EAN_MISMATCH"}
                catalog_hit = {
                    "produtoCodigo": item.get("produtoCodigo"),
                    "referenciaCodigo": item.get("referenciaCodigo"),
                    "descricao": item.get("nome"),
                    "grupoCodigo": item.get("grupoCodigo"),
                    "ncm": item.get("ncm"),
                    "cest": item.get("cest"),
                    "unidadeCompra": item.get("unidadeCompra"),
                    "unidadeVenda": item.get("unidadeVenda"),
                    "tipoProduto": item.get("tipoProduto"),
                }
                break

            if catalog_hit is None:
                logger.warning(f"codProduto {expected_cod} nao localizado no catalogo")
                return {"verified": False, "reason": "NOT_FOUND_IN_CATALOG"}

            company_link = None
            for item in self.reader.get_company_links(self.api_key, cursor, 50):
                if item.get("produtoCodigo") == expected_cod:
                    company_link = {
                        "empresaCodigo": item.get("empresaCodigo"),
                        "precoVenda": item.get("precoVenda"),
                        "precoCusto": item.get("precoCusto"),
                        "estoqueQtde": item.get("estoqueQtde"),
                    }
                    break

            if company_link is None:
                logger.error(f"codProduto {expected_cod} sem vinculo de empresa localizado")
                return {"verified": False, "reason": "COMPANY_LINK_NOT_FOUND", **catalog_hit}

            if company_link["empresaCodigo"] != COMPANY_CODE:
                logger.error(
                    f"codProduto {expected_cod} vinculado a empresa "
                    f"{company_link['empresaCodigo']}, esperado {COMPANY_CODE}"
                )
                return {
                    "verified": False,
                    "reason": "WRONG_COMPANY",
                    "empresaCodigo": company_link["empresaCodigo"],
                    **catalog_hit,
                }

            logger.info(
                f"Produto confirmado: codProduto {catalog_hit['produtoCodigo']}, "
                f"referencia {catalog_hit['referenciaCodigo']}, empresa {COMPANY_CODE}"
            )
            return {"verified": True, **catalog_hit, **company_link}

        except Exception as e:
            logger.error(f"Erro ao verificar produto: {e}")
            return {"verified": None, "error": str(e)}

    def execute_single_product(self, product_data: dict[str, Any], is_first: bool = False) -> dict[str, Any]:
        """Executa cadastro de um único produto (com validações)."""
        ean = product_data["ean"]
        descricao = product_data["descricao"]

        logger.info(f"\n{'='*80}")
        logger.info(f"{'PRIMEIRO PROBE' if is_first else 'CADASTRO'}: {ean} - {descricao[:50]}")
        logger.info(f"{'='*80}")

        # Verificar checkpoint. RESULT_UNKNOWN e POST_SENT tambem sao terminais aqui:
        # o POST pode ter gravado, e reenviar duplicaria o produto.
        if ean in self.checkpoint:
            status = self.checkpoint[ean].get("status")
            if status in TERMINAL_CHECKPOINT_STATES:
                logger.info(f"EAN {ean} ja processado anteriormente: {status} - SKIP")
                self.results["skipped"] += 1
                return {"status": "SKIPPED", "reason": f"Ja processado: {status}"}

        # Duplicate check
        dup_check = self.check_duplicate(ean)
        if dup_check.get("duplicate"):
            logger.warning(f"⚠ EAN {ean} já cadastrado — BLOQUEADO")
            self.checkpoint[ean] = {"status": "ALREADY_REGISTERED", "details": dup_check}
            self._save_checkpoint()
            self.results["already_registered"] += 1
            return {"status": "ALREADY_REGISTERED", "details": dup_check}

        # Reconstruir body com campos corrigidos
        body = self.rebuild_body(product_data)
        body_hash = RegistrationBodyBuilder().hash(body)

        # Log de execução
        self._log_execution(
            ean,
            {
                "event": "PRE_POST",
                "descricao": descricao,
                "body_hash": body_hash,
                "is_first": is_first,
            },
        )

        # POST
        self.checkpoint[ean] = {"status": "POSTING", "body_hash": body_hash}
        self._save_checkpoint()

        post_result = self.post_product(body)
        self.results["posts_sent"] += 1

        # Log de execução
        self._log_execution(ean, {"event": "POST_RESULT", "result": post_result})

        # Tratamento do resultado
        if post_result.get("success"):
            cod_produto = post_result.get("codProduto")

            # Verificação pós-cadastro
            verify_result = self.verify_product(ean, cod_produto)

            if verify_result.get("verified"):
                logger.info(f"✓✓✓ PRODUTO CRIADO E VERIFICADO: {ean} → codProduto {cod_produto}")
                self.checkpoint[ean] = {
                    "status": "CREATED_AND_VERIFIED",
                    "codProduto": cod_produto,
                    "referenciaCodigo": verify_result.get("referenciaCodigo"),
                    "body_hash": body_hash,
                    "post_result": post_result,
                    "verify_result": verify_result,
                }
                self.results["created_and_verified"] += 1
                self.results["created_products"].append(
                    {
                        "ean": ean,
                        "descricao": descricao,
                        "codProduto": cod_produto,
                        "referencia": verify_result.get("referenciaCodigo"),
                    }
                )
                self._save_checkpoint()

                if is_first:
                    self.results["first_probe"] = {
                        "ean": ean,
                        "http_status": post_result["http_status"],
                        "codProduto": cod_produto,
                        "verified": True,
                    }

                return {"status": "CREATED_AND_VERIFIED", "codProduto": cod_produto}
            else:
                logger.warning(f"⚠ Produto aparentemente criado mas NÃO VERIFICADO: {ean}")
                self.checkpoint[ean] = {
                    "status": "RESULT_UNKNOWN",
                    "codProduto": cod_produto,
                    "body_hash": body_hash,
                    "post_result": post_result,
                    "verify_result": verify_result,
                }
                self.results["result_unknown"] += 1
                self._save_checkpoint()

                if is_first:
                    self.results["first_probe"] = {
                        "ean": ean,
                        "http_status": post_result["http_status"],
                        "codProduto": cod_produto,
                        "verified": False,
                    }

                return {"status": "RESULT_UNKNOWN"}
        else:
            # POST rejeitado
            logger.error(f"✗✗✗ POST REJEITADO: {ean}")
            self.checkpoint[ean] = {
                "status": "REJECTED",
                "body_hash": body_hash,
                "post_result": post_result,
            }
            self.results["rejected"] += 1
            self._save_checkpoint()

            if is_first:
                self.results["first_probe"] = {
                    "ean": ean,
                    "http_status": post_result.get("http_status"),
                    "ret": post_result.get("ret"),
                    "men": post_result.get("men"),
                    "verified": False,
                }
                # Se o primeiro falhar com RET=3, PAUSAR
                if post_result.get("http_status") == 203 and post_result.get("ret") == 3:
                    logger.error("✗✗✗ PRIMEIRO PROBE REJEITADO COM RET=3 — PAUSANDO EXECUÇÃO")
                    self.results["status"] = "PAUSED_AFTER_CORRECTED_RET3"
                    return {"status": "REJECTED", "pause": True}

            return {"status": "REJECTED"}

    def execute_all(self, products: list[dict[str, Any]]):
        """Executa cadastro sequencial de todos os produtos."""
        self.results["planned"] = len(products)

        if not products:
            logger.warning("⚠ Nenhum produto para cadastrar")
            self.results["status"] = "COMPLETED"
            return

        # ETAPA 1: Primeiro produto
        first = self.select_first_candidate(products)
        if not first:
            logger.error("✗ Não foi possível selecionar primeiro candidato")
            self.results["status"] = "BLOCKED"
            return

        first_result = self.execute_single_product(first, is_first=True)

        if first_result.get("pause"):
            # RET=3 no primeiro — PAUSAR
            logger.error("⏸ EXECUÇÃO PAUSADA: Primeiro produto rejeitado com RET=3")
            self._save_final_report()
            return

        if first_result["status"] != "CREATED_AND_VERIFIED":
            logger.warning(f"⚠ Primeiro produto não foi verificado: {first_result['status']}")
            logger.warning("⏸ PAUSANDO execução para análise")
            self.results["status"] = "PAUSED_AFTER_FIRST_FAILURE"
            self._save_final_report()
            return

        # ETAPA 2: Continuar com os demais
        logger.info("\n" + "="*80)
        logger.info("✓✓✓ PRIMEIRO PRODUTO VERIFICADO — CONTINUANDO AUTOMATICAMENTE")
        logger.info("="*80 + "\n")

        remaining = [p for p in products if p["ean"] != first["ean"]]

        for i, product in enumerate(remaining, start=2):
            logger.info(f"\n[{i}/{len(products)}] Processando: {product['ean']}")

            result = self.execute_single_product(product, is_first=False)

            # Se algum for rejeitado com RET=3, pausar
            if result.get("status") == "REJECTED" and result.get("pause"):
                logger.error("⏸ EXECUÇÃO PAUSADA: RET=3 detectado")
                self.results["status"] = "PAUSED_BY_API_REJECTION"
                break

        # Finalizar
        self.results["pending"] = len([p for p in self.checkpoint.values() if p.get("status") == "PENDING"])

        if self.results["status"] == "IN_PROGRESS":
            if self.results["rejected"] == 0:
                self.results["status"] = "COMPLETED"
            else:
                self.results["status"] = "COMPLETED_WITH_REJECTIONS"

        self._save_final_report()

    def _save_final_report(self):
        """Salva relatório final."""
        self.results["completed_at"] = datetime.now(timezone.utc).isoformat()

        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        logger.info(f"\n{'='*80}")
        logger.info("RELATÓRIO FINAL")
        logger.info(f"{'='*80}")
        logger.info(f"Execution ID: {self.results['execution_id']}")
        logger.info(f"Planejado: {self.results['planned']}")
        logger.info(f"POSTs enviados: {self.results['posts_sent']}")
        logger.info(f"Criados e verificados: {self.results['created_and_verified']}")
        logger.info(f"Rejeitados: {self.results['rejected']}")
        logger.info(f"Resultado desconhecido: {self.results['result_unknown']}")
        logger.info(f"Já existentes: {self.results['already_registered']}")
        logger.info(f"Ignorados: {self.results['skipped']}")
        logger.info(f"Status: {self.results['status']}")
        logger.info(f"Relatório salvo: {REPORT_FILE}")
        logger.info("="*80)


def main():
    """Execução principal."""
    logger.info("="*80)
    logger.info("EXECUÇÃO REAL — CADASTRO DOS 35 READY_TO_CREATE")
    logger.info(f"Empresa: {COMPANY_CODE} — {COMPANY_NAME}")
    logger.info(f"Endpoint: POST {LEGACY_ENDPOINT}")
    logger.info("Roteamento: CHAVE_ONLY (sem empresaCodigo)")
    logger.info("="*80)

    # Localizar fase6_resultado.json
    fase6_file = project_root / "fase6_resultado.json"
    if not fase6_file.exists():
        logger.error(f"✗ Arquivo não encontrado: {fase6_file}")
        sys.exit(1)

    # Criar executor
    executor = ProductRegistrationExecutor()

    # Carregar produtos
    ready_products = executor.load_ready_products(fase6_file)

    if not ready_products:
        logger.error("✗ Nenhum produto READY_TO_CREATE encontrado")
        sys.exit(1)

    logger.info(f"\n✓ {len(ready_products)} produtos carregados")
    logger.info("✓ Primeiro produto será testado isoladamente")
    logger.info(f"✓ Se bem-sucedido, os outros {len(ready_products)-1} serão cadastrados automaticamente\n")

    # Confirmar execução
    input("Pressione ENTER para iniciar a execução...")

    # Executar
    executor.execute_all(ready_products)

    logger.info("\n✓ Execução concluída")
    logger.info(f"✓ Checkpoint: {CHECKPOINT_FILE}")
    logger.info(f"✓ Log de execução: {EXECUTION_LOG_FILE}")
    logger.info(f"✓ Relatório: {REPORT_FILE}")


if __name__ == "__main__":
    main()
