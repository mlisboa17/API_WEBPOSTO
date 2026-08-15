"""CLI permanente do motor de cadastro. Dry-run por padrao. Sem --execute nesta consolidacao.

Exit codes:
  0  sucesso ou dry-run aprovado
  1  preflight bloqueado ou dados invalidos
  2  autorizacao ausente
  3  empresa diverge do profile resolvido
  4  lock impede a operacao
  5  escrita recusada (falta --execute)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.operational.product_registration.engine_schemas import (  # noqa: E402
    ProductRegistrationRequest,
    RiskAuthorization,
)
from src.operational.product_registration.registration_engine import (  # noqa: E402
    ProductRegistrationService,
)
from src.operational.product_registration.stores import RegistrationLockStore  # noqa: E402

DEFAULT_CHECKPOINT = (
    ROOT / "data" / "product_registration" / "execution" / "checkpoint_118508.json"
)


def _service(args: argparse.Namespace) -> ProductRegistrationService:
    return ProductRegistrationService(Path(args.checkpoint), Path(args.lock) if args.lock else None)


def _print(payload: object) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    forbidden = ("CHAVE=", "WEBPOSTO_", "BEGIN CERTIFICATE")
    if any(token in text for token in forbidden):
        raise SystemExit("saida recusada: possivel segredo")
    print(text)


def cmd_status(args: argparse.Namespace) -> int:
    service = _service(args)
    _print(service.status(args.batch_id))
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    request = _request_from_args(args, execute=False)
    result = _service(args).preflight(request)
    _print(result.model_dump())
    if result.status == "PREFLIGHT_BLOCKED":
        return 1
    if any(item.get("decision") == "ROUTE_REJECTED" for item in result.decisions):
        return 3
    return 0


def cmd_register_one(args: argparse.Namespace) -> int:
    if args.execute:
        print("escrita recusada nesta consolidacao; use o executor de onda com autorizacao propria")
        return 5
    return cmd_preflight(args)


def cmd_register_batch(args: argparse.Namespace) -> int:
    if args.execute:
        print("escrita recusada nesta consolidacao")
        return 5
    lock = RegistrationLockStore(Path(args.lock) if args.lock else Path(args.checkpoint).with_name("wave_lock.json"))
    allowed, reason = lock.can_start()
    if not allowed:
        _print({"ok": False, "reason": reason})
        return 4
    _print({"ok": True, "dry_run": True, "batch": args.batch_id})
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    _print(
        {
            "dry_run": True,
            "produto_codigo": args.product_code,
            "mensagem": "verify exige gateway injetado; use o executor historico para GET real",
        }
    )
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    result = _service(args).resume(args.batch_id)
    _print(result)
    return 0 if result.get("ok") else 4


def cmd_audit_checkpoint(args: argparse.Namespace) -> int:
    store = _service(args).checkpoint
    payload = store.load()
    _print(
        {
            "path": str(store.path),
            "records": len([key for key in payload if not str(key).startswith("_")]),
            "legacy": bool(payload.get("_legacy")),
        }
    )
    return 0


def _request_from_args(args: argparse.Namespace, *, execute: bool) -> ProductRegistrationRequest:
    if not args.empresa:
        raise SystemExit("empresa deve ser informada explicitamente")
    return ProductRegistrationRequest(
        empresa=args.empresa,
        centro=args.centro,
        ean=args.ean,
        descricao=args.descricao,
        preco_venda=args.preco_venda,
        ncm=args.ncm,
        cest=args.cest,
        custo=args.custo,
        cost_source=args.cost_source,
        cost_status=args.cost_status,
        authorization=RiskAuthorization(
            execute=execute,
            allow_pending_dfe_cost=args.allow_pending_dfe_cost,
            accept_fiscal_risk=args.accept_fiscal_risk,
            accept_negative_margin=args.accept_negative_margin,
        ),
        perfil_fiscal={
            "cfop_entrada": "1.102",
            "cfop_saida": "5.405",
            "tributacao_monofasica": 0,
            "tributo_icms": {"cstSaida": "060"} if args.accept_fiscal_risk else {},
            "tributo_pis_cofins": {"cstPisSaida": "01"} if args.accept_fiscal_risk else {},
            "requires_accountant_review": True,
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Motor permanente de cadastro WebPosto")
    parser.add_argument("--empresa", type=int, help="codigo da empresa, obrigatorio nas escritas")
    parser.add_argument("--centro", type=int, default=24886)
    parser.add_argument("--checkpoint", default=str(DEFAULT_CHECKPOINT))
    parser.add_argument("--lock")
    parser.add_argument("--batch-id", default="dry-run")
    parser.add_argument("--execute", action="store_true", help="libera escrita; recusado nesta consolidacao")
    parser.add_argument("--allow-pending-dfe-cost", action="store_true")
    parser.add_argument("--accept-fiscal-risk", action="store_true")
    parser.add_argument("--accept-negative-margin", action="store_true")
    parser.add_argument("--ean")
    parser.add_argument("--descricao")
    parser.add_argument("--preco-venda", type=float, default=0.0)
    parser.add_argument("--ncm")
    parser.add_argument("--cest")
    parser.add_argument("--custo", type=float)
    parser.add_argument("--cost-source")
    parser.add_argument("--cost-status")
    parser.add_argument("--product-code", type=int)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("preflight")
    sub.add_parser("register-one")
    sub.add_parser("register-batch")
    sub.add_parser("verify")
    sub.add_parser("resume")
    sub.add_parser("audit-checkpoint")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    commands = {
        "status": cmd_status,
        "preflight": cmd_preflight,
        "register-one": cmd_register_one,
        "register-batch": cmd_register_batch,
        "verify": cmd_verify,
        "resume": cmd_resume,
        "audit-checkpoint": cmd_audit_checkpoint,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
