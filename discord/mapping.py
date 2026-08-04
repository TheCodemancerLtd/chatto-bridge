"""In-memory bidirectional mapping between Chatto rooms and Discord channels.

The initial mapping is loaded from the ``BRIDGE_MAP`` env var and can be
mutated at runtime via the ``Admin`` cog's ``/bridge link`` and ``/bridge
unlink`` slash commands.  When a file path is provided, the map is persisted
to JSON on every mutation and reloaded on startup, with ``BRIDGE_MAP`` taking
precedence for overlapping keys.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from threading import RLock

log = logging.getLogger(__name__)


class Persistence:
    """SQLite-backed storage for the bridge map.

    Uses a single ``bridges`` table.  Accepts ``":memory:"`` for testing.
    """

    def __init__(self, path: str) -> None:
        self._conn = sqlite3.connect(path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS bridges "
            "(room_id TEXT PRIMARY KEY, channel_id INTEGER UNIQUE NOT NULL)"
        )
        self._conn.commit()

    def load_bridges(self) -> dict[str, int]:
        rows = self._conn.execute("SELECT room_id, channel_id FROM bridges").fetchall()
        return {row[0]: row[1] for row in rows}

    def upsert_bridge(self, room_id: str, channel_id: int) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO bridges (room_id, channel_id) VALUES (?, ?)",
            (room_id, channel_id),
        )
        self._conn.commit()

    def delete_by_room(self, room_id: str) -> bool:
        cursor = self._conn.execute("DELETE FROM bridges WHERE room_id = ?", (room_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def delete_by_channel(self, channel_id: int) -> bool:
        cursor = self._conn.execute("DELETE FROM bridges WHERE channel_id = ?", (channel_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def close(self) -> None:
        self._conn.close()


class BridgeMap:
    def __init__(
        self,
        room_to_channel: dict[str, int],
        path: str | Path | None = None,
    ) -> None:
        self._lock = RLock()
        self._path: Path | None = Path(path) if path else None

        # Start from persisted state, then overlay env-var config.
        persisted: dict[str, int] = self._load()
        persisted.update(room_to_channel)

        self._room_to_channel: dict[str, int] = persisted
        self._channel_to_room: dict[int, str] = {
            channel: room for room, channel in persisted.items()
        }

    # -- persistence --------------------------------------------------------

    def _load(self) -> dict[str, int]:
        if self._path is None or not self._path.is_file():
            return {}
        try:
            data = json.loads(self._path.read_text())
            if not isinstance(data, dict):
                log.warning("bridge map file %s is not an object, ignoring", self._path)
                return {}
            # Validate types — discard invalid entries rather than crash.
            result: dict[str, int] = {}
            for key, value in data.items():
                if isinstance(key, str) and isinstance(value, int):
                    result[key] = value
            if result:
                log.info("loaded %d bridge map entries from %s", len(result), self._path)
            return result
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("failed to load bridge map from %s: %s", self._path, exc)
            return {}

    def _save(self) -> None:
        if self._path is None:
            return
        try:
            self._path.write_text(json.dumps(self._room_to_channel, indent=2) + "\n")
        except OSError as exc:
            log.warning("failed to save bridge map to %s: %s", self._path, exc)

    # -- lookup -------------------------------------------------------------

    def channel_for_room(self, room_id: str) -> int | None:
        with self._lock:
            return self._room_to_channel.get(room_id)

    def room_for_channel(self, channel_id: int) -> str | None:
        with self._lock:
            return self._channel_to_room.get(channel_id)

    # -- mutation -----------------------------------------------------------

    def link(self, room_id: str, channel_id: int) -> None:
        with self._lock:
            existing_channel = self._room_to_channel.get(room_id)
            if existing_channel is not None:
                self._channel_to_room.pop(existing_channel, None)
            existing_room = self._channel_to_room.get(channel_id)
            if existing_room is not None:
                self._room_to_channel.pop(existing_room, None)
            self._room_to_channel[room_id] = channel_id
            self._channel_to_room[channel_id] = room_id
        self._save()

    def unlink_room(self, room_id: str) -> bool:
        with self._lock:
            channel = self._room_to_channel.pop(room_id, None)
            if channel is None:
                return False
            self._channel_to_room.pop(channel, None)
        self._save()
        return True

    def unlink_channel(self, channel_id: int) -> bool:
        with self._lock:
            room = self._channel_to_room.pop(channel_id, None)
            if room is None:
                return False
            self._room_to_channel.pop(room, None)
        self._save()
        return True

    # -- inspection ---------------------------------------------------------

    def items(self) -> list[tuple[str, int]]:
        with self._lock:
            return list(self._room_to_channel.items())
