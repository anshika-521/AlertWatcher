"""SQLite-backed state store: last-seen state per watcher + alert history (for dedup)."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS watcher_state (
    watcher_name TEXT PRIMARY KEY,
    state_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    watcher_name TEXT NOT NULL,
    message TEXT NOT NULL,
    dedup_key TEXT NOT NULL,
    sent_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_alert_dedup ON alert_history (watcher_name, dedup_key);
"""


class Store:
    def __init__(self, db_path: str = "watchdog.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def get_state(self, watcher_name: str) -> Optional[dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT state_json FROM watcher_state WHERE watcher_name = ?",
                (watcher_name,),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def set_state(self, watcher_name: str, state: dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO watcher_state (watcher_name, state_json, updated_at)
                   VALUES (?, ?, datetime('now'))
                   ON CONFLICT(watcher_name) DO UPDATE SET
                       state_json = excluded.state_json,
                       updated_at = excluded.updated_at""",
                (watcher_name, json.dumps(state)),
            )

    def already_alerted(self, watcher_name: str, dedup_key: str) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM alert_history WHERE watcher_name = ? AND dedup_key = ?",
                (watcher_name, dedup_key),
            ).fetchone()
        return row is not None

    def record_alert(self, watcher_name: str, message: str, dedup_key: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO alert_history (watcher_name, message, dedup_key) VALUES (?, ?, ?)",
                (watcher_name, message, dedup_key),
            )

    def recent_alerts(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT watcher_name, message, sent_at FROM alert_history ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [{"watcher": r[0], "message": r[1], "sent_at": r[2]} for r in rows]

    def list_states(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT watcher_name, state_json, updated_at FROM watcher_state ORDER BY watcher_name",
            ).fetchall()
        return [{"watcher_name": r[0], "state_json": r[1], "updated_at": r[2]} for r in rows]
