#!/usr/bin/env python3
"""Migrate the bot's SQLite catalog into PostgreSQL.

Usage:
    python migrate_sqlite_to_postgres.py --sqlite catalog.db --postgres "$DATABASE_URL"

The target schema is created by Catalog before rows are copied. The operation
is idempotent for the normal primary-key based tables and can be re-run after
fixing a failed migration.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from catalog import Catalog


TABLES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("items", ("id", "kind", "title", "summary", "release_year", "poster_url", "stream_url", "backdrop_url", "quality", "genre", "rating", "tmdb_id", "created_at", "updated_at")),
    ("seasons", ("id", "series_id", "season_number")),
    ("episodes", ("id", "season_id", "episode_number", "title", "stream_url", "quality")),
    ("uploads", ("id", "original_name", "file_size", "mime_type", "stream_url", "chat_id", "message_id", "catalog_item_id", "created_at")),
    ("bot_admins", ("user_id", "created_at")),
    ("bot_users", ("user_id", "approved_by", "created_at")),
    ("access_notices", ("scope_id", "created_at")),
    ("bot_chats", ("chat_id", "title", "chat_type", "registered_by", "active", "created_at", "updated_at")),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite", default="catalog.db", help="Path to the source SQLite database")
    parser.add_argument("--postgres", help="Target PostgreSQL URL; defaults to DATABASE_URL")
    return parser.parse_args()


def normalize_row(table: str, columns: tuple[str, ...], row: sqlite3.Row) -> tuple[Any, ...]:
    values = [row[column] for column in columns]
    # Older SQLite databases may predate these nullable metadata columns.
    if table == "items":
        for column in ("backdrop_url", "quality", "genre"):
            if column in columns and values[columns.index(column)] is None:
                values[columns.index(column)] = ""
    if table == "episodes" and values[columns.index("quality")] is None:
        values[columns.index("quality")] = ""
    return tuple(values)


def migrate(sqlite_path: str, postgres_url: str) -> None:
    source_path = Path(sqlite_path)
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    if not postgres_url:
        raise ValueError("Provide --postgres or set DATABASE_URL")

    # This creates the target schema and indexes before the copy starts.
    Catalog(database_url=postgres_url)
    source = sqlite3.connect(source_path)
    source.row_factory = sqlite3.Row
    target = psycopg.connect(postgres_url, row_factory=dict_row, connect_timeout=15)
    try:
        with target.cursor() as cursor:
            for table, columns in TABLES:
                existing_columns = {row[1] for row in source.execute(f"PRAGMA table_info({table})").fetchall()}
                if not set(columns).issubset(existing_columns):
                    missing = sorted(set(columns) - existing_columns)
                    raise RuntimeError(f"SQLite table {table} is missing columns: {missing}")
                placeholders = ", ".join(["%s"] * len(columns))
                column_sql = ", ".join(columns)
                sql = f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
                rows = source.execute(f"SELECT {column_sql} FROM {table}").fetchall()
                for row in rows:
                    cursor.execute(sql, normalize_row(table, columns, row))
                if "id" in columns:
                    cursor.execute(
                        "SELECT setval(pg_get_serial_sequence(%s, %s), COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM " + table,
                        (table, "id"),
                    )
                print(f"{table}: copied {len(rows)} rows")
        target.commit()
    except Exception:
        target.rollback()
        raise
    finally:
        source.close()
        target.close()


if __name__ == "__main__":
    args = parse_args()
    import os
    migrate(args.sqlite, args.postgres or os.environ.get("DATABASE_URL", ""))
    print("Migration completed successfully")
