"""In-memory bidirectional mapping between Chatto rooms and platform channels.

Supports one-to-many: one Chatto room bridges to channels on multiple
platforms.  The initial mapping is loaded from the ``BRIDGE_MAP`` env var
(parsed by ``CoreConfig``) and can be mutated at runtime.  When a database
path is provided, the map is persisted to SQLite on every mutation.
"""

from __future__ import annotations

import logging
import sqlite3
from threading import RLock

log = logging.getLogger(__name__)


class Persistence:
    """SQLite-backed storage for the bridge map.

    Schema:
        bridges (room_id TEXT, platform TEXT, channel_id TEXT,
                 PRIMARY KEY (room_id, platform))
        UNIQUE INDEX on (platform, channel_id)

    Accepts ``":memory:"`` for testing.
    """

    def __init__(self, path: str) -> None:
        self._conn = sqlite3.connect(path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._ensure_schema()
        self._conn.commit()

    def _ensure_schema(self) -> None:
        # Check if bridges table already exists and needs migration
        tables = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='bridges'"
        ).fetchall()

        if tables:
            # Table exists — check if it needs migration
            cursor = self._conn.execute("PRAGMA table_info(bridges)").fetchall()
            column_names = [col[1] for col in cursor]
            if "platform" not in column_names:
                log.info("migrating bridges table: adding platform column")
                # Add platform column with default
                self._conn.execute(
                    "ALTER TABLE bridges ADD COLUMN platform TEXT NOT NULL DEFAULT 'discord'"
                )
                # Rebuild table with proper constraints
                self._conn.execute(
                    "CREATE TABLE bridges_new "
                    "(room_id TEXT NOT NULL, platform TEXT NOT NULL, "
                    "channel_id TEXT NOT NULL, PRIMARY KEY (room_id, platform))"
                )
                self._conn.execute(
                    "INSERT INTO bridges_new (room_id, platform, channel_id) "
                    "SELECT room_id, platform, CAST(channel_id AS TEXT) FROM bridges"
                )
                self._conn.execute("DROP TABLE bridges")
                self._conn.execute("ALTER TABLE bridges_new RENAME TO bridges")
                self._conn.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS bridges_channel_unique "
                    "ON bridges (platform, channel_id)"
                )
                return

            # Table exists with correct schema, just ensure index
            self._conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS bridges_channel_unique "
                "ON bridges (platform, channel_id)"
            )
        else:
            # Table doesn't exist — create with new schema
            self._conn.execute(
                "CREATE TABLE bridges "
                "(room_id TEXT NOT NULL, platform TEXT NOT NULL, "
                "channel_id TEXT NOT NULL, PRIMARY KEY (room_id, platform))"
            )
            self._conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS bridges_channel_unique "
                "ON bridges (platform, channel_id)"
            )

    def load_bridges(self) -> dict[tuple[str, str], str | int]:
        rows = self._conn.execute("SELECT room_id, platform, channel_id FROM bridges").fetchall()
        result: dict[tuple[str, str], str | int] = {}
        for room_id, platform, channel_id in rows:
            cid: str | int = int(channel_id) if _is_int(channel_id) else channel_id
            result[(room_id, platform)] = cid
        return result

    def upsert_bridge(self, room_id: str, platform: str, channel_id: str | int) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO bridges (room_id, platform, channel_id) VALUES (?, ?, ?)",
            (room_id, platform, str(channel_id)),
        )
        self._conn.commit()

    def delete_by_room(self, room_id: str) -> bool:
        cursor = self._conn.execute("DELETE FROM bridges WHERE room_id = ?", (room_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def delete_by_platform_channel(self, platform: str, channel_id: str | int) -> bool:
        cursor = self._conn.execute(
            "DELETE FROM bridges WHERE platform = ? AND channel_id = ?",
            (platform, str(channel_id)),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def delete_by_room_platform(self, room_id: str, platform: str) -> bool:
        cursor = self._conn.execute(
            "DELETE FROM bridges WHERE room_id = ? AND platform = ?",
            (room_id, platform),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def close(self) -> None:
        self._conn.close()


def _is_int(value: str) -> bool:
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False


class BridgeMap:
    def __init__(
        self,
        bridge_map: dict[tuple[str, str], str | int] | None = None,
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

        # Env var takes precedence
        if bridge_map:
            persisted.update(bridge_map)

        self._room_platform_to_channel: dict[tuple[str, str], str | int] = persisted
        self._platform_channel_to_room: dict[tuple[str, str | int], str] = {
            (platform, channel): room for (room, platform), channel in persisted.items()
        }

    # -- persistence --------------------------------------------------------

    def _persist_link(self, room_id: str, platform: str, channel_id: str | int) -> None:
        if self._persist is not None:
            try:
                self._persist.upsert_bridge(room_id, platform, channel_id)
            except Exception:
                log.exception(
                    "failed to persist bridge link %s/%s -> %s",
                    room_id,
                    platform,
                    channel_id,
                )

    def _persist_delete(self, platform: str, channel_id: str | int) -> None:
        if self._persist is not None:
            try:
                self._persist.delete_by_platform_channel(platform, channel_id)
            except Exception:
                log.exception(
                    "failed to persist bridge delete for %s/%s",
                    platform,
                    channel_id,
                )

    def close(self) -> None:
        if self._persist is not None:
            self._persist.close()

    # -- lookup -------------------------------------------------------------

    def channels_for_room(self, room_id: str) -> list[tuple[str, str | int]]:
        """Return all (platform, channel_id) pairs for a Chatto room."""
        with self._lock:
            return [
                (platform, channel)
                for (room, platform), channel in self._room_platform_to_channel.items()
                if room == room_id
            ]

    def room_for_channel(self, platform: str, channel_id: str | int) -> str | None:
        """Return the Chatto room for a platform channel, or None."""
        with self._lock:
            return self._platform_channel_to_room.get((platform, channel_id))

    # -- mutation -----------------------------------------------------------

    def link(self, room_id: str, platform: str, channel_id: str | int) -> None:
        with self._lock:
            # Evict any existing room for this platform+channel
            existing_room = self._platform_channel_to_room.get((platform, channel_id))
            if existing_room is not None:
                key = (existing_room, platform)
                self._room_platform_to_channel.pop(key, None)
            # Evict any existing channel for this room+platform
            existing_key = (room_id, platform)
            existing_channel = self._room_platform_to_channel.pop(existing_key, None)
            if existing_channel is not None:
                self._platform_channel_to_room.pop((platform, existing_channel), None)
            # Insert new mapping
            self._room_platform_to_channel[(room_id, platform)] = channel_id
            self._platform_channel_to_room[(platform, channel_id)] = room_id
            self._persist_link(room_id, platform, channel_id)

    def unlink(self, platform: str, channel_id: str | int) -> bool:
        with self._lock:
            room = self._platform_channel_to_room.pop((platform, channel_id), None)
            if room is None:
                return False
            self._room_platform_to_channel.pop((room, platform), None)
            self._persist_delete(platform, channel_id)
            return True

    # -- inspection ---------------------------------------------------------

    def items(self) -> list[tuple[str, str, str | int]]:
        with self._lock:
            return [
                (room, platform, channel)
                for (room, platform), channel in self._room_platform_to_channel.items()
            ]
