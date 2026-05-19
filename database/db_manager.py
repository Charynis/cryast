import sqlite3
import threading
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime
from typing import Any, List, Optional

from config import DB_PATH
from database.schema import SCHEMA_MIGRATIONS
from utils.logger import get_logger

logger = get_logger(__name__)

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return _local.conn


@contextmanager
def get_db():
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def run_migrations():
    with get_db() as conn:
        for sql in SCHEMA_MIGRATIONS:
            try:
                conn.execute(sql.strip())
            except sqlite3.Error as e:
                logger.warning(f"Migration skipped: {e}")
    logger.info("Database migrations complete")


def execute(sql: str, params: tuple = ()) -> sqlite3.Cursor:
    with get_db() as conn:
        return conn.execute(sql, params)


def fetchall(sql: str, params: tuple = ()) -> List[sqlite3.Row]:
    conn = _get_conn()
    return conn.execute(sql, params).fetchall()


def fetchone(sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
    conn = _get_conn()
    return conn.execute(sql, params).fetchone()


def insert(table: str, data: dict) -> int:
    cols = ", ".join(data.keys())
    placeholders = ", ".join("?" * len(data))
    sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
    with get_db() as conn:
        cur = conn.execute(sql, tuple(data.values()))
        return cur.lastrowid


def update(table: str, data: dict, where: str, where_params: tuple) -> int:
    set_clause = ", ".join(f"{k} = ?" for k in data.keys())
    sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
    with get_db() as conn:
        cur = conn.execute(sql, tuple(data.values()) + where_params)
        return cur.rowcount


def now_str() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
