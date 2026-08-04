from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    level TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    message TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS orders (
                    client_order_id TEXT PRIMARY KEY,
                    trade_date TEXT NOT NULL,
                    signal_key TEXT NOT NULL,
                    broker_order_id TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                """
            )
            connection.commit()

    def set_paused(self, paused: bool, reason: str) -> None:
        payload = json.dumps({"paused": paused, "reason": reason})
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO metadata(key, value, updated_at) VALUES('pause_state', ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                """,
                (payload, now),
            )
            connection.commit()
        self.record_event(
            level="WARNING" if paused else "INFO",
            kind="pause_state",
            message=reason,
            payload={"paused": paused},
        )

    def get_pause_state(self) -> tuple[bool, str]:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT value FROM metadata WHERE key='pause_state'"
            ).fetchone()
        if row is None:
            return False, ""
        parsed = json.loads(str(row["value"]))
        return bool(parsed.get("paused", False)), str(parsed.get("reason", ""))

    def record_event(
        self,
        *,
        level: str,
        kind: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO events(created_at, level, kind, message, payload_json)
                VALUES(?, ?, ?, ?, ?)
                """,
                (now, level, kind, message, json.dumps(payload or {}, default=str)),
            )
            connection.commit()

    def recent_events(self, limit: int = 20) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 100))
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT created_at, level, kind, message, payload_json
                FROM events ORDER BY id DESC LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [
            {
                "created_at": row["created_at"],
                "level": row["level"],
                "kind": row["kind"],
                "message": row["message"],
                "payload": json.loads(row["payload_json"]),
            }
            for row in rows
        ]

    def record_order(
        self,
        *,
        client_order_id: str,
        trade_date: date,
        signal_key: str,
        broker_order_id: str | None,
        status: str,
        payload: dict[str, Any],
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO orders(
                    client_order_id, trade_date, signal_key, broker_order_id,
                    status, created_at, payload_json
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(client_order_id) DO UPDATE SET
                    broker_order_id=excluded.broker_order_id,
                    status=excluded.status,
                    payload_json=excluded.payload_json
                """,
                (
                    client_order_id,
                    trade_date.isoformat(),
                    signal_key,
                    broker_order_id,
                    status,
                    now,
                    json.dumps(payload, default=str),
                ),
            )
            connection.commit()

    def has_order(self, client_order_id: str) -> bool:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT 1 FROM orders WHERE client_order_id=?",
                (client_order_id,),
            ).fetchone()
        return row is not None

    def count_orders_for_day(self, trade_date: date) -> int:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS count FROM orders
                WHERE trade_date=? AND status != 'failed'
                """,
                (trade_date.isoformat(),),
            ).fetchone()
        return int(row["count"] if row is not None else 0)

    def status_summary(self) -> dict[str, Any]:
        paused, reason = self.get_pause_state()
        with closing(self._connect()) as connection:
            order_count = connection.execute("SELECT COUNT(*) AS count FROM orders").fetchone()
            event_count = connection.execute("SELECT COUNT(*) AS count FROM events").fetchone()
        return {
            "paper_only": True,
            "paused": paused,
            "pause_reason": reason,
            "database": str(self.path),
            "orders_recorded": int(order_count["count"] if order_count else 0),
            "events_recorded": int(event_count["count"] if event_count else 0),
        }
