from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class StateStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS control "
                "(id INTEGER PRIMARY KEY CHECK(id=1), paused INTEGER NOT NULL, reason TEXT)"
            )
            connection.execute(
                "INSERT OR IGNORE INTO control(id, paused, reason) "
                "VALUES(1, 1, 'initial safety pause')"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS events "
                "(created_at TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def pause(self, reason: str) -> None:
        with self._connect() as connection:
            connection.execute("UPDATE control SET paused=1, reason=? WHERE id=1", (reason,))
        self.event("pause", {"reason": reason})

    def resume(self) -> None:
        with self._connect() as connection:
            connection.execute("UPDATE control SET paused=0, reason=NULL WHERE id=1")
        self.event("resume", {})

    def status(self) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute("SELECT paused, reason FROM control WHERE id=1").fetchone()
        if row is None:
            raise RuntimeError("Control row is missing")
        return {"paused": bool(row[0]), "reason": row[1]}

    def event(self, kind: str, payload: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO events(created_at, kind, payload) VALUES(?,?,?)",
                (datetime.now(UTC).isoformat(), kind, json.dumps(payload, sort_keys=True)),
            )
