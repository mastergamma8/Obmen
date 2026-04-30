"""db_async.py — Async PostgreSQL adapter (psycopg3) с пулом соединений.

Пул (psycopg_pool.AsyncConnectionPool) заменяет создание нового соединения
на каждый запрос. Соединение берётся из пула перед выполнением SQL и
возвращается обратно сразу после завершения контекстного менеджера.

Инициализация:
    Вызовите `await db_async.init_pool(dsn)` один раз при старте приложения
    (например, в FastAPI lifespan).
    Вызовите `await db_async.close_pool()` при остановке.

Требует:  psycopg[binary] + psycopg-pool
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Iterable, Sequence

try:
    import psycopg  # type: ignore
except ImportError as exc:
    raise ImportError(
        "psycopg не установлен. Установите: pip install 'psycopg[binary]'"
    ) from exc

try:
    from psycopg_pool import AsyncConnectionPool  # type: ignore
except ImportError as exc:
    raise ImportError(
        "psycopg_pool не установлен. Установите: pip install psycopg-pool"
    ) from exc


# ── Глобальный пул соединений ─────────────────────────────────────────────────

_pool: AsyncConnectionPool | None = None


async def init_pool(dsn: str, min_size: int = 5, max_size: int = 20) -> None:
    """Создаёт пул соединений. Вызывать один раз при старте приложения."""
    global _pool
    _pool = AsyncConnectionPool(
        dsn,
        min_size=min_size,
        max_size=max_size,
        # Ждём до 10 секунд, если все соединения заняты, прежде чем бросить ошибку
        timeout=10.0,
        # Соединение, простаивающее > 5 минут, закрывается и пересоздаётся
        max_idle=300.0,
        open=False,  # открываем явно ниже, чтобы поймать ошибки подключения
    )
    await _pool.open(wait=True)


async def close_pool() -> None:
    """Закрывает пул соединений. Вызывать при остановке приложения."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def _get_pool() -> AsyncConnectionPool:
    if _pool is None:
        raise RuntimeError(
            "Пул соединений не инициализирован. "
            "Вызовите await db_async.init_pool(dsn) при старте приложения."
        )
    return _pool


# ── Вспомогательные типы ──────────────────────────────────────────────────────

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


# ── SQL-транслятор (SQLite → PostgreSQL) ─────────────────────────────────────

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
    # Экранируем литеральный % (например, в LIKE 'prefix_%') → %%
    # ОБЯЗАТЕЛЬНО до замены ? → %s, иначе наши же плейсхолдеры станут %%s.
    sql = sql.replace("%", "%%")
    sql = sql.replace("?", "%s")
    return sql


# ── Курсор ────────────────────────────────────────────────────────────────────

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
        cols = [
            col[0] if isinstance(col, tuple) else getattr(col, "name", None)
            for col in (self._cursor.description or [])
        ]
        return _RowProxy(cols, row)

    async def fetchall(self):
        await self._execute()
        rows = await self._cursor.fetchall()
        cols = [
            col[0] if isinstance(col, tuple) else getattr(col, "name", None)
            for col in (self._cursor.description or [])
        ]
        return [_RowProxy(cols, r) for r in rows]

    async def close(self):
        if self._cursor is not None:
            await self._cursor.close()
            self._cursor = None


# ── Соединение (берётся из пула, не создаётся заново) ─────────────────────────

class _PgConnection:
    """Обёртка над одним соединением из пула.

    При входе в `async with connect(...) as db` берёт соединение из пула.
    При выходе — коммитит (или откатывает при ошибке) и возвращает соединение
    обратно в пул. Это критически важно: `conn.close()` здесь означает
    возврат в пул, а не физическое закрытие TCP-соединения.
    """

    def __init__(self, dsn: str):
        # dsn хранится для обратной совместимости с сигнатурой connect(database),
        # но фактически используется пул, инициализированный через init_pool().
        self._dsn = dsn
        self._conn = None          # физическое psycopg.AsyncConnection
        self._pool_conn = None     # контекстный менеджер пула
        self.row_factory = Row

    async def _ensure_connection(self):
        if self._conn is not None:
            return self._conn
        # Берём соединение из пула
        self._pool_conn = _get_pool().connection()
        self._conn = await self._pool_conn.__aenter__()
        return self._conn

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> _PgCursor:
        return _PgCursor(self, sql, params)

    async def executemany(self, sql: str, seq_of_params: Iterable[Sequence[Any]]):
        last_cursor = None
        for params in seq_of_params:
            last_cursor = await self.execute(sql, params)
        return last_cursor

    async def commit(self):
        if self._conn is not None:
            await self._conn.commit()

    async def rollback(self):
        if self._conn is not None:
            await self._conn.rollback()

    async def close(self):
        """Возвращает соединение в пул (не закрывает физически)."""
        if self._pool_conn is not None:
            # Передаём None, None, None → нет исключения → соединение вернётся
            # в пул в «чистом» состоянии (psycopg_pool сам сделает rollback
            # если транзакция не была закрыта явно).
            await self._pool_conn.__aexit__(None, None, None)
            self._pool_conn = None
            self._conn = None

    async def __aenter__(self):
        await self._ensure_connection()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type is not None:
            await self.rollback()
        # Возвращаем соединение в пул в любом случае
        await self.close()


# ── Публичный API (совместим с aiosqlite) ────────────────────────────────────

def connect(database: str, *args, **kwargs) -> _PgConnection:
    """Возвращает объект соединения, берущий коннект из пула при первом запросе."""
    return _PgConnection(database)


__all__ = ["connect", "Row", "IntegrityError", "init_pool", "close_pool"]
