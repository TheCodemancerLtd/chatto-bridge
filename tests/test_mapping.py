"""Basic tests for the room↔channel bridge map."""

from __future__ import annotations

import tempfile

from chatto_bridge.mapping import BridgeMap, Persistence

# -- basic tests ------------------------------------------------------------


def test_link_and_lookup() -> None:
    m = BridgeMap({})
    m.link("room-a", "discord", 1)
    assert ("discord", 1) in m.channels_for_room("room-a")
    assert m.room_for_channel("discord", 1) == "room-a"
    m.close()


def test_relinking_removes_stale_pairings() -> None:
    m = BridgeMap({("room-a", "discord"): 1})
    m.link("room-a", "discord", 2)
    assert m.room_for_channel("discord", 1) is None
    assert m.room_for_channel("discord", 2) == "room-a"
    m.close()


def test_channel_reassignment_evicts_prior_room() -> None:
    m = BridgeMap({("room-a", "discord"): 1})
    m.link("room-b", "discord", 1)
    assert m.room_for_channel("discord", 1) == "room-b"
    assert m.channels_for_room("room-a") == []
    m.close()


def test_unlink_channel() -> None:
    m = BridgeMap({("room-a", "discord"): 1})
    assert m.unlink("discord", 1) is True
    assert m.unlink("discord", 1) is False
    assert m.channels_for_room("room-a") == []
    m.close()


def test_items_returns_snapshot() -> None:
    m = BridgeMap({("room-a", "discord"): 1, ("room-b", "discord"): 2})
    items = m.items()
    assert ("room-a", "discord", 1) in items
    assert ("room-b", "discord", 2) in items
    m.close()


# -- persistence tests ------------------------------------------------------


def test_persist_link() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=True) as tmp:
        path = tmp.name
        m = BridgeMap({}, path=path)
        m.link("room-x", "discord", 42)
        m.close()
        m2 = BridgeMap({}, path=path)
        assert ("discord", 42) in m2.channels_for_room("room-x")
        m2.close()


def test_persist_unlink() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=True) as tmp:
        path = tmp.name
        m = BridgeMap({("room-x", "discord"): 42}, path=path)
        m.unlink("discord", 42)
        m.close()
        m2 = BridgeMap({}, path=path)
        assert m2.channels_for_room("room-x") == []
        m2.close()


def test_load_from_persist_on_startup() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=True) as tmp:
        path = tmp.name
        p = Persistence(path)
        p.upsert_bridge("room-a", "discord", 10)
        p.upsert_bridge("room-b", "discord", 20)
        p.close()
        m = BridgeMap({}, path=path)
        assert m.room_for_channel("discord", 10) == "room-a"
        assert m.room_for_channel("discord", 20) == "room-b"
        m.close()


def test_env_var_overrides_persisted() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=True) as tmp:
        path = tmp.name
        p = Persistence(path)
        p.upsert_bridge("room-a", "discord", 1)
        p.close()
        m = BridgeMap({("room-a", "discord"): 99}, path=path)
        assert m.room_for_channel("discord", 99) == "room-a"
        assert m.room_for_channel("discord", 1) is None
        m.close()


def test_no_persist_when_path_none() -> None:
    m = BridgeMap({("room-a", "discord"): 1})
    assert m.room_for_channel("discord", 1) == "room-a"
    m.close()


# -- persistence class tests ------------------------------------------------


def test_persistence_crud():
    p = Persistence(":memory:")
    p.upsert_bridge("r1", "discord", 100)
    p.upsert_bridge("r2", "discord", 200)
    result = p.load_bridges()
    assert result[("r1", "discord")] == 100
    assert result[("r2", "discord")] == 200
    assert p.delete_by_room("r1") is True
    assert ("r1", "discord") not in p.load_bridges()
    assert p.delete_by_platform_channel("discord", 200) is True
    assert p.load_bridges() == {}
    p.close()


def test_persistence_upsert_replaces_existing_room():
    p = Persistence(":memory:")
    p.upsert_bridge("r1", "discord", 100)
    p.upsert_bridge("r1", "discord", 200)
    result = p.load_bridges()
    assert result[("r1", "discord")] == 200
    p.close()


def test_persistence_delete_nonexistent_returns_false():
    p = Persistence(":memory:")
    assert p.delete_by_room("missing") is False
    assert p.delete_by_platform_channel("discord", 999) is False
    p.close()


def test_persistence_load_empty_db():
    p = Persistence(":memory:")
    assert p.load_bridges() == {}
    p.close()


# -- one-to-many tests ------------------------------------------------------


def test_one_to_many_link_and_lookup():
    m = BridgeMap({})
    m.link("room-a", "discord", 100)
    m.link("room-a", "slack", "C01ABC")
    entries = m.channels_for_room("room-a")
    assert ("discord", 100) in entries
    assert ("slack", "C01ABC") in entries
    assert m.room_for_channel("discord", 100) == "room-a"
    assert m.room_for_channel("slack", "C01ABC") == "room-a"
    m.close()


def test_one_to_many_unlink_by_platform():
    m = BridgeMap({})
    m.link("room-a", "discord", 100)
    m.link("room-a", "slack", "C01ABC")
    m.unlink("discord", 100)
    assert m.room_for_channel("discord", 100) is None
    assert m.room_for_channel("slack", "C01ABC") == "room-a"
    m.close()


def test_one_to_many_persist_and_reload():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=True) as tmp:
        path = tmp.name
        m = BridgeMap({}, path=path)
        m.link("room-a", "discord", 100)
        m.link("room-a", "slack", "C01ABC")
        m.close()
        m2 = BridgeMap({}, path=path)
        entries = m2.channels_for_room("room-a")
        assert ("discord", 100) in entries
        assert ("slack", "C01ABC") in entries
        m2.close()


def test_one_to_many_env_override():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=True) as tmp:
        path = tmp.name
        p = Persistence(path)
        p.upsert_bridge("room-a", "discord", 1)
        p.close()
        m = BridgeMap({("room-a", "discord"): 99}, path=path)
        assert m.room_for_channel("discord", 99) == "room-a"
        m.close()


# -- schema migration tests -------------------------------------------------


def test_migration_adds_platform_column():
    """Verify old schema (room_id PRIMARY KEY, channel_id INTEGER) migrates."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=True) as tmp:
        path = tmp.name
        import sqlite3

        conn = sqlite3.connect(path)
        conn.execute(
            "CREATE TABLE bridges (room_id TEXT PRIMARY KEY, channel_id INTEGER UNIQUE NOT NULL)"
        )
        conn.execute(
            "INSERT INTO bridges (room_id, channel_id) VALUES (?, ?)",
            ("old-room", 12345),
        )
        conn.commit()
        conn.close()

        m = BridgeMap({}, path=path)
        assert m.room_for_channel("discord", 12345) == "old-room"
        assert ("discord", 12345) in m.channels_for_room("old-room")
        m.close()
