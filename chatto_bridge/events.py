"""Decoded Chatto NATS event representation.

The bridge's `NatsListener` cog receives raw protobuf bytes from Chatto's
`live.evt.room.>` republish subject and turns them into instances of
`RoomEvent` below. The `chatto.core.evt.v1.Event` protobuf bindings live under
`chatto_bridge._pb` and are generated from the vendored `.proto` sources by
`scripts/generate_pb.sh`.

The bindings are optional at import time so that development against the
Discord side alone doesn't require running the proto generator. When the
bindings are missing, `decode_event` raises with a helpful message.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RoomEvent:
    """A decoded `chatto.core.evt.v1.Event` scoped to a specific room."""

    room_id: str
    event_type: str
    """Snake_case oneof case name, e.g. "message_posted", "reaction_added"."""
    payload: Any
    """Concrete oneof sub-message (protobuf message)."""
    raw: Any
    """The full `chatto.core.evt.v1.Event` envelope, for callers that need it."""


def parse_room_subject(subject: str) -> tuple[str, str] | None:
    """Return (room_id, event_type) for a `[live.]evt.room.{id}.{type}` subject.

    Returns None for subjects that don't match the room shape.
    """

    tokens = subject.split(".")
    if tokens and tokens[0] == "live":
        tokens = tokens[1:]
    if len(tokens) < 4 or tokens[0] != "evt" or tokens[1] != "room":
        return None
    room_id = tokens[2]
    event_type = ".".join(tokens[3:])
    return room_id, event_type


def _ensure_pb_importable() -> None:
    """Make the generated `chatto.core.evt.v1` bindings importable.

    chattolib vendors its own top-level `chatto` package (api/realtime
    bindings) via a sys.path insert in `chattolib._pb`. Once that package
    is imported, plain sys.path tricks can't find the bridge's separate
    `chatto.core.*` tree — so we also extend the imported package's
    __path__ with our vendored copy.
    """
    import sys
    from pathlib import Path

    _pb_dir = Path(__file__).parent / "_pb"
    if not _pb_dir.is_dir():
        raise ModuleNotFoundError("chatto.core.evt.v1 bindings")
    if str(_pb_dir) not in sys.path:
        sys.path.insert(0, str(_pb_dir))
    chatto_pkg = sys.modules.get("chatto")
    if chatto_pkg is not None and getattr(chatto_pkg, "__path__", None) is not None:
        extra = str(_pb_dir / "chatto")
        if extra not in list(chatto_pkg.__path__):
            chatto_pkg.__path__.append(extra)


def decode_event(subject: str, data: bytes) -> RoomEvent | None:
    """Decode a raw NATS message into a `RoomEvent`.

    Returns None for non-room subjects. Raises `RuntimeError` if the generated
    protobuf bindings for `chatto.core.evt.v1.Event` are not available — run
    `scripts/generate_pb.sh` to produce them.
    """

    parsed = parse_room_subject(subject)
    if parsed is None:
        return None
    room_id, event_type = parsed

    try:
        from importlib import import_module

        _ensure_pb_importable()
        event_pb2 = import_module("chatto.core.evt.v1.event_pb2")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "chatto.core.evt.v1 protobuf bindings are missing. Run "
            "scripts/generate_pb.sh to generate them."
        ) from exc

    envelope = event_pb2.Event()
    envelope.ParseFromString(data)
    which = envelope.WhichOneof("event")
    payload = getattr(envelope, which) if which else None
    return RoomEvent(
        room_id=room_id,
        event_type=which or event_type,
        payload=payload,
        raw=envelope,
    )
