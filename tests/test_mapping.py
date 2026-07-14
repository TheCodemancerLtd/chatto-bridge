"""Basic tests for the room↔channel bridge map."""

from __future__ import annotations

from chatto_bridge.mapping import BridgeMap


def test_link_and_lookup() -> None:
    m = BridgeMap({})
    m.link("room-a", 1)
    assert m.channel_for_room("room-a") == 1
    assert m.room_for_channel(1) == "room-a"


def test_relinking_removes_stale_pairings() -> None:
    m = BridgeMap({"room-a": 1})
    m.link("room-a", 2)  # move room-a to a different channel
    assert m.channel_for_room("room-a") == 2
    assert m.room_for_channel(1) is None
    assert m.room_for_channel(2) == "room-a"


def test_channel_reassignment_evicts_prior_room() -> None:
    m = BridgeMap({"room-a": 1})
    m.link("room-b", 1)  # channel 1 now belongs to room-b
    assert m.room_for_channel(1) == "room-b"
    assert m.channel_for_room("room-a") is None


def test_unlink_channel() -> None:
    m = BridgeMap({"room-a": 1})
    assert m.unlink_channel(1) is True
    assert m.unlink_channel(1) is False
    assert m.channel_for_room("room-a") is None


def test_items_returns_snapshot() -> None:
    m = BridgeMap({"room-a": 1, "room-b": 2})
    items = dict(m.items())
    assert items == {"room-a": 1, "room-b": 2}
