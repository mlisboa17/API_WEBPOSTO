"""Ingestao DF-e + recálculo de custo da 118508. Sem escrita WebPosto e sem manifestacao."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from src.operational.dfe_sync.service import DfeCostSyncService

COMPANY = 118508


def _print(payload: object) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    if any(token in text for token in ("CHAVE=", "BEGIN CERTIFICATE", "DFE_VAULT_MASTER_KEY")):
        raise SystemExit("saida recusada: possivel segredo")
    print(text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync incremental DF-e 118508")
    parser.add_argument("--empresa", type=int, default=COMPANY)
    parser.add_argument("--ean", action="append", default=[])
    parser.add_argument("--execute", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("import-local", "sync-sefaz-once", "recalculate", "status", "run-once"):
        sub.add_parser(name)
    args = parser.parse_args()
    if args.empresa != COMPANY:
        print("empresa deve ser 118508")
        return 3
    if args.execute:
        print("COST_UPDATE_WRITES_NOT_IMPLEMENTED")
        return 5
    service = DfeCostSyncService(ROOT)
    if args.command == "status":
        _print(service.status())
        return 0
    if args.command == "import-local":
        _print(service.import_local())
        return 0
    if args.command == "sync-sefaz-once":
        _print(service.sync_sefaz_once())
        return 0
    if args.command == "recalculate":
        _print(service.recalculate(set(args.ean)))
        return 0
    _print(service.run_once())
    return 0


if __name__ == "__main__":
    sys.exit(main())
