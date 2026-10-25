"""Decode tests against the generated chatto.core.evt.v1 bindings.

These require `scripts/generate_pb.sh` to have been run (the bindings are
gitignored). They are skipped automatically when `_pb/` is absent.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from chatto_bridge.events import decode_event

_PB_DIR = Path(__file__).parent.parent / "chatto_bridge" / "_pb" / "chatto" / "core" / "evt" / "v1"

pytestmark = pytest.mark.skipif(not _PB_DIR.is_dir(), reason="run scripts/generate_pb.sh first")


@pytest.fixture(autouse=True)
def _pb_on_syspath() -> None:
    """Mirror how events.decode_event makes the gitignored generated
    bindings importable (including alongside chattolib's own `chatto` pkg)."""
    from chatto_bridge.events import _ensure_pb_importable

    _ensure_pb_importable()


def test_decode_message_posted_event() -> None:
    from chatto.core.evt.v1 import event_pb2, message_events_pb2

    envelope = event_pb2.Event()
    envelope.id = "01MSG"
    envelope.actor_id = "01USER"
    envelope.message_posted.CopyFrom(
        message_events_pb2.MessagePostedEvent(room_id="01ROOM", author_id="01USER")
    )

    ev = decode_event("live.evt.room.01ROOM.message_posted", envelope.SerializeToString())
    assert ev is not None
    assert ev.room_id == "01ROOM"
    assert ev.event_type == "message_posted"
    assert ev.raw.id == "01MSG"
    # Post-cutover (ADR-034) the payload is a thin hint: no body on the wire.
    assert not hasattr(ev.payload, "body")
    assert ev.payload.author_id == "01USER"


def test_decode_room_invitation_event() -> None:
    """Room invitations landed in Chatto 0.5.0-beta.20."""
    from chatto.core.evt.v1 import event_pb2, room_events_pb2

    envelope = event_pb2.Event()
    envelope.id = "01INV"
    envelope.room_invitation_created.CopyFrom(
        room_events_pb2.RoomInvitationCreatedEvent(room_id="01ROOM")
    )

    ev = decode_event("live.evt.room.01ROOM.room_invitation_created", envelope.SerializeToString())
    assert ev is not None
    assert ev.event_type == "room_invitation_created"
