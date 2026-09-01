"""Lock entre processos e D-1 idempotente — somente fixtures isoladas, sem rede."""

from __future__ import annotations

import asyncio
import inspect
import os
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from src.services.sds_catchup_service import DayStatus, InMemoryDayStatusStore, SdsCatchupService
from src.services.sds_identity import (
    LICENSED_SDS_CODES,
    STATUS_FALHA,
    STATUS_SUCESSO,
)
from src.services.sds_process_lock import (
    LockUnavailable,
    NullSdsProcessLock,
    SqliteSdsProcessLock,
    default_lock_path,
    process_start_key,
    sanitize_lock_path,
)
from src.services.sds_sanitize import sanitize_value
from src.services.webposto.schemas import WEBPOSTO_WRITES

ROOT = Path(__file__).resolve().parents[2]


def test_env_explicito_tem_prioridade(monkeypatch, tmp_path: Path) -> None:
    custom = tmp_path / "custom-lock.sqlite"
    monkeypatch.setenv("SDS_CATCHUP_LOCK_PATH", str(custom))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    assert default_lock_path() == custom


def test_padrao_usa_localappdata(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("SDS_CATCHUP_LOCK_PATH", raising=False)
    local = tmp_path / "AppLocal"
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    path = default_lock_path()
    assert path.name == "sds_catchup_lock.sqlite"
    assert path.parent.name == "WebPosto_API"
    assert path.parent.parent == local
    assert path.parent != ROOT / "data"


def test_padrao_nao_fica_no_projeto(monkeypatch) -> None:
    monkeypatch.delenv("SDS_CATCHUP_LOCK_PATH", raising=False)
    if not (os.environ.get("LOCALAPPDATA") or "").strip():
        pytest.skip("LOCALAPPDATA ausente")
    path = default_lock_path().resolve()
    project = ROOT.resolve()
    assert project not in path.parents
    assert path != project / "data" / "sds_catchup_lock.sqlite"


def test_diretorio_especifico_criado_com_seguranca(tmp_path: Path) -> None:
    target = tmp_path / "WebPosto_API" / "sds_catchup_lock.sqlite"
    lock = SqliteSdsProcessLock(target)
    assert target.parent.is_dir()
    assert lock.acquire(trigger="mkdir") is True
    assert lock.release() is True


def test_falha_abrir_lock_bloqueia_catchup(tmp_path: Path) -> None:
    blocker = tmp_path / "nao-e-diretorio"
    blocker.write_text("x", encoding="utf-8")

    with pytest.raises(LockUnavailable):
        SqliteSdsProcessLock(blocker / "sds_catchup_lock.sqlite")


@pytest.mark.asyncio
async def test_falha_de_lock_nao_segue_sem_lock() -> None:
    class BoomLock:
        def acquire(self, trigger: str = "manual") -> bool:
            raise LockUnavailable("nao foi possivel abrir o lock SDS")

        def release(self) -> bool:
            return False

        def peek(self):
            return None

    calls: list[tuple[int, date]] = []

    async def sync(emp, dia, force=False):
        calls.append((emp, dia))
        return {"status": STATUS_SUCESSO}

    svc = SdsCatchupService(
        sync_day=sync,
        process_lock=BoomLock(),
        today_fn=lambda: date(2026, 8, 14),
        retries=0,
    )
    result = await svc.run(inicio=date(2026, 8, 13), fim=date(2026, 8, 13), empresas=[5555])
    assert result["status"] == "LOCK_UNAVAILABLE"
    assert result["webpostoWrites"] == 0
    assert calls == []
    assert result["metodosWebPosto"] == []


def test_wire_real_nao_usa_null() -> None:
    from src.services.sds_catchup_service import _wire_defaults

    source = inspect.getsource(_wire_defaults)
    assert "production_process_lock" in source
    assert "NullSdsProcessLock" not in source


def test_sanitize_lock_path_nao_vaza_usuario() -> None:
    raw = Path(os.environ.get("LOCALAPPDATA") or "C:/Users/demo/AppData/Local")
    cleaned = sanitize_lock_path(raw / "WebPosto_API" / "sds_catchup_lock.sqlite")
    assert "token" not in cleaned.lower()
    user = (os.environ.get("USERNAME") or "").strip()
    if user:
        assert user not in cleaned
HOLDER = r"""
import os, sys, time
sys.path.insert(0, os.environ["SDS_TEST_ROOT"])
from src.services.sds_process_lock import SqliteSdsProcessLock
lock = SqliteSdsProcessLock(os.environ["SDS_LOCK_DB"])
assert lock.acquire(trigger="holder")
open(os.environ["SDS_READY"], "w").write("1")
time.sleep(float(sys.argv[1]))
lock.release()
"""

ORPHAN = r"""
import os, sys
sys.path.insert(0, os.environ["SDS_TEST_ROOT"])
from src.services.sds_process_lock import SqliteSdsProcessLock
lock = SqliteSdsProcessLock(os.environ["SDS_LOCK_DB"])
assert lock.acquire(trigger="orphan")
open(os.environ["SDS_READY"], "w").write("1")
os._exit(1)
"""

CATCHUP = r"""
import asyncio, os, sys
from datetime import date
sys.path.insert(0, os.environ["SDS_TEST_ROOT"])
from src.services.sds_catchup_service import SdsCatchupService
from src.services.sds_identity import STATUS_SUCESSO
from src.services.sds_process_lock import SqliteSdsProcessLock

calls = []

async def sync(emp, dia, force=False):
    calls.append((emp, dia.isoformat()))
    return {"status": STATUS_SUCESSO, "quantidadeAbastecimentos": 1}

async def main():
    svc = SdsCatchupService(
        sync_day=sync,
        process_lock=SqliteSdsProcessLock(os.environ["SDS_LOCK_DB"]),
        last_sds_date=None,
        today_fn=lambda: date(2026, 8, 29),
        max_days=1,
        retries=0,
    )
    result = await svc.run(
        inicio=date(2026, 8, 20),
        fim=date(2026, 8, 20),
        empresas=[5555],
        trigger="proc-b",
    )
    print(result.get("status") or "RAN")
    print(len(calls))

asyncio.run(main())
"""


def _env(lock_db: Path, ready: Path | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env["SDS_TEST_ROOT"] = str(ROOT)
    env["SDS_LOCK_DB"] = str(lock_db)
    env["WEBPOSTO_WRITES"] = "0"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if ready is not None:
        env["SDS_READY"] = str(ready)
    return env


def _wait_ready(path: Path, timeout: float = 5.0) -> None:
    deadline = datetime.now(timezone.utc).timestamp() + timeout
    while datetime.now(timezone.utc).timestamp() < deadline:
        if path.exists() and path.read_text(encoding="utf-8").strip():
            return
        import time
        time.sleep(0.05)
    raise AssertionError("processo auxiliar nao sinalizou ready")


def test_dois_processos_apenas_um_adquire(tmp_path: Path) -> None:
    lock_db = tmp_path / "lock.sqlite"
    ready = tmp_path / "ready.txt"
    holder = subprocess.Popen(
        [sys.executable, "-c", HOLDER, "2.5"],
        cwd=str(ROOT),
        env=_env(lock_db, ready),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_ready(ready)
        other = SqliteSdsProcessLock(str(lock_db))
        assert other.acquire(trigger="challenger") is False
        info = other.peek()
        assert info is not None
        assert info["status"] == "LOCKED"
        assert "token" not in str(info).lower() or info.get("ownerToken") in (None, "[redacted]")
        assert other.release() is False
    finally:
        holder.wait(timeout=8)
        assert holder.returncode == 0


def test_perdedor_locked_zero_sync(tmp_path: Path) -> None:
    lock_db = tmp_path / "lock.sqlite"
    ready = tmp_path / "ready.txt"
    holder = subprocess.Popen(
        [sys.executable, "-c", HOLDER, "3"],
        cwd=str(ROOT),
        env=_env(lock_db, ready),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_ready(ready)
        proc = subprocess.run(
            [sys.executable, "-c", CATCHUP],
            cwd=str(ROOT),
            env=_env(lock_db),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        assert "LOCKED" in lines
        assert "0" in lines
        assert proc.returncode == 0
    finally:
        holder.wait(timeout=8)


@pytest.mark.asyncio
async def test_lock_liberado_apos_sucesso(tmp_path: Path) -> None:
    lock = SqliteSdsProcessLock(str(tmp_path / "lock.sqlite"))

    async def sync(emp, dia, force=False):
        return {"status": STATUS_SUCESSO, "quantidadeAbastecimentos": 1}

    svc = SdsCatchupService(
        sync_day=sync,
        process_lock=lock,
        today_fn=lambda: date(2026, 8, 14),
        max_days=1,
        retries=0,
    )
    result = await svc.run(inicio=date(2026, 8, 13), fim=date(2026, 8, 13), empresas=[5555])
    assert result.get("status") != "LOCKED"
    assert lock.peek() is None
    assert lock.acquire(trigger="after-success") is True
    assert lock.release() is True


@pytest.mark.asyncio
async def test_lock_liberado_apos_excecao(tmp_path: Path) -> None:
    lock = SqliteSdsProcessLock(str(tmp_path / "lock.sqlite"))

    async def boom(*_a, **_k):
        raise RuntimeError("falha interna de teste")

    class Broken(SdsCatchupService):
        async def _run_locked(self, **kwargs):
            raise RuntimeError("onda quebrou")

    svc = Broken(
        sync_day=boom,
        process_lock=lock,
        today_fn=lambda: date(2026, 8, 14),
        retries=0,
    )
    with pytest.raises(RuntimeError, match="onda quebrou"):
        await svc.run(inicio=date(2026, 8, 13), fim=date(2026, 8, 13), empresas=[5555])
    assert lock.peek() is None
    assert lock.acquire(trigger="after-exc") is True
    lock.release()


def test_nao_proprietario_nao_libera(tmp_path: Path) -> None:
    path = str(tmp_path / "lock.sqlite")
    owner = SqliteSdsProcessLock(path)
    other = SqliteSdsProcessLock(path)
    assert owner.acquire(trigger="owner") is True
    assert other.release() is False
    assert owner.peek() is not None
    assert owner.release() is True


def test_orfao_pode_ser_reassumido(tmp_path: Path) -> None:
    lock_db = tmp_path / "lock.sqlite"
    ready = tmp_path / "ready.txt"
    orphan = subprocess.Popen(
        [sys.executable, "-c", ORPHAN],
        cwd=str(ROOT),
        env=_env(lock_db, ready),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _wait_ready(ready)
    orphan.wait(timeout=8)
    assert orphan.returncode != 0
    successor = SqliteSdsProcessLock(str(lock_db))
    assert successor.acquire(trigger="successor") is True
    assert successor.release() is True


def test_dono_vivo_nao_e_stale_por_idade(tmp_path: Path) -> None:
    path = str(tmp_path / "lock.sqlite")
    owner = SqliteSdsProcessLock(path)
    assert owner.acquire(trigger="long-hold") is True
    owner.mark_acquired_at_for_test("2000-01-01T00:00:00+00:00")
    challenger = SqliteSdsProcessLock(path)
    assert challenger.acquire(trigger="age-only") is False
    assert owner.release() is True


@pytest.mark.asyncio
async def test_d1_sucesso_zero_sync_e_updated_at_intacto() -> None:
    d1 = date(2026, 8, 28)
    store = InMemoryDayStatusStore()
    original = DayStatus(
        empresa_codigo=5555,
        data=d1,
        status=STATUS_SUCESSO,
        quantidade_abastecimentos=10,
        tentativas=1,
        mensagem="ok",
    )
    original.updated_at = datetime(2026, 8, 29, 14, 22, 44, tzinfo=timezone.utc)
    store._rows[(5555, d1)] = original
    calls: list[tuple[int, date]] = []

    async def sync(emp, dia, force=False):
        calls.append((emp, dia))
        return {"status": STATUS_SUCESSO, "quantidadeAbastecimentos": 99}

    svc = SdsCatchupService(
        store=store,
        sync_day=sync,
        process_lock=NullSdsProcessLock(),
        today_fn=lambda: date(2026, 8, 29),
        max_days=1,
        retries=0,
    )
    result = await svc.run(include_d1=True, empresas=[5555], force_days={d1})
    row = await store.get(5555, d1)
    assert calls == []
    assert result["contadores"]["skipped"] >= 1
    assert any(item.get("skipped") for item in result["detalhes"] if item["data"] == d1.isoformat())
    assert row is not None
    assert row.status == STATUS_SUCESSO
    assert row.quantidade_abastecimentos == 10
    assert row.tentativas == 1
    assert row.updated_at == original.updated_at


@pytest.mark.asyncio
async def test_force_true_nao_reprocessa_sucesso() -> None:
    store = InMemoryDayStatusStore()
    await store.upsert(
        DayStatus(empresa_codigo=11495, data=date(2026, 8, 28), status=STATUS_SUCESSO, tentativas=2)
    )
    calls: list[date] = []

    async def sync(emp, dia, force=False):
        calls.append(dia)
        return {"status": STATUS_SUCESSO}

    svc = SdsCatchupService(
        store=store,
        sync_day=sync,
        process_lock=NullSdsProcessLock(),
        today_fn=lambda: date(2026, 8, 29),
        retries=0,
    )
    item = await svc._process_day(11495, date(2026, 8, 28), force=True)
    assert item.get("skipped") is True
    assert calls == []
    kept = await store.get(11495, date(2026, 8, 28))
    assert kept is not None and kept.tentativas == 2


@pytest.mark.asyncio
async def test_falha_retomada_com_force() -> None:
    store = InMemoryDayStatusStore()
    await store.upsert(
        DayStatus(empresa_codigo=74014, data=date(2026, 8, 27), status=STATUS_FALHA, tentativas=1)
    )
    calls: list[date] = []

    async def sync(emp, dia, force=False):
        calls.append(dia)
        return {"status": STATUS_SUCESSO, "quantidadeAbastecimentos": 3}

    svc = SdsCatchupService(
        store=store,
        sync_day=sync,
        process_lock=NullSdsProcessLock(),
        today_fn=lambda: date(2026, 8, 29),
        retries=0,
    )
    item = await svc._process_day(74014, date(2026, 8, 27), force=True)
    assert item["status"] == STATUS_SUCESSO
    assert calls == [date(2026, 8, 27)]


@pytest.mark.asyncio
async def test_duas_execucoes_nao_consolidam_mesmo_par(tmp_path: Path) -> None:
    lock = SqliteSdsProcessLock(str(tmp_path / "lock.sqlite"))
    started = asyncio.Event()
    release = asyncio.Event()
    calls: list[tuple[int, date]] = []

    async def slow(emp, dia, force=False):
        calls.append((emp, dia))
        started.set()
        await release.wait()
        return {"status": STATUS_SUCESSO, "quantidadeAbastecimentos": 1}

    first = SdsCatchupService(
        sync_day=slow,
        process_lock=lock,
        today_fn=lambda: date(2026, 8, 14),
        max_days=1,
        retries=0,
    )
    second = SdsCatchupService(
        sync_day=slow,
        process_lock=SqliteSdsProcessLock(str(tmp_path / "lock.sqlite")),
        today_fn=lambda: date(2026, 8, 14),
        max_days=1,
        retries=0,
    )
    task = asyncio.create_task(
        first.run(inicio=date(2026, 8, 13), fim=date(2026, 8, 13), empresas=[5555])
    )
    await asyncio.wait_for(started.wait(), timeout=2)
    locked = await second.run(inicio=date(2026, 8, 13), fim=date(2026, 8, 13), empresas=[5555])
    assert locked["status"] == "LOCKED"
    assert locked["webpostoWrites"] == 0
    release.set()
    await task
    assert calls == [(5555, date(2026, 8, 13))]


def test_unidades_licenciadas_e_writes() -> None:
    assert LICENSED_SDS_CODES == (5555, 11495, 74014)
    assert 6666 not in LICENSED_SDS_CODES
    assert WEBPOSTO_WRITES == 0
    payload = sanitize_value(
        {
            "status": "LOCKED",
            "ownerPid": os.getpid(),
            "token": "nao-deve-aparecer",
            "url": "https://host/INTEGRACAO/ABASTECIMENTO?CHAVE=secreto",
        }
    )
    dumped = str(payload)
    assert payload["token"] == "[redacted]"
    assert "secreto" not in dumped
    assert "nao-deve-aparecer" not in dumped


@pytest.mark.asyncio
async def test_canario_explicito_ainda_pode_reprocessar_sucesso() -> None:
    store = InMemoryDayStatusStore()
    await store.upsert(
        DayStatus(empresa_codigo=5555, data=date(2026, 8, 13), status=STATUS_SUCESSO, tentativas=1)
    )
    calls: list[date] = []

    async def sync(emp, dia, force=False):
        calls.append(dia)
        return {"status": STATUS_SUCESSO, "quantidadeAbastecimentos": 4}

    svc = SdsCatchupService(
        store=store,
        sync_day=sync,
        process_lock=NullSdsProcessLock(),
        retries=0,
    )
    item = await svc._process_day(
        5555, date(2026, 8, 13), force=True, allow_complete_reprocess=True
    )
    assert item.get("skipped") is not True
    assert calls == [date(2026, 8, 13)]


def test_process_start_key_do_pid_atual() -> None:
    key = process_start_key(os.getpid())
    assert key
    assert "token" not in key.lower()
    assert "http" not in key.lower()


@pytest.mark.asyncio
async def test_simulacao_d1_28_tres_unidades_puladas() -> None:
    store = InMemoryDayStatusStore()
    d1 = date(2026, 8, 28)
    for emp in LICENSED_SDS_CODES:
        await store.upsert(DayStatus(empresa_codigo=emp, data=d1, status=STATUS_SUCESSO, tentativas=1))
    calls: list[tuple[int, date]] = []

    async def sync(emp, dia, force=False):
        calls.append((emp, dia))
        return {"status": STATUS_SUCESSO}

    svc = SdsCatchupService(
        store=store,
        sync_day=sync,
        process_lock=NullSdsProcessLock(),
        today_fn=lambda: date(2026, 8, 29),
        max_days=1,
        retries=0,
    )
    result = await svc.run(include_d1=True, empresas=list(LICENSED_SDS_CODES))
    skipped = [item for item in result["detalhes"] if item.get("skipped") and item["data"] == "2026-08-28"]
    assert {item["empresaCodigo"] for item in skipped} == set(LICENSED_SDS_CODES)
    assert calls == []
    assert result["webpostoWrites"] == 0
    assert 6666 not in result["unidades"]
