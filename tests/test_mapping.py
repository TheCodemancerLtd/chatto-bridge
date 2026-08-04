"""Basic tests for the room↔channel bridge map."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from chatto_bridge.discord.mapping import BridgeMap, Persistence


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


# -- persistence tests ------------------------------------------------------


def test_persist_link_to_file() -> None:
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "bridge.json"
        m = BridgeMap({}, path=path)
        m.link("room-x", 42)
        data = json.loads(path.read_text())
        assert data == {"room-x": 42}


def test_persist_unlink_to_file() -> None:
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "bridge.json"
        m = BridgeMap({"room-x": 42}, path=path)
        m.unlink_channel(42)
        data = json.loads(path.read_text())
        assert data == {}


def test_load_from_file_on_startup() -> None:
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "bridge.json"
        path.write_text(json.dumps({"room-a": 10, "room-b": 20}))
        m = BridgeMap({})
        _ = m
        m2 = BridgeMap({}, path=path)
        assert m2.channel_for_room("room-a") == 10
        assert m2.channel_for_room("room-b") == 20


def test_env_var_overrides_file() -> None:
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "bridge.json"
        path.write_text(json.dumps({"room-a": 10}))
        m = BridgeMap({"room-a": 99}, path=path)
        assert m.channel_for_room("room-a") == 99


def test_load_corrupt_file_ignored() -> None:
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "bridge.json"
        path.write_text("not json")
        m = BridgeMap({"room-a": 1}, path=path)
        assert m.channel_for_room("room-a") == 1


def test_load_non_object_file_ignored() -> None:
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "bridge.json"
        path.write_text(json.dumps(["room-a", 1]))
        m = BridgeMap({"room-a": 1}, path=path)
        assert m.channel_for_room("room-a") == 1


def test_missing_file_is_noop() -> None:
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "nonexistent.json"
        m = BridgeMap({"room-a": 1}, path=path)
        assert m.channel_for_room("room-a") == 1


# -- persistence class tests ------------------------------------------------


def test_persistence_crud():
    p = Persistence(":memory:")
    p.upsert_bridge("r1", 100)
    p.upsert_bridge("r2", 200)
    assert p.load_bridges() == {"r1": 100, "r2": 200}
    assert p.delete_by_room("r1") is True
    assert p.load_bridges() == {"r2": 200}
    assert p.delete_by_channel(200) is True
    assert p.load_bridges() == {}
    p.close()


def test_persistence_upsert_replaces_existing_room():
    p = Persistence(":memory:")
    p.upsert_bridge("r1", 100)
    p.upsert_bridge("r1", 200)
    assert p.load_bridges() == {"r1": 200}
    p.close()


def test_persistence_delete_nonexistent_returns_false():
    p = Persistence(":memory:")
    assert p.delete_by_room("missing") is False
    assert p.delete_by_channel(999) is False
    p.close()


def test_persistence_load_empty_db():
    p = Persistence(":memory:")
    assert p.load_bridges() == {}
    p.close()
