"""CLI read-only de propostas de custo DF-e para a empresa 118508.

Somente GET. --execute e recusado com COST_UPDATE_WRITES_NOT_IMPLEMENTED.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from src.operational.cost_update.current_cost_reader import CurrentProductCostReader  # noqa: E402
from src.operational.cost_update.ports import WRITES_NOT_IMPLEMENTED  # noqa: E402
from src.operational.cost_update.service import CostUpdateService  # noqa: E402
from src.operational.product_registration.company_credentials import (  # noqa: E402
    HttpProductReader,
    resolve_credential,
)

COMPANY = 118508
DEFAULT_OUT = ROOT / "data" / "cost_update" / "118508"


class ReadOnlyClient:
    """Recusa qualquer verbo de escrita."""

    def __init__(self, client: httpx.Client) -> None:
        self._client = client
        self.writes = 0

    def get(self, *args, **kwargs):
        return self._client.get(*args, **kwargs)

    def post(self, *args, **kwargs):
        self.writes += 1
        raise RuntimeError(WRITES_NOT_IMPLEMENTED)

    def put(self, *args, **kwargs):
        self.writes += 1
        raise RuntimeError(WRITES_NOT_IMPLEMENTED)

    def patch(self, *args, **kwargs):
        self.writes += 1
        raise RuntimeError(WRITES_NOT_IMPLEMENTED)

    def delete(self, *args, **kwargs):
        self.writes += 1
        raise RuntimeError(WRITES_NOT_IMPLEMENTED)


def _print(payload: object) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    forbidden = ("CHAVE=", "WEBPOSTO_", "BEGIN CERTIFICATE")
    if any(token in text for token in forbidden):
        raise SystemExit("saida recusada: possivel segredo")
    print(text)


def _service(args: argparse.Namespace, key: str | None = None) -> CostUpdateService:
    reader = None
    if key is not None:
        client = ReadOnlyClient(httpx.Client(timeout=60.0))
        reader = CurrentProductCostReader(HttpProductReader(client))
    return CostUpdateService(Path(args.output), reader=reader, empresa=COMPANY)


def cmd_scan(args: argparse.Namespace) -> int:
    credential = resolve_credential(COMPANY)
    if credential.empresa_codigo != COMPANY:
        return 3
    result = _service(args, credential.key).scan(credential.key)
    _print(json.loads(result.model_dump_json(exclude={"items"})))
    return 0


def cmd_propose(args: argparse.Namespace) -> int:
    credential = resolve_credential(COMPANY)
    result = _service(args, credential.key).propose(credential.key)
    _print(result)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    _print(_service(args).status())
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    payload = _service(args).show_proposal(args.ean)
    if payload is None:
        _print({"ok": False, "reason": "PROPOSAL_NOT_FOUND"})
        return 1
    _print(payload)
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    service = _service(args)
    _print({"events": service.audit.events, "status": service.status()})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Propostas de custo DF-e 118508 (read-only)")
    parser.add_argument("--empresa", type=int, default=COMPANY)
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--ean")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("scan")
    sub.add_parser("propose")
    sub.add_parser("status")
    sub.add_parser("show-proposal")
    sub.add_parser("audit")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.empresa != COMPANY:
        print("empresa deve ser 118508 nesta CLI")
        return 3
    if args.execute:
        print(WRITES_NOT_IMPLEMENTED)
        return 5
    commands = {
        "scan": cmd_scan,
        "propose": cmd_propose,
        "status": cmd_status,
        "show-proposal": cmd_show,
        "audit": cmd_audit,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
