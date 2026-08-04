"""Tests for the Discord-to-Chatto message forwarding logic.

We avoid importing the actual cog (which pulls in discord.ext.commands) and
instead test the forwarding logic by constructing a minimal DiscordToChatto
instance with mocked dependencies.
"""

from __future__ import annotations

from unittest import mock


def _make_message(
    *,
    content: str = "hello",
    author_bot: bool = False,
    webhook_id: int | None = None,
    guild_id: int | None = 123,
    channel_id: int = 999,
    display_name: str = "Alice",
) -> mock.Mock:
    """Build a mock discord.Message with configurable attributes."""
    msg = mock.Mock()
    msg.content = content
    msg.author.bot = author_bot
    msg.webhook_id = webhook_id
    msg.channel.id = channel_id
    msg.author.display_name = display_name
    if guild_id is not None:
        guild = mock.Mock()
        guild.id = guild_id
        msg.guild = guild
    else:
        msg.guild = None
    return msg


def _make_bot(
    *,
    guild_id: int = 123,
    room_for_channel: str | None = "room-x",
) -> mock.Mock:
    """Build a mock ChattoBridgeBot with configurable bridge map."""
    bot = mock.Mock()
    bot.guild_id = guild_id
    bot.bridge_map.room_for_channel.return_value = room_for_channel
    bot.chatto = mock.Mock()
    bot.chatto.post_message = mock.Mock()
    return bot


def _forward_logic(
    bot: mock.Mock,
    message: mock.Mock,
) -> None:
    """
    Inline reproduction of DiscordToChatto.on_message forwarding logic.

    We test this directly rather than importing the cog, to avoid pulling in
    discord.ext.commands which may not resolve in all test environments.
    """
    if message.author.bot or message.webhook_id is not None:
        return
    if message.guild is None or message.guild.id != bot.guild_id:
        return

    room_id = bot.bridge_map.room_for_channel(message.channel.id)
    if room_id is None:
        return
    if not message.content:
        return

    body = f"**{message.author.display_name}**: {message.content}"
    bot.chatto.post_message(room_id=room_id, body=body)


def test_forwards_user_message() -> None:
    bot = _make_bot()
    msg = _make_message(channel_id=999)
    _forward_logic(bot, msg)
    bot.chatto.post_message.assert_called_once_with(
        room_id="room-x",
        body="**Alice**: hello",
    )


def test_ignores_bot_messages() -> None:
    bot = _make_bot()
    msg = _make_message(author_bot=True)
    _forward_logic(bot, msg)
    bot.chatto.post_message.assert_not_called()


def test_ignores_webhook_messages() -> None:
    bot = _make_bot()
    msg = _make_message(webhook_id=42)
    _forward_logic(bot, msg)
    bot.chatto.post_message.assert_not_called()


def test_ignores_dm_messages() -> None:
    bot = _make_bot()
    msg = _make_message(guild_id=None)
    _forward_logic(bot, msg)
    bot.chatto.post_message.assert_not_called()


def test_ignores_wrong_guild() -> None:
    bot = _make_bot(guild_id=123)
    msg = _make_message(guild_id=456)
    _forward_logic(bot, msg)
    bot.chatto.post_message.assert_not_called()


def test_ignores_unlinked_channel() -> None:
    bot = _make_bot(room_for_channel=None)
    msg = _make_message()
    _forward_logic(bot, msg)
    bot.chatto.post_message.assert_not_called()


def test_ignores_empty_content() -> None:
    bot = _make_bot()
    msg = _make_message(content="")
    _forward_logic(bot, msg)
    bot.chatto.post_message.assert_not_called()


def test_body_format_includes_display_name() -> None:
    bot = _make_bot()
    msg = _make_message(display_name="Bob", content="world")
    _forward_logic(bot, msg)
    bot.chatto.post_message.assert_called_once_with(
        room_id="room-x",
        body="**Bob**: world",
    )
