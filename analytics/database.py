"""Database connection management for PerformIQ."""

import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "performiq.db"
SCHEMA_PATH = Path(__file__).parent.parent / "server" / "db" / "schema.sql"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = get_connection()
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
    conn.close()
    print(f"Database initialized at {DB_PATH}")


def query(sql: str, params: tuple = (), one: bool = False):
    conn = get_connection()
    try:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        if one:
            return dict(rows[0]) if rows else None
        return [dict(row) for row in rows]
    finally:
        conn.close()


def execute(sql: str, params: tuple = ()) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def execute_many(sql: str, params_list: list):
    conn = get_connection()
    try:
        conn.executemany(sql, params_list)
        conn.commit()
    finally:
        conn.close()
