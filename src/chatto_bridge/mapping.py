"""In-memory bidirectional mapping between Chatto rooms and Discord channels.

The initial mapping is loaded from the `BRIDGE_MAP` env var and can be
mutated at runtime via the `Admin` cog's `/bridge link` and `/bridge unlink`
slash commands. Persistence to disk is intentionally out of scope for the
initial scaffold — restart repopulates from env.
"""

from __future__ import annotations

from threading import RLock


class BridgeMap:
    def __init__(self, room_to_channel: dict[str, int]) -> None:
        self._lock = RLock()
        self._room_to_channel: dict[str, int] = dict(room_to_channel)
        self._channel_to_room: dict[int, str] = {
            channel: room for room, channel in room_to_channel.items()
        }

    def channel_for_room(self, room_id: str) -> int | None:
        with self._lock:
            return self._room_to_channel.get(room_id)

    def room_for_channel(self, channel_id: int) -> str | None:
        with self._lock:
            return self._channel_to_room.get(channel_id)

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

    def unlink_room(self, room_id: str) -> bool:
        with self._lock:
            channel = self._room_to_channel.pop(room_id, None)
            if channel is None:
                return False
            self._channel_to_room.pop(channel, None)
            return True

    def unlink_channel(self, channel_id: int) -> bool:
        with self._lock:
            room = self._channel_to_room.pop(channel_id, None)
            if room is None:
                return False
            self._room_to_channel.pop(room, None)
            return True

    def items(self) -> list[tuple[str, int]]:
        with self._lock:
            return list(self._room_to_channel.items())
