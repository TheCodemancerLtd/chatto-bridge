"""In-memory bidirectional mapping between Chatto rooms and Discord channels.

The initial mapping is loaded from the ``BRIDGE_MAP`` env var and can be
mutated at runtime via the ``Admin`` cog's ``/bridge link`` and ``/bridge
unlink`` slash commands.  When a database path is provided, the map is
persisted to SQLite on every mutation and reloaded on startup, with
``BRIDGE_MAP`` taking precedence for overlapping keys.
"""

from __future__ import annotations

import logging
import sqlite3
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
        path: str | None = None,
    ) -> None:
        self._lock = RLock()
        self._persist: Persistence | None = None

        if path is not None:
            self._persist = Persistence(path)
            persisted = self._persist.load_bridges()
            if persisted:
                log.info("loaded %d bridge map entries from %s", len(persisted), path)
        else:
            persisted = {}

        persisted.update(room_to_channel)

        self._room_to_channel: dict[str, int] = persisted
        self._channel_to_room: dict[int, str] = {
            channel: room for room, channel in persisted.items()
        }

    # -- persistence --------------------------------------------------------

    def _persist_link(self, room_id: str, channel_id: int) -> None:
        if self._persist is not None:
            try:
                self._persist.upsert_bridge(room_id, channel_id)
            except Exception:
                log.exception("failed to persist bridge link %s -> %s", room_id, channel_id)

    def _persist_delete_room(self, room_id: str) -> None:
        if self._persist is not None:
            try:
                self._persist.delete_by_room(room_id)
            except Exception:
                log.exception("failed to persist bridge delete for room %s", room_id)

    def _persist_delete_channel(self, channel_id: int) -> None:
        if self._persist is not None:
            try:
                self._persist.delete_by_channel(channel_id)
            except Exception:
                log.exception("failed to persist bridge delete for channel %s", channel_id)

    def close(self) -> None:
        if self._persist is not None:
            self._persist.close()

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
        self._persist_link(room_id, channel_id)

    def unlink_room(self, room_id: str) -> bool:
        with self._lock:
            channel = self._room_to_channel.pop(room_id, None)
            if channel is None:
                return False
            self._channel_to_room.pop(channel, None)
        self._persist_delete_room(room_id)
        return True

    def unlink_channel(self, channel_id: int) -> bool:
        with self._lock:
            room = self._channel_to_room.pop(channel_id, None)
            if room is None:
                return False
            self._room_to_channel.pop(room, None)
        self._persist_delete_channel(channel_id)
        return True

    # -- inspection ---------------------------------------------------------

    def items(self) -> list[tuple[str, int]]:
        with self._lock:
            return list(self._room_to_channel.items())
