import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Optional


class Catalog:
    def __init__(self, database_path: str = "catalog.db") -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        connection = sqlite3.connect(self.database_path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL CHECK(kind IN ('movie', 'series')),
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL DEFAULT '',
                    release_year INTEGER,
                    poster_url TEXT NOT NULL DEFAULT '',
                    stream_url TEXT NOT NULL DEFAULT '',
                    backdrop_url TEXT NOT NULL DEFAULT '',
                    quality TEXT NOT NULL DEFAULT '',
                    genre TEXT NOT NULL DEFAULT '',
                    rating REAL,
                    tmdb_id INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS seasons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    series_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
                    season_number INTEGER NOT NULL,
                    UNIQUE(series_id, season_number)
                );
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    season_id INTEGER NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
                    episode_number INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    stream_url TEXT NOT NULL DEFAULT '',
                    quality TEXT NOT NULL DEFAULT '',
                    UNIQUE(season_id, episode_number)
                );
                    CREATE TABLE IF NOT EXISTS uploads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        original_name TEXT NOT NULL,
                        file_size INTEGER NOT NULL DEFAULT 0,
                        mime_type TEXT NOT NULL DEFAULT '',
                        stream_url TEXT NOT NULL,
                        chat_id INTEGER NOT NULL,
                        message_id INTEGER NOT NULL,
                        catalog_item_id INTEGER,
                        created_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS bot_admins (
                        user_id INTEGER PRIMARY KEY,
                        created_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS bot_users (
                        user_id INTEGER PRIMARY KEY,
                        approved_by INTEGER NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS access_notices (
                        scope_id TEXT PRIMARY KEY,
                        created_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS bot_chats (
                        chat_id INTEGER PRIMARY KEY,
                        title TEXT NOT NULL DEFAULT '',
                        chat_type TEXT NOT NULL,
                        registered_by INTEGER NOT NULL,
                        active INTEGER NOT NULL DEFAULT 1,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                """
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(items)").fetchall()}
            migrations = {
                "backdrop_url": "ALTER TABLE items ADD COLUMN backdrop_url TEXT NOT NULL DEFAULT ''",
                "rating": "ALTER TABLE items ADD COLUMN rating REAL",
                "tmdb_id": "ALTER TABLE items ADD COLUMN tmdb_id INTEGER",
                "quality": "ALTER TABLE items ADD COLUMN quality TEXT NOT NULL DEFAULT ''",
                "genre": "ALTER TABLE items ADD COLUMN genre TEXT NOT NULL DEFAULT ''",
            }
            for column, statement in migrations.items():
                if column not in columns:
                    connection.execute(statement)
            episode_columns = {row[1] for row in connection.execute("PRAGMA table_info(episodes)").fetchall()}
            if "quality" not in episode_columns:
                connection.execute("ALTER TABLE episodes ADD COLUMN quality TEXT NOT NULL DEFAULT ''")
            connection.executescript(
                """
                CREATE INDEX IF NOT EXISTS idx_items_kind_title ON items(kind, title);
                CREATE INDEX IF NOT EXISTS idx_items_updated_at ON items(updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_seasons_series_number ON seasons(series_id, season_number);
                CREATE INDEX IF NOT EXISTS idx_episodes_season_number ON episodes(season_id, episode_number);
                CREATE INDEX IF NOT EXISTS idx_uploads_created_at ON uploads(created_at DESC);
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def add_item(
        self,
        kind: str,
        title: str,
        summary: str = "",
        release_year: Optional[int] = None,
        poster_url: str = "",
        stream_url: str = "",
        backdrop_url: str = "",
        rating: Optional[float] = None,
        tmdb_id: Optional[int] = None,
        quality: str = "",
        genre: str = "",
    ) -> int:
        now = self._now()
        with self._connect() as connection:
            cursor = connection.execute(
                """INSERT INTO items
                         (kind, title, summary, release_year, poster_url, stream_url,
                                 backdrop_url, rating, tmdb_id, quality, genre, created_at, updated_at)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                     (kind, title, summary, release_year, poster_url, stream_url,
                             backdrop_url, rating, tmdb_id, quality, genre, now, now),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("Could not create catalog item")
            return int(cursor.lastrowid)

    def update_item(self, item_id: int, **fields: Any) -> None:
        allowed = {
            "title", "summary", "release_year", "poster_url", "stream_url",
            "backdrop_url", "rating", "tmdb_id",
            "quality", "genre",
        }
        updates = {key: value for key, value in fields.items() if key in allowed}
        if not updates:
            return
        updates["updated_at"] = self._now()
        assignments = ", ".join(f"{key} = ?" for key in updates)
        with self._connect() as connection:
            connection.execute(
                f"UPDATE items SET {assignments} WHERE id = ?",
                (*updates.values(), item_id),
            )

    def get_item(self, item_id: int) -> Optional[dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        return dict(row) if row else None

    def search(self, query: str, kind: Optional[str] = None) -> list[dict[str, Any]]:
        pattern = f"%{query.strip()}%"
        sql = "SELECT * FROM items WHERE (title LIKE ? OR summary LIKE ?)"
        parameters: list[Any] = [pattern, pattern]
        if kind:
            sql += " AND kind = ?"
            parameters.append(kind)
        sql += " ORDER BY updated_at DESC"
        with self._connect() as connection:
            return [dict(row) for row in connection.execute(sql, parameters).fetchall()]

    def list_items(self, kind: Optional[str] = None) -> list[dict[str, Any]]:
        return self.search("", kind)

    def delete_item(self, item_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM items WHERE id = ?", (item_id,))

    def add_season(self, series_id: int, season_number: int) -> int:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO seasons (series_id, season_number) VALUES (?, ?)",
                (series_id, season_number),
            )
            row = connection.execute(
                "SELECT id FROM seasons WHERE series_id = ? AND season_number = ?",
                (series_id, season_number),
            ).fetchone()
            return int(row["id"])

    def list_seasons(self, series_id: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT * FROM seasons WHERE series_id = ? ORDER BY season_number",
                (series_id,),
            ).fetchall()]

    def delete_season(self, series_id: int, season_number: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM seasons WHERE series_id = ? AND season_number = ?",
                (series_id, season_number),
            )

    def add_episode(
        self,
        series_id: int,
        season_number: int,
        episode_number: int,
        title: str,
        stream_url: str = "",
        quality: str = "",
    ) -> int:
        season_id = self.add_season(series_id, season_number)
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO episodes
                         (season_id, episode_number, title, stream_url, quality)
                         VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(season_id, episode_number) DO UPDATE SET
                         title = excluded.title, stream_url = excluded.stream_url,
                         quality = excluded.quality""",
                     (season_id, episode_number, title, stream_url, quality),
            )
            row = connection.execute(
                "SELECT id FROM episodes WHERE season_id = ? AND episode_number = ?",
                (season_id, episode_number),
            ).fetchone()
            return int(row["id"])

    def list_episodes(self, series_id: int, season_number: Optional[int] = None) -> list[dict[str, Any]]:
        sql = """SELECT episodes.*, seasons.season_number
                 FROM episodes JOIN seasons ON seasons.id = episodes.season_id
                 WHERE seasons.series_id = ?"""
        parameters: list[Any] = [series_id]
        if season_number is not None:
            sql += " AND seasons.season_number = ?"
            parameters.append(season_number)
        sql += " ORDER BY seasons.season_number, episodes.episode_number"
        with self._connect() as connection:
            return [dict(row) for row in connection.execute(sql, parameters).fetchall()]

    def delete_episode(self, series_id: int, season_number: int, episode_number: int) -> None:
        with self._connect() as connection:
            connection.execute(
                """DELETE FROM episodes WHERE season_id IN
                   (SELECT id FROM seasons WHERE series_id = ? AND season_number = ?)
                   AND episode_number = ?""",
                (series_id, season_number, episode_number),
            )

    def save_upload(
        self,
        original_name: str,
        file_size: int,
        mime_type: str,
        stream_url: str,
        chat_id: int,
        message_id: int,
        catalog_item_id: Optional[int] = None,
    ) -> int:
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT id FROM uploads WHERE chat_id = ? AND message_id = ?",
                (chat_id, message_id),
            ).fetchone()
            if existing:
                return int(existing["id"])
            cursor = connection.execute(
                """INSERT INTO uploads
                   (original_name, file_size, mime_type, stream_url, chat_id,
                    message_id, catalog_item_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    original_name, file_size, mime_type, stream_url, chat_id,
                    message_id, catalog_item_id, self._now(),
                ),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("Could not save upload")
            return int(cursor.lastrowid)

    def attach_upload(self, upload_id: int, catalog_item_id: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE uploads SET catalog_item_id = ? WHERE id = ?",
                (catalog_item_id, upload_id),
            )

    def list_uploads(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT * FROM uploads ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()]

    def summary(self) -> dict[str, int]:
        with self._connect() as connection:
            movies = connection.execute("SELECT COUNT(*) FROM items WHERE kind = 'movie'").fetchone()[0]
            series = connection.execute("SELECT COUNT(*) FROM items WHERE kind = 'series'").fetchone()[0]
            seasons = connection.execute("SELECT COUNT(*) FROM seasons").fetchone()[0]
            episodes = connection.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
            uploads = connection.execute("SELECT COUNT(*) FROM uploads").fetchone()[0]
        return {
            "movies": movies, "series": series, "seasons": seasons,
            "episodes": episodes, "uploads": uploads,
        }

    def checkpoint(self) -> None:
        """Flush the WAL into the main SQLite file before a remote snapshot."""
        with self._connect() as connection:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    def add_admin(self, user_id: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO bot_admins (user_id, created_at) VALUES (?, ?)",
                (user_id, self._now()),
            )

    def remove_admin(self, user_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM bot_admins WHERE user_id = ?", (user_id,))

    def list_admins(self) -> list[int]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT user_id FROM bot_admins ORDER BY user_id"
            ).fetchall()
        return [int(row["user_id"]) for row in rows]

    def add_user(self, user_id: int, approved_by: int) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO bot_users (user_id, approved_by, created_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET approved_by = excluded.approved_by""",
                (user_id, approved_by, self._now()),
            )

    def remove_user(self, user_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM bot_users WHERE user_id = ?", (user_id,))

    def list_users(self) -> list[int]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT user_id FROM bot_users ORDER BY user_id"
            ).fetchall()
        return [int(row["user_id"]) for row in rows]

    def is_user_approved(self, user_id: int) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM bot_users WHERE user_id = ?", (user_id,)
            ).fetchone()
        return row is not None

    def claim_access_notice(self, scope_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO access_notices (scope_id, created_at) VALUES (?, ?)",
                (scope_id, self._now()),
            )
        return cursor.rowcount == 1

    def register_chat(
        self,
        chat_id: int,
        title: str,
        chat_type: str,
        registered_by: int,
    ) -> None:
        now = self._now()
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO bot_chats
                   (chat_id, title, chat_type, registered_by, active, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 1, ?, ?)
                   ON CONFLICT(chat_id) DO UPDATE SET
                   title = excluded.title, chat_type = excluded.chat_type,
                   registered_by = excluded.registered_by, active = 1,
                   updated_at = excluded.updated_at""",
                (chat_id, title, chat_type, registered_by, now, now),
            )

    def unregister_chat(self, chat_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM bot_chats WHERE chat_id = ?", (chat_id,))

    def list_bot_chats(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT * FROM bot_chats WHERE active = 1 ORDER BY title, chat_id"
            ).fetchall()]

    def is_chat_registered(self, chat_id: int) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM bot_chats WHERE chat_id = ? AND active = 1",
                (chat_id,),
            ).fetchone()
        return row is not None

    def integrity_report(self) -> dict[str, list[dict[str, Any]]]:
        """Find duplicate titles and gaps between numbered episodes."""
        with self._connect() as connection:
            duplicate_rows = connection.execute(
                """SELECT kind, lower(trim(title)) AS normalized_title,
                          MIN(title) AS title, GROUP_CONCAT(id) AS item_ids,
                          COUNT(*) AS count
                   FROM items
                   GROUP BY kind, normalized_title
                   HAVING COUNT(*) > 1
                   ORDER BY kind, normalized_title"""
            ).fetchall()
            series_rows = connection.execute(
                """SELECT items.id AS series_id, items.title AS series_title,
                          seasons.season_number,
                          GROUP_CONCAT(episodes.episode_number) AS episode_numbers
                   FROM items
                   JOIN seasons ON seasons.series_id = items.id
                   LEFT JOIN episodes ON episodes.season_id = seasons.id
                   WHERE items.kind = 'series'
                   GROUP BY items.id, items.title, seasons.season_number
                   ORDER BY items.title, seasons.season_number"""
            ).fetchall()

        duplicates: list[dict[str, Any]] = [
            {
                "kind": row["kind"],
                "title": row["title"],
                "item_ids": sorted(int(value) for value in row["item_ids"].split(",")),
                "count": int(row["count"]),
            }
            for row in duplicate_rows
        ]
        missing_episodes: list[dict[str, Any]] = []
        for row in series_rows:
            if not row["episode_numbers"]:
                continue
            episode_numbers = sorted({int(value) for value in row["episode_numbers"].split(",")})
            if len(episode_numbers) < 2:
                continue
            expected = set(range(episode_numbers[0], episode_numbers[-1] + 1))
            missing = sorted(expected - set(episode_numbers))
            if missing:
                missing_episodes.append({
                    "series_id": int(row["series_id"]),
                    "series_title": row["series_title"],
                    "season_number": int(row["season_number"]),
                    "missing_episodes": missing,
                })
        return {"duplicates": duplicates, "missing_episodes": missing_episodes}
