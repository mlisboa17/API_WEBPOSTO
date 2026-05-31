from __future__ import annotations

import aiosqlite
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable


@dataclass(frozen=True)
class ParsedExpenseRow:
    description: str
    amount: Decimal
    source_line: int


async def iter_report_lines(stream: AsyncIterator[bytes], chunk_size: int = 64 * 1024) -> AsyncIterator[str]:
    """Itera linhas sem carregar o relatório inteiro em RAM."""
    if chunk_size < 1024:
        raise ValueError("chunk_size must be >= 1024")

    buffer = bytearray()
    async for chunk in stream:
        if not chunk:
            continue
        if len(chunk) > chunk_size * 4:
            # proteção contra chunks gigantes vindos da origem
            chunk = chunk[: chunk_size * 4]
        buffer.extend(chunk)

        while True:
            idx = buffer.find(b"\n")
            if idx < 0:
                break
            line = bytes(memoryview(buffer)[:idx]).decode("utf-8", errors="ignore").strip()
            del buffer[: idx + 1]
            if line:
                yield line

    if buffer:
        line = bytes(memoryview(buffer)).decode("utf-8", errors="ignore").strip()
        if line:
            yield line


def _parse_line(line: str, line_no: int) -> ParsedExpenseRow:
    if line.startswith("{"):
        payload = json.loads(line)
        desc = str(payload.get("description") or payload.get("descricao") or "").strip()
        amount = Decimal(str(payload.get("amount") or payload.get("valor") or "0"))
        return ParsedExpenseRow(description=desc, amount=amount, source_line=line_no)

    # CSV simples: descricao;valor ou descricao,valor
    sep = ";" if ";" in line else ","
    parts = [p.strip() for p in line.split(sep)]
    if len(parts) < 2:
        raise ValueError(f"Invalid expense line at #{line_no}")
    return ParsedExpenseRow(description=parts[0], amount=Decimal(parts[1]), source_line=line_no)


async def parse_expense_stream(stream: AsyncIterator[bytes], chunk_size: int = 64 * 1024) -> AsyncIterator[ParsedExpenseRow]:
    line_no = 0
    async for line in iter_report_lines(stream, chunk_size=chunk_size):
        line_no += 1
        yield _parse_line(line, line_no)


async def _persist_row_sqlite(row: ParsedExpenseRow, sqlite_url: str) -> None:
    db_path = sqlite_url.replace("sqlite+aiosqlite:///", "", 1)
    path = Path(db_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(path.as_posix()) as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expense_ingest_fallback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                amount TEXT NOT NULL,
                source_line INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await conn.execute(
            "INSERT INTO expense_ingest_fallback(description, amount, source_line) VALUES (?, ?, ?)",
            (row.description, str(row.amount), row.source_line),
        )
        await conn.commit()


async def ingest_with_safe_fallback(
    stream: AsyncIterator[bytes],
    primary_writer: Callable[[ParsedExpenseRow], Awaitable[None]],
    sqlite_url: str = "sqlite+aiosqlite:///./webposto.db",
    chunk_size: int = 64 * 1024,
) -> dict[str, Any]:
    """Processa relatório em stream e cai para SQLite local quando o writer principal degrada."""
    processed = 0
    fallback_written = 0
    degraded = False

    async for row in parse_expense_stream(stream, chunk_size=chunk_size):
        processed += 1
        if not degraded:
            try:
                await primary_writer(row)
                continue
            except Exception:
                degraded = True

        await _persist_row_sqlite(row, sqlite_url)
        fallback_written += 1

    return {
        "processed": processed,
        "fallback_written": fallback_written,
        "degraded": degraded,
    }
