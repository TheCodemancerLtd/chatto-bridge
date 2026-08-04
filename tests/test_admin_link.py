"""Tests for the interactive /bridge link command.

Follows the pattern of test_discord_to_chatto.py: we test the link logic
directly rather than importing the Admin cog, to avoid pulling in
discord.ext.commands which shadows the local discord/ package.
"""

from __future__ import annotations

import re
from unittest import mock

import pytest
from chatto_bridge.discord.cogs.room_resolver import resolve_room_id

_ULID_RE = re.compile(r"^[0-2ACJEPHTNPZMRGV5DFKRWXSH36789]{26}$", re.IGNORECASE)


def _make_bot(*, chatto_ready: bool = True) -> mock.Mock:
    bot = mock.Mock()
    bot.chatto_ready = chatto_ready
    bot.bridge_map = mock.Mock()
    bot.bridge_map.link = mock.Mock()
    bot.bridge_map.room_for_channel = mock.Mock(return_value=None)
    bot.guild_id = 123
    bot.wait_for = mock.AsyncMock()
    if chatto_ready:
        bot.chatto = mock.Mock()
        bot.chatto.list_rooms = mock.AsyncMock(return_value=[])
    else:
        bot.chatto = None
    return bot


def _make_interaction(*, channel_id: int = 999, user_id: int = 111) -> mock.Mock:
    interaction = mock.Mock()
    interaction.channel_id = channel_id
    interaction.user.id = user_id
    interaction.response = mock.Mock()
    interaction.response.send_message = mock.AsyncMock()
    interaction.followup = mock.Mock()
    interaction.followup.send = mock.AsyncMock()
    interaction.channel = mock.Mock()
    interaction.channel.delete_message = mock.AsyncMock()
    return interaction


def _link_logic(
    bot: mock.Mock,
    interaction: mock.Mock,
    room_id: str | None,
) -> str:
    """
    Inline reproduction of Admin.link command logic.

    Tests the decision tree: direct link vs. discovery vs. fuzzy search.
    """
    channel_id = interaction.channel_id or 0

    if room_id is not None:
        resolved = resolve_room_id(room_id)
        if resolved is None:
            return "reject"

        # Direct link if: URL extraction succeeded, or input is a valid ULID
        is_direct = (
            room_id.startswith(("http://", "https://"))
            or resolved != room_id
            or _ULID_RE.match(resolved)
        )
        if is_direct:
            bot.bridge_map.link(resolved, channel_id)
            return "direct"
        else:
            # Fuzzy search - trigger discovery with search term
            if not bot.chatto_ready:
                return "not_ready"
            return "discovery_with_search"
    else:
        # Discovery flow
        if not bot.chatto_ready:
            return "not_ready"
        return "discovery"


@pytest.mark.asyncio
async def test_link_with_plain_ulid() -> None:
    bot = _make_bot()
    interaction = _make_interaction()
    # Valid 26-char ULID is treated as direct link
    result = _link_logic(bot, interaction, "01ARZ3N9K7DEFGHJKMNPRSTVWX")
    assert result == "direct"
    bot.bridge_map.link.assert_called_once_with("01ARZ3N9K7DEFGHJKMNPRSTVWX", 999)


@pytest.mark.asyncio
async def test_link_with_short_id_as_fuzzy() -> None:
    """Short non-ULID strings are treated as fuzzy search."""
    bot = _make_bot()
    interaction = _make_interaction()
    result = _link_logic(bot, interaction, "r3m5t7x9k2")
    assert result == "discovery_with_search"


@pytest.mark.asyncio
async def test_link_with_url() -> None:
    bot = _make_bot()
    interaction = _make_interaction()
    result = _link_logic(bot, interaction, "https://chat.chatto.run/room/r3m5t7x9k2")
    assert result == "direct"
    bot.bridge_map.link.assert_called_once_with("r3m5t7x9k2", 999)


@pytest.mark.asyncio
async def test_link_rejects_not_ready() -> None:
    bot = _make_bot(chatto_ready=False)
    interaction = _make_interaction()
    result = _link_logic(bot, interaction, None)
    assert result == "not_ready"


@pytest.mark.asyncio
async def test_link_discovery_fetches_rooms() -> None:
    from chattolib.types import Room, RoomViewerState, RoomWithViewerState

    room_data = RoomWithViewerState(
        room=Room(
            id="room-abc",
            kind="ROOM_KIND_CHANNEL",
            name="General",
            description="",
            archived=False,
            group_id="",
            universal=False,
        ),
        viewer_state=RoomViewerState(
            is_member=False,
            has_unread=False,
        ),
    )

    bot = _make_bot()
    bot.chatto.list_rooms.return_value = [room_data]

    interaction = _make_interaction()
    result = _link_logic(bot, interaction, None)
    assert result == "discovery"


@pytest.mark.asyncio
async def test_link_fuzzy_search() -> None:
    bot = _make_bot()
    interaction = _make_interaction()
    result = _link_logic(bot, interaction, "general")
    assert result == "discovery_with_search"


@pytest.mark.asyncio
async def test_link_fuzzy_search_not_ready() -> None:
    bot = _make_bot(chatto_ready=False)
    interaction = _make_interaction()
    result = _link_logic(bot, interaction, "general")
    assert result == "not_ready"


@pytest.mark.asyncio
async def test_link_rejects_invalid_url() -> None:
    bot = _make_bot()
    interaction = _make_interaction()
    result = _link_logic(bot, interaction, "https://chat.chatto.run/not-a-room")
    assert result == "reject"


@pytest.mark.asyncio
async def test_link_empty_string() -> None:
    bot = _make_bot()
    interaction = _make_interaction()
    result = _link_logic(bot, interaction, "")
    assert result == "reject"
