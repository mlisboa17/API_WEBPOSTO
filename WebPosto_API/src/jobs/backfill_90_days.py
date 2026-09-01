"""
Backfill híbrido — últimos 90 dias das 3 filiais oficiais.

Uso:
    python -m src.jobs.backfill_90_days
    python -m src.jobs.backfill_90_days --days 90
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections import defaultdict


async def _run(days: int) -> int:
    from src.infrastructure.config.database import close_db, init_db
    from src.services.data_sync_scheduler import CRON_EXPR
    from src.services.data_sync_service import FILIAL_NAMES, get_data_sync_service

    # Windows cp1252: evita UnicodeEncodeError no console
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print("=" * 72)
    print("LOGOS - Backfill hibrido (company_products + sales_daily_summary)")
    print(f"Janela: ultimos {days} dias | Filiais: 5555, 11495, 74014")
    print(f"Cron noturno configurado: {CRON_EXPR} (03:00 AM America/Recife)")
    print("=" * 72)

    await init_db()
    svc = get_data_sync_service()

    def progress(day_idx: int, total_days: int, code: int, res: dict) -> None:
        nome = FILIAL_NAMES.get(code, str(code))
        if "erro" in res:
            print(
                f"[{day_idx}/{total_days}] FAIL {code} {nome} "
                f"{res.get('data_referencia')}: {res.get('erro')}"
            )
            return
        print(
            f"[{day_idx}/{total_days}] OK {code} {nome} {res.get('data_referencia')} "
            f"| abast={res.get('quantidade_abastecimentos')} "
            f"litros={res.get('litros')} fat={res.get('faturamento')} "
            f"produtos={res.get('produtos_descobertos')}"
        )

    try:
        summary = await svc.backfill(days=days, progress_cb=progress)
    finally:
        await close_db()

    print("-" * 72)
    print("RESUMO BACKFILL")
    print(
        f"Periodo: {summary['periodo']['inicio']} -> {summary['periodo']['fim']} "
        f"({summary['dias']} dias)"
    )
    print(
        f"Totais: abast={summary['totais']['abastecimentos']} "
        f"litros={summary['totais']['litros']} "
        f"fat={summary['totais']['faturamento']} "
        f"erros={summary['erros']}"
    )
    print("-" * 72)
    print("PRODUTOS DESCOBERTOS (autodiscovery)")

    by_emp: dict[int, list] = defaultdict(list)
    for p in summary.get("produtos") or []:
        by_emp[int(p["empresa_codigo"])].append(p)

    for code in (5555, 11495, 74014):
        items = sorted(by_emp.get(code, []), key=lambda x: x.get("nome_produto") or "")
        print(f"\n### {code} — {FILIAL_NAMES.get(code)} ({len(items)} produtos)")
        for p in items:
            flag = "ADITIVADO" if p.get("is_aditivado") else "COMUM"
            print(
                f"  - [{p.get('codigo_produto_webposto')}] {p.get('nome_produto')} "
                f"| {p.get('categoria')} | {flag}"
            )

    print("\n" + "=" * 72)
    if summary["erros"]:
        print(f"Concluido com {summary['erros']} erro(s).")
        return 1
    print("Backfill concluido com sucesso.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill 90 dias WebPosto LOGOS")
    parser.add_argument("--days", type=int, default=90, help="Quantidade de dias (default 90)")
    args = parser.parse_args(argv)
    return asyncio.run(_run(max(1, int(args.days))))


if __name__ == "__main__":
    sys.exit(main())
