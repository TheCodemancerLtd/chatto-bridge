"""Subject parsing tests. Full protobuf decoding tests live alongside the
generated bindings once `scripts/generate_pb.sh` has been run."""

from __future__ import annotations

from chatto_bridge.events import parse_room_subject


def test_parse_room_subject_with_live_prefix() -> None:
    assert parse_room_subject("live.evt.room.01H.message_posted") == (
        "01H",
        "message_posted",
    )


def test_parse_room_subject_without_live_prefix() -> None:
    assert parse_room_subject("evt.room.abc.reaction_added") == (
        "abc",
        "reaction_added",
    )


def test_parse_room_subject_rejects_non_room_subjects() -> None:
    assert parse_room_subject("evt.user.u1.presence_updated") is None
    assert parse_room_subject("live.sync.room.x.user_typing") is None
    assert parse_room_subject("evt.room") is None
