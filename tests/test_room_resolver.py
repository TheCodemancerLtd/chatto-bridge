from __future__ import annotations

from chatto_bridge.discord.cogs.room_resolver import resolve_room_id


def test_plain_ulid_passthrough() -> None:
    assert resolve_room_id("r3m5t7x9k2") == "r3m5t7x9k2"


def test_http_url_extraction() -> None:
    assert resolve_room_id("https://chat.chatto.run/room/r3m5t7x9k2") == "r3m5t7x9k2"


def test_https_url_with_trailing_slash() -> None:
    assert resolve_room_id("https://chat.chatto.run/room/r3m5t7x9k2/") == "r3m5t7x9k2"


def test_url_with_query_params() -> None:
    assert resolve_room_id("https://chat.chatto.run/room/r3m5t7x9k2?view=thread") == "r3m5t7x9k2"


def test_invalid_url_returns_none() -> None:
    assert resolve_room_id("not-a-url-or-ulid") is not None  # treated as raw input


def test_empty_string_returns_none() -> None:
    assert resolve_room_id("") is None
