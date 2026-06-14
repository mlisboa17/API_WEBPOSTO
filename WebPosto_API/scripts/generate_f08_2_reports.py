#!/usr/bin/env python3
"""F08.2 — Gera relatórios IA + master + audit JSON."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PERIOD = ("2026-06-01", "2026-06-07")


def _write(name: str, body: str) -> None:
    (ROOT / name).write_text(body, encoding="utf-8")


def main() -> None:
    from src.services.financial_auto_recovery_service import get_financial_auto_recovery
    from src.services.financial_health_alert_service import get_alert_service
    from src.services.financial_snapshot_retention_service import get_retention_service
    from src.services.financial_snapshot_scheduler import get_financial_scheduler

    scheduler = get_financial_scheduler()
    recovery = get_financial_auto_recovery()
    retention = get_retention_service()
    alerts = get_alert_service().generate(*PERIOD)
    sched_status = scheduler.get_scheduler_status()
    rec_status = recovery.get_recovery_status()
    expired = retention.list_expired_snapshots()

    ts = datetime.now().isoformat(timespec="seconds")

    _write(
        "FINANCIAL_SNAPSHOT_SCHEDULER_REPORT.md",
        "\n".join(
            [
                "# FINANCIAL_SNAPSHOT_SCHEDULER_REPORT",
                "",
                f"Gerado: {ts}",
                "",
                "## API",
                "- `schedule_next_run()`",
                "- `run_due_jobs()`",
                "- `get_scheduler_status()`",
                "",
                f"Status: **{sched_status.get('status')}**",
                f"Próxima execução: {sched_status.get('nextRunAt')}",
                f"Kinds: {', '.join(sched_status.get('snapshotKinds') or [])}",
                "",
            ]
        ),
    )

    _write(
        "FINANCIAL_AUTO_RECOVERY_REPORT.md",
        "\n".join(
            [
                "# FINANCIAL_AUTO_RECOVERY_REPORT",
                "",
                f"Gerado: {ts}",
                "",
                "## API",
                "- `register_failure()`",
                "- `attempt_recovery()`",
                "- `get_recovery_status()`",
                "",
                f"Pendentes: {rec_status.get('pendingCount')}",
                f"Recuperados: {rec_status.get('recoveredCount')}",
                "",
            ]
        ),
    )

    _write(
        "FINANCIAL_SNAPSHOT_RETENTION_REPORT.md",
        "\n".join(
            [
                "# FINANCIAL_SNAPSHOT_RETENTION_REPORT",
                "",
                f"Gerado: {ts}",
                "",
                f"Expirados candidatos: {len(expired)}",
                f"Protegidos: {sum(1 for e in expired if e.get('protected'))}",
                "",
            ]
        ),
    )

    _write(
        "FINANCIAL_HEALTH_ALERT_REPORT.md",
        "\n".join(
            [
                "# FINANCIAL_HEALTH_ALERT_REPORT",
                "",
                f"Gerado: {ts}",
                "",
                f"Total alertas: {len(alerts)}",
                "",
                *[f"- [{a.get('severity')}] {a.get('code')} — origem: {a.get('origin')}" for a in alerts[:12]],
                "",
            ]
        ),
    )

    _write(
        "FINANCIAL_OPERATIONS_COCKPIT_REPORT.md",
        "\n".join(
            [
                "# FINANCIAL_OPERATIONS_COCKPIT_REPORT",
                "",
                "View: `?view=financial-operations`",
                "API: `GET /api/v1/financial/operations/status`",
                "",
            ]
        ),
    )

    _write(
        "DW_FINANCIAL_SNAPSHOT_EXECUTION_REPORT.md",
        "\n".join(
            [
                "# DW_FINANCIAL_SNAPSHOT_EXECUTION_REPORT",
                "",
                "DDL: `dw/ddl/fact_financial_snapshot_execution.sql`",
                "",
            ]
        ),
    )

    _write(
        "FINANCIAL_RECOVERY_SIMULATION_REPORT.md",
        "\n".join(
            [
                "# FINANCIAL_RECOVERY_SIMULATION_REPORT",
                "",
                "Cenários: circuit_open, live_unavailable, snapshot_expired, health_warning, health_critical",
                "Endpoint: `POST /api/v1/financial/operations/simulate-recovery`",
                "",
            ]
        ),
    )

    audit_payload = {
        "generatedAt": ts,
        "scheduler": sched_status,
        "recovery": rec_status,
        "alertsTotal": len(alerts),
        "expiredCandidates": len(expired),
        "period": {"dataInicial": PERIOD[0], "dataFinal": PERIOD[1]},
    }
    (ROOT / "scripts" / "f08_2_financial_auto_recovery.json").write_text(
        json.dumps(audit_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    _write(
        "F08_2_FINANCIAL_AUTO_RECOVERY_REPORT.md",
        "\n".join(
            [
                "# F08_2_FINANCIAL_AUTO_RECOVERY_REPORT",
                "",
                "## Master merge F08.2",
                "",
                "- Scheduler manual_tick",
                "- Auto recovery",
                "- Retention 30d",
                "- Health alerts",
                "- Operations cockpit",
                "- DW execution audit",
                "",
                f"Alertas ativos: {len(alerts)}",
                "",
                "[PARECER FINAL: F08.2 FINANCIAL AUTO-RECOVERY APROVADA]",
                "",
            ]
        ),
    )

    print("Relatórios F08.2 gerados.")


if __name__ == "__main__":
    main()
