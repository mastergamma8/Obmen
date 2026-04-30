"""db_async.py — Async PostgreSQL adapter (psycopg3).

SQLite поддержка удалена намеренно: в проде используется только PostgreSQL,
двойная ветка усложняла отладку и скрывала ошибки конфигурации.

Требует: psycopg[binary] или psycopg (psycopg3).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Iterable, Sequence

try:
    import psycopg  # type: ignore
except ImportError as exc:
    raise ImportError(
        "psycopg не установлен. Для работы с PostgreSQL необходим psycopg3.\n"
        "Установите его: pip install 'psycopg[binary]'"
    ) from exc


class IntegrityError(Exception):
    """Ошибка нарушения ограничений целостности PostgreSQL."""


class _RowProxy(Mapping[str, Any]):
    __slots__ = ("_columns", "_values", "_index")

    def __init__(self, columns: Sequence[str], values: Sequence[Any]):
        self._columns = tuple(columns)
        self._values = tuple(values)
        self._index = {name: idx for idx, name in enumerate(self._columns)}

    def __getitem__(self, key: str | int) -> Any:
        if isinstance(key, int):
            return self._values[key]
        return self._values[self._index[key]]

    def __iter__(self):
        return iter(self._columns)

    def __len__(self) -> int:
        return len(self._columns)

    def __repr__(self) -> str:
        items = ", ".join(f"{k}={self[k]!r}" for k in self._columns)
        return f"Row({items})"


def Row(cursor, row):  # noqa: N802 — API-совместимость с aiosqlite.Row
    """Фабрика строк с поддержкой dict(row), row[0] и row['column']."""
    description = getattr(cursor, "description", None) or []
    columns = [
        col[0] if isinstance(col, tuple) else getattr(col, "name", None)
        for col in description
    ]
    return _RowProxy(columns, row)


def _translate_sql(sql: str) -> str:
    """Приводит SQL с SQLite-синтаксисом к PostgreSQL.

    Транслируются:
      - BEGIN IMMEDIATE → BEGIN
      - datetime('now') → CURRENT_TIMESTAMP
      - INTEGER PRIMARY KEY AUTOINCREMENT → BIGSERIAL PRIMARY KEY
      - INSERT OR IGNORE INTO … → INSERT INTO … ON CONFLICT DO NOTHING
      - ? → %s (параметры psycopg)
    """
    sql = re.sub(r"\bBEGIN\s+IMMEDIATE\b", "BEGIN", sql, flags=re.I)
    sql = re.sub(r"\bdatetime\('now'\)", "CURRENT_TIMESTAMP", sql, flags=re.I)
    sql = re.sub(
        r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b",
        "BIGSERIAL PRIMARY KEY",
        sql,
        flags=re.I,
    )
    if re.search(r"\bINSERT\s+OR\s+IGNORE\s+INTO\b", sql, flags=re.I):
        sql = re.sub(r"\bINSERT\s+OR\s+IGNORE\s+INTO\b", "INSERT INTO", sql, flags=re.I)
        if "ON CONFLICT" not in sql.upper():
            sql = sql.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
    sql = sql.replace("?", "%s")
    return sql


class _PgCursor:
    def __init__(
        self,
        connection: "_PgConnection",
        sql: str,
        params: Sequence[Any] | None,
    ):
        self._connection = connection
        self._sql = sql
        self._params = tuple(params or ())
        self._cursor = None
        self.rowcount = -1

    async def _execute(self):
        if self._cursor is not None:
            return self
        conn = await self._connection._ensure_connection()
        sql = _translate_sql(self._sql)
        try:
            self._cursor = await conn.execute(sql, self._params)
            self.rowcount = getattr(self._cursor, "rowcount", -1)
            return self
        except psycopg.IntegrityError as exc:
            raise IntegrityError(str(exc)) from exc

    def __await__(self):
        return self._execute().__await__()

    async def __aenter__(self):
        return await self._execute()

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def fetchone(self):
        await self._execute()
        row = await self._cursor.fetchone()
        if row is None:
            return None
        if self._connection.row_factory is None:
            return tuple(row)
        cols = [
            col[0] if isinstance(col, tuple) else getattr(col, "name", None)
            for col in (self._cursor.description or [])
        ]
        return _RowProxy(cols, row)

    async def fetchall(self):
        await self._execute()
        rows = await self._cursor.fetchall()
        if self._connection.row_factory is None:
            return [tuple(r) for r in rows]
        cols = [
            col[0] if isinstance(col, tuple) else getattr(col, "name", None)
            for col in (self._cursor.description or [])
        ]
        return [_RowProxy(cols, r) for r in rows]

    async def close(self):
        if self._cursor is not None:
            await self._cursor.close()
            self._cursor = None


class _PgConnection:
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._conn = None
        self.row_factory = Row

    async def _ensure_connection(self):
        if self._conn is not None:
            return self._conn
        self._conn = await psycopg.AsyncConnection.connect(self._dsn)
        return self._conn

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> _PgCursor:
        return _PgCursor(self, sql, params)

    async def executemany(self, sql: str, seq_of_params: Iterable[Sequence[Any]]):
        last_cursor = None
        for params in seq_of_params:
            last_cursor = await self.execute(sql, params)
        return last_cursor

    async def commit(self):
        conn = await self._ensure_connection()
        await conn.commit()

    async def rollback(self):
        if self._conn is not None:
            await self._conn.rollback()

    async def close(self):
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def __aenter__(self):
        await self._ensure_connection()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type:
            await self.rollback()
        await self.close()


def connect(database: str, *args, **kwargs) -> _PgConnection:
    """Открывает асинхронное подключение к PostgreSQL по DSN."""
    return _PgConnection(database)


__all__ = ["connect", "Row", "IntegrityError"]
