"""Executa uma onda de cadastro por perfis fiscais na empresa 118508.

A aprovacao e por perfil, nao por produto: o primeiro produto de cada perfil e o canario e
so ele exige leitura completa. Verificado o canario, os demais produtos do mesmo perfil
seguem na mesma execucao.

Falha fiscal conhecida antes do POST remove apenas aquele produto. Problema de integridade
— duplicidade, empresa errada, divergencia entre o enviado e o lido, perfil que nao
corresponde ao body — interrompe a onda inteira.

Uso: python scripts/execute_wave_118508.py --wave 1 --limit 20

Nao imprime credencial. Nao envia empresaCodigo. Sem PUT, PATCH, DELETE ou rollback.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.operational.product_registration.company_credentials import (  # noqa: E402
    HttpProductReader,
    company_guard,
    resolve_credential,
)
from src.operational.product_registration.duplicate_checker import (  # noqa: E402
    find_description_duplicates,
    looks_fabricated_gtin,
)
from src.operational.product_registration.ean_service import (  # noqa: E402
    gtin_prefix_length_conflict,
)
from src.operational.product_registration.final_wave import (  # noqa: E402
    LEGITIMATE_VARIANT,
    SAME_PRODUCT,
    UNRESOLVED_DUPLICATE,
    classify_final_duplicate,
)
from src.operational.product_registration.fiscal_profiles import (  # noqa: E402
    payload_id,
    payload_key,
    special_category,
)
from src.operational.product_registration.product_family import (  # noqa: E402
    commercial_family,
)
from src.operational.product_registration.registration_engine import (  # noqa: E402
    ProductRegistrationService,
)
from src.operational.product_registration.stores import interpret_lock  # noqa: E402

BASE_URL = "https://web.qualityautomacao.com.br"
LEGACY_ENDPOINT = "/INTEGRACAO/INCLUIR_PRODUTO"
COMPANY_CODE = 118508
PROFILE = "WEBPOSTO_CONVENIENCIA_24_HORAS_KEY"
COST_CENTER = 24886
MAX_WAVE = 20
EXHAUST_MAX = 36
EXHAUST_MAX_BY_WAVE = {2: 36, 3: 80, 4: 80, 5: 80}
PAUSE_SECONDS = 1.5
SENTINEL_EVERY = 10

REGISTRATION_DIR = ROOT / "data" / "product_registration"
PROFILES = REGISTRATION_DIR / "fiscal_profiles_118508.json"
CHECKPOINT = REGISTRATION_DIR / "execution" / "checkpoint_118508.json"
ACCOUNTANT_REVIEW = REGISTRATION_DIR / "accountant_review_118508.json"
PENDING_COST_UPDATE = REGISTRATION_DIR / "pending_cost_update_118508.json"
PENDING_PRICE_REVIEW = REGISTRATION_DIR / "pending_price_review_118508.json"

PENDING_COST_FLAG = "ALLOW_PENDING_DFE_COST"
PENDING_COST_STATUS = "PENDING"

BLOCKED_EANS = {"7891000376928", "7891962076317", "789607405141"}
BLOCKED_CODES = {2481160, 2481344}
WAVE_LEVELS = {
    1: {"PROFILE_A", "PROFILE_B", "PROFILE_C"},
    2: {"PROFILE_D"},
    3: {"PROFILE_D"},
    4: {"PROFILE_SPECIAL", "PROFILE_D"},
    5: {"PROFILE_D", "PROFILE_SPECIAL"},
}

WAVE4_CATEGORY_RANK = {
    "TABACARIA_ACESSORIO": 1,
    "BEBIDA_ALCOOLICA": 2,
    "OUTRO_ESPECIAL": 3,
    "TABACO": 4,
}

# Familias que seguem com as categorias especiais, mesmo quando o NCM nao denuncia o
# regime: isqueiro entra como acendedor, mas a loja o vende no balcao da tabacaria.
SENSITIVE_FAMILIES = frozenset(
    {"TABACARIA", "FARMACIA", "CERVEJA", "VINHO_ESPUMANTE", "DESTILADO"}
)


class WaveHalted(Exception):
    """Interrompe a onda sem enviar mais nenhum POST."""


def load_json(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def barcodes(product: dict[str, Any]) -> set[str]:
    values = {
        str((e.get("codigoBarra") if isinstance(e, dict) else e) or "").strip()
        for e in product.get("produtoCodigoBarra") or []
    }
    external = product.get("produtoCodigoExterno")
    if external:
        values.add(str(external).strip())
    return {v for v in values if v}


def pending_cost_allowed() -> bool:
    """Autorizacao de custo zero, valida apenas para o processo atual."""
    return os.environ.get(PENDING_COST_FLAG, "").strip().lower() == "true"


def validate_cost(cost: Any, cost_info: dict[str, Any]) -> tuple[bool, str]:
    if cost is None:
        return False, "CUSTO_AUSENTE"
    cost = float(cost)
    if cost < 0:
        return False, "CUSTO_NEGATIVO"
    if cost > 0:
        if cost_info.get("source") != "DFE":
            return False, "CUSTO_POSITIVO_SEM_ORIGEM_DFE"
        return True, "CUSTO_DFE"
    if cost_info.get("cost_status") != PENDING_COST_STATUS:
        return False, "CUSTO_ZERO_SEM_STATUS_PENDENTE"
    if not pending_cost_allowed():
        return False, "CUSTO_ZERO_SEM_AUTORIZACAO_EXPLICITA"
    return True, "CUSTO_ZERO_AUTORIZADO"


def body_matches_profile(body: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    """Campos do body que nao correspondem ao perfil aprovado."""
    divergences = []
    if body.get("codigoNcm") not in profile["ncms"]:
        divergences.append("ncm")
    if profile["cests"] and body.get("codigoCest") not in profile["cests"]:
        divergences.append("cest")
    divergences.extend(body_matches_payload(body, profile))
    return divergences


def body_matches_payload(body: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    """Campos tributarios do body que nao correspondem ao payload aprovado.

    O payload nao fixa NCM nem CEST, porque produtos de NCM diferente podem gerar o mesmo
    payload tributario. Exige, porem, que a presenca de CEST seja a mesma: payload com CEST
    aprovado nao autoriza enviar produto sem CEST.
    """
    divergences = []
    if body.get("tributoIcms") != profile["tributo_icms"]:
        divergences.append("tributoIcms")
    if body.get("tributoPisCofins") != profile["tributo_pis_cofins"]:
        divergences.append("tributoPisCofins")
    if body.get("cdCfopSaida") != profile["cfop_saida"]:
        divergences.append("cfopSaida")
    if body.get("cdCfopEntrada") != profile["cfop_entrada"]:
        divergences.append("cfopEntrada")
    if body.get("Tributação Monofásica") != profile["tributacao_monofasica"]:
        divergences.append("tributacaoMonofasica")
    if bool(body.get("codigoCest")) != bool(profile["cests"]):
        divergences.append("presencaDeCest")
    return divergences


def group_by_payload(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Funde perfis fiscais que produzem o mesmo payload em um perfil operacional.

    O canario passa a provar o payload, nao o NCM: assim uma unica prova serve para todos
    os produtos que a API vai receber com a mesma tributacao. O perfil fiscal de origem
    continua registrado em cada produto, para a trilha individual.
    """
    grouped: dict[tuple, dict[str, Any]] = {}
    for profile in profiles:
        key = payload_key(profile)
        operational = grouped.get(key)
        if operational is None:
            operational = {
                **profile,
                "profile_id": payload_id(profile),
                "ncms": [],
                "cests": [],
                "produtos": [],
                "profile_canary_status": "PENDING",
                "produto_canario": None,
                "canario_origem": None,
                "perfis_fiscais": [],
            }
            grouped[key] = operational
        operational["ncms"] = sorted(set(operational["ncms"]) | set(profile["ncms"]))
        operational["cests"] = sorted(set(operational["cests"]) | set(profile["cests"]))
        operational["perfis_fiscais"].append(profile["profile_id"])
        for product in profile["produtos"]:
            operational["produtos"].append({**product, "perfilFiscal": profile["profile_id"]})
        if profile.get("profile_canary_status") == "VERIFIED":
            operational["profile_canary_status"] = "VERIFIED"
            operational["produto_canario"] = profile.get("produto_canario")
            operational["canario_origem"] = profile.get("canario_origem")
    for operational in grouped.values():
        operational["quantidade_candidatos"] = len(operational["produtos"])
    return list(grouped.values())


def product_gate(product: dict[str, Any], *, allow_special: bool = False) -> str | None:
    """Motivo para o produto nao entrar na fila, ou None.

    Roda antes de ocupar vaga no lote: assim uma exclusao nao consome uma das vagas
    autorizadas nem interrompe os demais produtos. Na onda 4 as categorias especiais
    sao a fila, nao o bloqueio.
    """
    ean = product["ean"]
    if ean in BLOCKED_EANS:
        return "GTIN_BLOQUEADO_PERMANENTE"
    fabricated = looks_fabricated_gtin(ean)
    if fabricated:
        return f"GTIN_COM_APARENCIA_DE_INVENTADO:{fabricated}"
    prefix_conflict = gtin_prefix_length_conflict(ean)
    if prefix_conflict:
        return f"GTIN_INCOERENTE_COM_O_PREFIXO:{prefix_conflict}"
    if not allow_special:
        special = special_category(product.get("ncm"), product.get("descricao"))
        if special:
            return f"CATEGORIA_ESPECIAL_DA_ONDA_4:{special}"
        family = product.get("familiaComercial")
        if family in SENSITIVE_FAMILIES:
            return f"CATEGORIA_ESPECIAL_DA_ONDA_4:{family}"
    if not product.get("precoVenda") or product["precoVenda"] <= 0:
        return "PRECO_VENDA_INVALIDO"
    return None


def wave4_category(product: dict[str, Any]) -> str:
    """Ordem fiscal da onda 4: acessorio, alcool, demais especiais, tabaco por ultimo."""
    spec = special_category(product.get("ncm"), product.get("descricao"))
    ncm = str(product.get("ncm") or "")
    if spec == "TABACO" or ncm.startswith("24"):
        return "TABACO"
    if spec == "TABACARIA_CORRELATO" or product.get("familiaComercial") == "TABACARIA":
        return "TABACARIA_ACESSORIO"
    if spec == "BEBIDA_ALCOOLICA":
        return "BEBIDA_ALCOOLICA"
    return "OUTRO_ESPECIAL"


def build_wave4_queue(
    profiles: list[dict[str, Any]],
    limit: int,
    *,
    gate: Any = None,
    rejected: list[dict[str, Any]] | None = None,
    checkpoint: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Fila da onda 4: categoria fiscal, depois payload, canario primeiro."""
    checkpoint = checkpoint or {}
    staged: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for profile in profiles:
        if profile.get("onda") != 4:
            continue
        for product in profile["produtos"]:
            if product["ean"] in checkpoint:
                continue
            reason = gate(product) if gate else None
            if reason:
                if rejected is not None:
                    rejected.append(
                        {
                            "ean": product["ean"],
                            "descricao": product["descricao"],
                            "ncm": product.get("ncm"),
                            "cest": product.get("cest"),
                            "familiaComercial": product.get("familiaComercial"),
                            "perfilFiscal": profile["profile_id"],
                            "motivo": reason,
                        }
                    )
                continue
            staged.append((wave4_category(product), profile, product))
    staged.sort(
        key=lambda item: (
            WAVE4_CATEGORY_RANK[item[0]],
            payload_id(item[1]),
            item[2]["precoVenda"],
            item[2]["ean"],
        )
    )
    queue: list[dict[str, Any]] = []
    opened: set[tuple[str, str]] = set()
    for category, profile, product in staged:
        if len(queue) >= limit:
            break
        operational_id = payload_id(profile)
        key = (category, operational_id)
        canary = key not in opened
        opened.add(key)
        queue.append(
            {
                "profile": {
                    **profile,
                    "profile_id": operational_id,
                    "wave4_category": category,
                },
                "product": {
                    **product,
                    "perfilFiscal": profile["profile_id"],
                    "categoriaEspecial": category,
                    "categoriaEspecialSistema": special_category(
                        product.get("ncm"), product.get("descricao")
                    ),
                },
                "is_canary": canary,
                "by_payload": True,
                "wave4_category": category,
            }
        )
    return queue


def build_queue(
    profiles: list[dict[str, Any]],
    levels: set[str],
    limit: int,
    *,
    by_payload: bool = False,
    gate: Any = None,
    rejected: list[dict[str, Any]] | None = None,
    checkpoint: dict[str, Any] | None = None,
    onda: int | None = None,
) -> list[dict[str, Any]]:
    """Fila da onda: canario de cada perfil primeiro, depois os demais do mesmo perfil.

    Perfis com mais produtos vem antes, para que uma unica aprovacao renda o maximo de
    cadastros no lote. Com by_payload, o agrupamento e feito pelo payload tributario.

    Produtos ja presentes no checkpoint sao pulados silenciosamente: eles ja foram
    processados em lotes anteriores e nao devem consumir vagas nem ser contados como
    rejeicao do gate.
    """
    checkpoint = checkpoint or {}
    eligible = [p for p in profiles if p["level"] in levels]
    if onda is not None:
        eligible = [p for p in eligible if p.get("onda") == onda]
    if by_payload:
        eligible = group_by_payload(eligible)
    eligible.sort(key=lambda p: (-p["quantidade_candidatos"], p["profile_id"]))
    queue: list[dict[str, Any]] = []
    for profile in eligible:
        products = sorted(
            profile["produtos"],
            key=lambda prod: (
                prod["ean"] != profile.get("produto_canario"),
                not prod.get("familiaComercial"),
                prod["precoVenda"],
            ),
        )
        for product in products:
            if len(queue) >= limit:
                return queue
            ean = product["ean"]
            if ean in checkpoint:
                continue
            reason = gate(product) if gate else None
            if reason:
                if rejected is not None:
                    rejected.append(
                        {
                            "ean": product["ean"],
                            "descricao": product["descricao"],
                            "ncm": product.get("ncm"),
                            "cest": product.get("cest"),
                            "familiaComercial": product.get("familiaComercial"),
                            "perfilFiscal": product.get("perfilFiscal")
                            or profile["profile_id"],
                            "motivo": reason,
                        }
                    )
                continue
            queue.append(
                {
                    "profile": profile,
                    "product": product,
                    # O canario e o primeiro produto que de fato sera enviado deste perfil.
                    "is_canary": not any(
                        item["profile"]["profile_id"] == profile["profile_id"] for item in queue
                    )
                    and profile.get("profile_canary_status") != "VERIFIED",
                    "by_payload": by_payload,
                }
            )
    return queue


def retry_after_seconds(response: httpx.Response, default: float = 5.0) -> float:
    """Espera pedida pelo servidor em 429, limitada para nao travar o lote."""
    header = response.headers.get("Retry-After", "").strip()
    try:
        return min(max(float(header), 1.0), 60.0)
    except ValueError:
        return default


def find_recent_by_ean(
    reader: HttpProductReader, key: str, ean: str, from_code: int
) -> dict[str, Any] | None:
    """Procura um EAN entre os produtos criados a partir de from_code.

    Serve para decidir, depois de um timeout, se o POST chegou a criar o produto. Produto
    novo recebe codigo crescente, entao basta varrer dai para frente.
    """
    cursor = max(from_code - 1, 0)
    seen: set[int] = set()
    for _ in range(50):
        rows = reader.get_catalog(key, cursor=cursor, page_size=200)
        if not rows:
            return None
        for row in rows:
            if ean in barcodes(row):
                return row
        nxt = max(int(row.get("produtoCodigo") or 0) for row in rows)
        if nxt == cursor or nxt in seen:
            return None
        seen.add(nxt)
        cursor = nxt
    return None


def send_product(
    client: httpx.Client,
    reader: HttpProductReader,
    key: str,
    body: dict[str, Any],
    *,
    ean: str,
    from_code: int,
    service: ProductRegistrationService | None = None,
) -> tuple[str, httpx.Response | None, dict[str, Any] | None, str | None]:
    """Envia o POST somente pela fachada. Timeout resolve por GET."""
    facade = service or ProductRegistrationService(CHECKPOINT)
    return facade.post_product(
        client,
        reader,
        key,
        body,
        ean=ean,
        from_code=from_code,
        pause_seconds=PAUSE_SECONDS,
    )


def confirm_sentinel(credential: Any, reader: HttpProductReader, when: str) -> None:
    """Confere o BONO no inicio, a cada 10 confirmados e no encerramento."""
    guard = company_guard(credential, reader)
    if not guard.passed:
        raise WaveHalted(f"Sentinel BONO nao confirmado ({when})")
    print(f"sentinel BONO ({when}): encontrado={guard.sentinel_found} "
          f"vinculo={guard.company_link_confirmed}")


def persist_lock(
    path: Path,
    *,
    status: str,
    wave: int,
    batch: str,
    by_payload: bool,
    post_count: int,
    created: int,
    skipped: int,
    halted_reason: str | None,
    verified_profiles: set[str],
) -> None:
    if not status:
        raise ValueError("novo lock exige status explicito")
    save_json(
        path,
        {
            "status": status,
            "executedAt": datetime.now(timezone.utc).isoformat(),
            "wave": wave,
            "batch": batch,
            "groupedByPayload": by_payload,
            "postCount": post_count,
            "createdAndVerified": created,
            "skippedPrePost": skipped,
            "haltedReason": halted_reason,
            "verifiedProfiles": sorted(verified_profiles),
            "reexecution": "LOCKED" if status in {"COMPLETED", "PARTIAL"} else "OPEN",
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa uma onda de perfis fiscais da 118508")
    parser.add_argument("--wave", type=int, default=1, choices=sorted(WAVE_LEVELS))
    parser.add_argument("--limit", type=int, default=MAX_WAVE)
    parser.add_argument("--batch", default="01")
    parser.add_argument(
        "--by-payload",
        action="store_true",
        help="agrupa perfis de mesmo payload tributario sob um unico canario",
    )
    parser.add_argument(
        "--exhaust",
        action="store_true",
        help="permite ate EXHAUST_MAX produtos numa unica execucao da onda",
    )
    args = parser.parse_args()

    max_allowed = EXHAUST_MAX_BY_WAVE.get(args.wave, EXHAUST_MAX) if args.exhaust else MAX_WAVE
    if args.wave in {4, 5} and args.exhaust and args.limit == MAX_WAVE:
        args.limit = max_allowed
    if args.limit > max_allowed:
        raise WaveHalted(f"Limite {args.limit} excede o maximo de {max_allowed} por execucao")

    out_dir = REGISTRATION_DIR / f"wave_{args.wave:02d}_batch_{args.batch}_118508"
    if args.wave == 1 and args.batch == "01":
        # A onda 1 executou antes de existir a numeracao de lote; preserva a trava dela.
        out_dir = REGISTRATION_DIR / "wave_01_118508"
    result_path = out_dir / "execution_result.json"
    wave_lock = out_dir / "wave_lock.json"
    existing_lock = interpret_lock(load_json(wave_lock, {}) if wave_lock.is_file() else {})
    if existing_lock and existing_lock.get("status") != "RUNNING":
        raise WaveHalted(
            f"Onda {args.wave} lote {args.batch} já executado em {existing_lock.get('executedAt')} "
            f"({existing_lock.get('postCount')} POSTs). Nova execução recusada."
        )

    payload = load_json(PROFILES, {})
    if not payload.get("profiles"):
        raise WaveHalted("fiscal_profiles_118508.json ausente ou vazio")

    credential = resolve_credential(COMPANY_CODE)
    if credential.variable_name != PROFILE:
        raise WaveHalted(f"Credencial fora do profile exigido: {credential.variable_name}")

    checkpoint = load_json(CHECKPOINT, {})
    review = load_json(ACCOUNTANT_REVIEW, {})
    pending_cost = load_json(PENDING_COST_UPDATE, {})
    pending_price = load_json(PENDING_PRICE_REVIEW, {})

    gated_out: list[dict[str, Any]] = []
    if args.wave == 4:
        queue = build_wave4_queue(
            payload["profiles"],
            args.limit,
            gate=lambda product: product_gate(product, allow_special=True),
            rejected=gated_out,
            checkpoint=checkpoint,
        )
    else:
        queue = build_queue(
            payload["profiles"],
            WAVE_LEVELS[args.wave],
            args.limit,
            by_payload=args.by_payload or args.wave == 5,
            gate=(
                (lambda product: product_gate(product, allow_special=True))
                if args.wave == 5
                else None if args.exhaust else product_gate
            ),
            rejected=gated_out,
            checkpoint=checkpoint,
            onda=args.wave,
        )
    if not queue and args.wave != 5:
        raise WaveHalted(f"Nenhum produto elegivel na onda {args.wave}")

    profile_ids = {item["profile"]["profile_id"] for item in queue}
    print(f"ONDA {args.wave} LOTE {args.batch} | fila={len(queue)} | "
          f"perfis={len(profile_ids)} | gated={len(gated_out)} | "
          f"custo_pendente={pending_cost_allowed()}")

    executed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    verified_profiles: set[str] = set()
    halted_reason: str | None = None
    post_count = 0
    sent_hashes = {
        str(row.get("body_hash"))
        for row in checkpoint.values()
        if isinstance(row, dict) and row.get("body_hash")
    }

    persist_lock(
        wave_lock,
        status="RUNNING",
        wave=args.wave,
        batch=args.batch,
        by_payload=args.by_payload,
        post_count=0,
        created=0,
        skipped=0,
        halted_reason=None,
        verified_profiles=verified_profiles,
    )

    try:
        with httpx.Client(timeout=120.0) as client:
            reader = HttpProductReader(client)
            service = ProductRegistrationService(CHECKPOINT, wave_lock)
            confirm_sentinel(credential, reader, "inicio")

            catalog_rows: list[dict[str, Any]] = []
            cursor = 0
            seen: set[int] = set()
            page = reader.get_catalog(credential.key, cursor=0, page_size=200)
            while page:
                catalog_rows.extend(page)
                nxt = max(int(p.get("produtoCodigo") or 0) for p in page)
                if nxt == cursor or nxt in seen:
                    break
                seen.add(nxt)
                cursor = nxt
                page = reader.get_catalog(credential.key, cursor=cursor, page_size=200)
            all_codes: dict[str, int] = {}
            for entry in catalog_rows:
                for bar in barcodes(entry):
                    all_codes.setdefault(bar, int(entry.get("produtoCodigo") or 0))
            # Referencia para localizar um produto criado durante um timeout: codigo novo é
            # sempre maior que os existentes.
            highest_code = max(int(row.get("produtoCodigo") or 0) for row in catalog_rows)
            print(f"catalogo indexado: {len(catalog_rows)} produtos | {len(all_codes)} codigos"
                  f" | maior codigo {highest_code}")
            print()

            current_category: str | None = None
            blocked_payloads: set[str] = set()
            for item in queue:
                profile = item["profile"]
                product = item["product"]
                ean = product["ean"]
                body = product["body"]["preview"]
                expected_hash = product["body"]["hash"]
                canary = item["is_canary"] and profile["profile_id"] not in verified_profiles
                category = item.get("wave4_category") or (
                    wave4_category(product) if args.wave == 5 else None
                )
                if category and category != current_category:
                    if current_category is not None:
                        confirm_sentinel(credential, reader, f"troca_{current_category}_para_{category}")
                    current_category = category
                    print(f"CATEGORIA {category}")

                def skip(reason: str, detail: str | None = None) -> None:
                    skipped.append(
                        {
                            "ean": ean,
                            "descricao": product["descricao"],
                            "profileId": profile["profile_id"],
                            "motivo": "SKIPPED_PRE_POST",
                            "detalhe": f"{reason}{f':{detail}' if detail else ''}",
                        }
                    )
                    print(f"SKIP {ean} {reason}{f':{detail}' if detail else ''}")

                # --- Falhas individuais: removem o produto e a onda continua ---------------
                if profile["profile_id"] in blocked_payloads:
                    skip("PERFIL_BLOQUEADO_SEM_CEST")
                    continue
                gate_reason = product_gate(product, allow_special=args.wave in {4, 5})
                if gate_reason:
                    skip("GATE", gate_reason)
                    continue
                if ean in BLOCKED_EANS or ean in checkpoint:
                    skip("JA_PROCESSADO_OU_BLOQUEADO")
                    continue
                if expected_hash in sent_hashes:
                    skip("BODY_HASH_JA_ENVIADO")
                    continue
                fabricated = looks_fabricated_gtin(ean)
                if fabricated:
                    skip("GTIN_COM_APARENCIA_DE_INVENTADO", fabricated)
                    continue
                if not body.get("precoVenda") or body["precoVenda"] <= 0:
                    skip("PRECO_VENDA_INVALIDO")
                    continue
                cost_ok, cost_reason = validate_cost(body.get("precoCusto"), product.get("custo") or {})
                if not cost_ok:
                    skip(cost_reason)
                    continue

                if ean in all_codes:
                    skip("DUPLICADO_NO_CATALOGO", str(all_codes[ean]))
                    continue
                description_matches = find_description_duplicates(product["descricao"], catalog_rows)
                if description_matches:
                    existing = description_matches[0]
                    if args.wave == 5:
                        label, reason = classify_final_duplicate(
                            product["descricao"],
                            existing.get("nome") or "",
                            candidate_family=product.get("familiaComercial"),
                            existing_family=commercial_family(existing.get("nome") or ""),
                        )
                        if label == LEGITIMATE_VARIANT:
                            pass
                        elif label == SAME_PRODUCT:
                            skip(
                                "ALREADY_REGISTERED_BY_DESCRIPTION",
                                str(existing.get("produtoCodigo")),
                            )
                            checkpoint[ean] = {
                                "status": "ALREADY_REGISTERED_BY_DESCRIPTION",
                                "ean": ean,
                                "descricao": product["descricao"],
                                "produto_existente": existing.get("produtoCodigo"),
                                "produto_existente_descricao": existing.get("nome"),
                                "bloqueio": "Nao cadastrar. Nao alterar o produto existente.",
                                "classificadoEm": datetime.now(timezone.utc).isoformat(),
                            }
                            save_json(CHECKPOINT, checkpoint)
                            continue
                        else:
                            skip("UNRESOLVED_DUPLICATE" if label == UNRESOLVED_DUPLICATE else label, reason)
                            continue
                    else:
                        skip(
                            "DUPLICIDADE_POR_DESCRICAO",
                            f"{ean}->{existing.get('produtoCodigo')}",
                        )
                        continue
                if "empresaCodigo" in body:
                    halted_reason = f"BODY_COM_EMPRESA_CODIGO:{ean}"
                    break
                if body["codigoBarras"] != ean or body["codigoExterno"] != ean:
                    halted_reason = f"BODY_DIVERGENTE_DO_EAN:{ean}"
                    break
                profile_divergences = (
                    body_matches_payload(body, profile)
                    if item["by_payload"]
                    else body_matches_profile(body, profile)
                )
                if profile_divergences:
                    halted_reason = f"BODY_FORA_DO_PERFIL:{ean}:{','.join(profile_divergences)}"
                    break
                if not body.get("codigoNcm"):
                    skip("NCM_AUSENTE")
                    continue

                outcome, response, recovered, transport_error = send_product(
                    client,
                    reader,
                    credential.key,
                    body,
                    ean=ean,
                    from_code=highest_code,
                    service=service,
                )
                post_count += 1
                if outcome == "TIMEOUT_UNCONFIRMED":
                    executed.append(
                        {
                            "ean": ean,
                            "descricao": product["descricao"],
                            "profileId": profile["profile_id"],
                            "classification": "RESULT_UNKNOWN",
                            "transportError": transport_error,
                        }
                    )
                    halted_reason = f"RESULT_UNKNOWN:{ean}"
                    print(f"STOP RESULT_UNKNOWN {ean}")
                    break
                if outcome == "TIMEOUT_BUT_CREATED":
                    # Timeout, mas o EAN existe: segue para a mesma verificacao do POST ok.
                    http_status = 200
                    response_payload = {
                        "codProduto": recovered.get("produtoCodigo"),
                        "recoveredAfterTimeout": True,
                        "transportError": transport_error,
                    }
                    ret = None
                    men = None
                    cod_produto = recovered.get("produtoCodigo")
                else:
                    http_status = response.status_code
                    try:
                        response_payload = response.json()
                    except Exception:
                        response_payload = {"raw": (response.text or "")[:400]}
                    ret = response_payload.get("RET") if isinstance(response_payload, dict) else None
                    men = response_payload.get("MEN") if isinstance(response_payload, dict) else None
                    cod_produto = (
                        response_payload.get("codProduto")
                        if isinstance(response_payload, dict)
                        else None
                    )

                record: dict[str, Any] = {
                    "ean": ean,
                    "descricao": product["descricao"],
                    "profileId": profile["profile_id"],
                    "profileLevel": profile["level"],
                    "canary": canary,
                    "httpStatus": http_status,
                    "ret": ret,
                    "men": men,
                    "codProduto": cod_produto,
                    "bodyHash": expected_hash,
                    "response": response_payload,
                }

                if http_status in {401, 403}:
                    record["classification"] = "HTTP_AUTH"
                    executed.append(record)
                    halted_reason = f"HTTP_AUTH:{http_status}"
                    print(f"STOP HTTP_AUTH {http_status} {ean}")
                    break
                if http_status != 200:
                    record["classification"] = "HTTP_INESPERADO"
                    executed.append(record)
                    halted_reason = f"HTTP_INESPERADO:{http_status}"
                    print(f"STOP HTTP {http_status} {ean}")
                    break
                if ret not in (None, 0, "0"):
                    if args.wave in {3, 5} and not body.get("codigoCest"):
                        record["classification"] = "CEST_REJEITADO_PELA_API"
                        executed.append(record)
                        blocked_payloads.add(profile["profile_id"])
                        print(f"SKIP {ean} CEST_REJEITADO_PELA_API:{ret}")
                        continue
                    record["classification"] = "RET_NAO_SUCESSO"
                    executed.append(record)
                    halted_reason = f"RET_NAO_SUCESSO:{ret}"
                    break
                if not cod_produto:
                    record["classification"] = "SEM_CODPRODUTO"
                    executed.append(record)
                    halted_reason = "SEM_CODPRODUTO"
                    break

                code = int(cod_produto)
                if code in BLOCKED_CODES:
                    record["classification"] = "CODIGO_BLOQUEADO_RETORNADO"
                    executed.append(record)
                    halted_reason = f"CODIGO_BLOQUEADO_RETORNADO:{code}"
                    break

                links = reader.get_company_links(credential.key, cursor=code - 1, page_size=50)
                matching = [row for row in links if int(row.get("produtoCodigo") or 0) == code]
                company_link = next(
                    (row for row in matching if int(row.get("empresaCodigo") or 0) == COMPANY_CODE),
                    None,
                )
                rows = reader.get_catalog(credential.key, cursor=code - 1, page_size=50)
                created = next((p for p in rows if int(p.get("produtoCodigo") or 0) == code), None)

                record["verification"] = {
                    "produtoCodigo": code,
                    "links": [
                        {
                            "empresaCodigo": row.get("empresaCodigo"),
                            "precoVenda": row.get("precoVenda"),
                            "precoCusto": row.get("precoCusto"),
                            "ativo": row.get("ativo"),
                        }
                        for row in matching
                    ],
                    "companyLinkConfirmed": bool(company_link),
                    "catalog": (
                        {
                            "nome": created.get("nome"),
                            "referenciaCodigo": created.get("referenciaCodigo"),
                            "ncm": created.get("ncm"),
                            "cest": created.get("cest"),
                            "grupoCodigo": created.get("grupoCodigo"),
                            "produtoCodigoExterno": created.get("produtoCodigoExterno"),
                        }
                        if created
                        else None
                    ),
                    "centerSent": COST_CENTER,
                }

                if not company_link:
                    record["classification"] = (
                        "CREATED_IN_WRONG_COMPANY" if matching else "ORPHANED_SHARED_CATALOG_RECORD"
                    )
                    executed.append(record)
                    halted_reason = record["classification"]
                    print(f"    ALERTA: {record['classification']}")
                    break

                divergences = []
                if abs(float(company_link.get("precoVenda") or 0) - float(body["precoVenda"])) > 0.005:
                    divergences.append("precoVenda")
                if abs(float(company_link.get("precoCusto") or 0) - float(body["precoCusto"])) > 0.005:
                    divergences.append("precoCusto")
                if not company_link.get("ativo"):
                    divergences.append("ativo")
                if created and str(created.get("ncm") or "") != str(body["codigoNcm"]):
                    divergences.append("ncm")
                if created and str(created.get("cest") or "") != str(body.get("codigoCest") or ""):
                    divergences.append("cest")
                if created and ean not in barcodes(created):
                    divergences.append("codigoBarras")
                record["verification"]["divergences"] = divergences

                if divergences:
                    record["classification"] = "DIVERGENCIA_BODY_VS_LIDO"
                    executed.append(record)
                    halted_reason = f"DIVERGENCIA:{','.join(divergences)}"
                    print(f"    ALERTA: divergência em {divergences}")
                    break

                record["classification"] = "CREATED_AND_VERIFIED"
                executed.append(record)
                reference = record["verification"]["catalog"]["referenciaCodigo"]
                created_count = len(
                    [row for row in executed if row.get("classification") == "CREATED_AND_VERIFIED"]
                )
                print(f"OK {created_count}/{len(queue)} {ean} {code}")
                if canary:
                    verified_profiles.add(profile["profile_id"])
                if created:
                    catalog_rows.append(created)
                    for bar in barcodes(created):
                        all_codes.setdefault(bar, code)
                    highest_code = max(highest_code, code)
                sent_hashes.add(expected_hash)

                cost_info = product.get("custo") or {}
                nfe = cost_info.get("nfe") or {}
                evidence = profile["evidencias"]
                trail = {
                    "tax_basis_source": evidence.get("tax_basis_source"),
                    "entry_tax_evidence": evidence.get("entry_tax_evidence"),
                    "decision_authority": evidence.get("decision_authority"),
                }
                checkpoint[ean] = {
                    **trail,
                    "payload_id": profile["profile_id"] if item["by_payload"] else None,
                    "perfil_fiscal": product.get("perfilFiscal") or profile["profile_id"],
                    # Payload compartilhado nao apaga a identidade fiscal do produto.
                    "familia_comercial": product.get("familiaComercial"),
                    "cest_status": "NOT_PROVIDED" if not body.get("codigoCest") else "PROVIDED",
                    "categoria_especial": product.get("categoriaEspecial"),
                    "categoria_especial_sistema": product.get("categoriaEspecialSistema"),
                    "cfop_entrada": body.get("cdCfopEntrada"),
                    "cfop_saida": body.get("cdCfopSaida"),
                    "tributacao_monofasica": body.get("Tributação Monofásica"),
                    "status": "CREATED_AND_VERIFIED",
                    "codProduto": code,
                    "referenciaCodigo": reference,
                    "descricao": product["descricao"],
                    "body_hash": expected_hash,
                    "empresa_pretendida": COMPANY_CODE,
                    "empresa_efetiva": int(company_link.get("empresaCodigo") or 0),
                    "credencial_usada": credential.variable_name,
                    "preco_venda": company_link.get("precoVenda"),
                    "preco_custo": company_link.get("precoCusto"),
                    "precoCusto": body["precoCusto"],
                    "ncm": body["codigoNcm"],
                    "cest": body.get("codigoCest"),
                    "cost_source": cost_info.get("source"),
                    "cost_status": cost_info.get("cost_status"),
                    "cost_risk": cost_info.get("cost_risk"),
                    "requires_cost_update": cost_info.get("requires_cost_update", False),
                    "dfe_invoice": f"{nfe.get('numero')}/{nfe.get('serie')}" if nfe else None,
                    "profile_id": profile["profile_id"],
                    "profile_level": profile["level"],
                    "profile_canary": canary,
                    "icms_table_reference": profile["referencia_icms"],
                    "pis_cofins_table_reference": profile["referencia_pis_cofins"],
                    "confidence": profile["confidence"],
                    "fiscal_risk": profile["fiscal_risk"],
                    "requires_accountant_review": profile["requires_accountant_review"],
                    "rollback": "NOT_PERFORMED",
                    "bloqueio": "Cadastrado e verificado. Nao reenviar.",
                }
                save_json(CHECKPOINT, checkpoint)

                if profile["requires_accountant_review"]:
                    review[ean] = {
                        **trail,
                        "ean": ean,
                        "descricao": product["descricao"],
                        "produtoCodigo": code,
                        "referenciaCodigo": reference,
                        "ncm": body["codigoNcm"],
                        "cest": body.get("codigoCest"),
                        "familiaComercial": product.get("familiaComercial"),
                        "profileId": product.get("perfilFiscal") or profile["profile_id"],
                        "payloadId": profile["profile_id"] if item["by_payload"] else None,
                        "profileLevel": profile["level"],
                        "baseUsada": {
                            "icmsTableReference": profile["referencia_icms"],
                            "tributoIcms": body["tributoIcms"],
                            "pisCofinsTableReference": profile["referencia_pis_cofins"],
                            "tributoPisCofins": body["tributoPisCofins"],
                            "cfopEntrada": body["cdCfopEntrada"],
                            "cfopSaida": body["cdCfopSaida"],
                            "tratamentoObservado": profile["tratamento_observado"],
                        },
                        "evidencias": profile["evidencias"],
                        "confidence": profile["confidence"],
                        "fiscal_risk": profile["fiscal_risk"],
                        "requires_accountant_review": True,
                        "justificativa": (
                            "Base atribuida por perfil fiscal aprovado pelo proprietario, "
                            f"nivel {profile['level']}, sem lancamento fiscal proprio do produto."
                        ),
                        "criadoEm": datetime.now(timezone.utc).isoformat(),
                    }
                    save_json(ACCOUNTANT_REVIEW, review)

                if product.get("requires_price_review") or cost_info.get("requires_price_review"):
                    pending_price[ean] = {
                        "ean": ean,
                        "descricao": product["descricao"],
                        "produtoCodigo": code,
                        "referenciaCodigo": reference,
                        "precoCustoDfe": body["precoCusto"],
                        "precoVenda": body["precoVenda"],
                        "negative_margin": True,
                        "commercial_risk": "OWNER_ACCEPTED",
                        "requires_price_review": True,
                        "criadoEm": datetime.now(timezone.utc).isoformat(),
                    }
                    save_json(PENDING_PRICE_REVIEW, pending_price)

                if cost_info.get("requires_cost_update"):
                    pending_cost[ean] = {
                        "ean": ean,
                        "descricao": product["descricao"],
                        "produtoCodigo": code,
                        "referenciaCodigo": reference,
                        "precoCustoCadastrado": body["precoCusto"],
                        "precoVenda": body["precoVenda"],
                        "cost_source": cost_info.get("source"),
                        "cost_status": cost_info.get("cost_status"),
                        "cost_risk": cost_info.get("cost_risk"),
                        "requires_cost_update": True,
                        "motivo": cost_info.get("motivoRevisao")
                        or "Sem NF-e de entrada autorizada com o EAN no armazenamento de DF-e",
                        "acaoNecessaria": (
                            "Atualizar custo quando a NF-e de compra entrar no DF-e. "
                            "Correcao de cadastro existente depende de operacao de escrita "
                            "hoje proibida (PUT)."
                        ),
                        "criadoEm": datetime.now(timezone.utc).isoformat(),
                    }
                    save_json(PENDING_COST_UPDATE, pending_cost)

                created_so_far = len(
                    [row for row in executed if row.get("classification") == "CREATED_AND_VERIFIED"]
                )
                persist_lock(
                    wave_lock,
                    status="RUNNING",
                    wave=args.wave,
                    batch=args.batch,
                    by_payload=args.by_payload,
                    post_count=post_count,
                    created=created_so_far,
                    skipped=len(skipped),
                    halted_reason=None,
                    verified_profiles=verified_profiles,
                )
                if created_so_far and created_so_far % SENTINEL_EVERY == 0:
                    confirm_sentinel(credential, reader, f"a_cada_{SENTINEL_EVERY}")
                time.sleep(PAUSE_SECONDS)

            confirm_sentinel(credential, reader, "encerramento")
    except WaveHalted as exc:
        persist_lock(
            wave_lock,
            status="PARTIAL" if args.wave == 5 else "HALTED",
            wave=args.wave,
            batch=args.batch,
            by_payload=args.by_payload,
            post_count=post_count,
            created=len(
                [row for row in executed if row.get("classification") == "CREATED_AND_VERIFIED"]
            ),
            skipped=len(skipped),
            halted_reason=str(exc),
            verified_profiles=verified_profiles,
        )
        raise

    created = [r for r in executed if r.get("classification") == "CREATED_AND_VERIFIED"]
    final_status = (
        "COMPLETED"
        if not halted_reason
        else ("PARTIAL" if args.wave == 5 else "HALTED")
    )
    persist_lock(
        wave_lock,
        status=final_status,
        wave=args.wave,
        batch=args.batch,
        by_payload=args.by_payload,
        post_count=post_count,
        created=len(created),
        skipped=len(skipped),
        halted_reason=halted_reason,
        verified_profiles=verified_profiles,
    )
    save_json(
        result_path,
        {
            "title": f"ONDA {args.wave} LOTE {args.batch} EXECUTION — 118508",
            "executedAt": datetime.now(timezone.utc).isoformat(),
            "groupedByPayload": args.by_payload,
            "endpoint": f"POST {LEGACY_ENDPOINT}",
            "urlSanitized": f"{LEGACY_ENDPOINT}?CHAVE=***REDACTED***",
            "routing": "CHAVE_ONLY",
            "empresaCodigoInQuery": "OMITTED",
            "credentialVariable": credential.variable_name,
            "keyExposed": False,
            "queued": len(queue),
            "gatedOut": gated_out,
            "postCount": post_count,
            "createdAndVerified": len(created),
            "verifiedProfiles": sorted(verified_profiles),
            "haltedReason": halted_reason,
            "products": executed,
            "skipped": skipped,
            "rollback": "NOT_PERFORMED",
            "nextWave": "NONE" if args.wave == 5 else "PAUSED_AWAITING_AUTHORIZATION",
            "ondaFinal": args.wave == 5,
        },
    )

    # O arquivo de perfis guarda o canario verificado, para que a proxima onda nao repita
    # a aprovacao de um perfil que já foi provado em producao.
    if verified_profiles:
        for profile in payload["profiles"]:
            # Com agrupamento por payload, o canario prova o payload: todos os perfis
            # fiscais que geram aquele mesmo payload ficam liberados junto.
            identifier = payload_id(profile) if args.by_payload else profile["profile_id"]
            if identifier not in verified_profiles:
                continue
            proof = next(r for r in created if r["profileId"] == identifier and r["canary"])
            profile["profile_canary_status"] = "VERIFIED"
            profile["produto_canario"] = proof["ean"]
            profile["produto_canario_codigo"] = proof["codProduto"]
            profile["canario_origem"] = (
                f"PAYLOAD_VERIFICADO_NA_ONDA_{args.wave}_LOTE_{args.batch}"
                if args.by_payload
                else f"VERIFICADO_NA_ONDA_{args.wave}"
            )
        save_json(PROFILES, payload)

    print("=" * 78)
    print(f"POSTS ENVIADOS: {post_count}")
    print(f"CRIADOS E VERIFICADOS: {len(created)}/{len(queue)}")
    print(f"REMOVIDOS DO LOTE: {len(skipped)}")
    print(f"PERFIS COM CANARIO VERIFICADO NESTA ONDA: {len(verified_profiles)}")
    print(f"INTERROMPIDO POR: {halted_reason or 'NADA — onda concluida'}")
    print("PROXIMA ONDA: NENHUMA" if args.wave == 5 else "PROXIMA ONDA: PAUSADA aguardando autorizacao")
    print(f"resultado: {result_path}")


if __name__ == "__main__":
    try:
        main()
    except WaveHalted as exc:
        print(f"ONDA NAO EXECUTADA: {exc}")
        print("POSTS ENVIADOS: 0")
        sys.exit(1)
