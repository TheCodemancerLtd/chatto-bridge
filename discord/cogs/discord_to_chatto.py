"""Forwards Discord messages into their linked Chatto room via chattolib.

Chatto does not accept externally-published NATS events for writes — the
only supported injection path is the ConnectRPC `MessageService.PostMessage`
call, authenticated as a Chatto bot account. `chattolib.ChattoClient`
handles the bearer + session cookie plumbing.
"""

from __future__ import annotations

import logging

from chatto_bridge.discord.bot import ChattoBridgeBot

import discord
from discord.ext import commands

log = logging.getLogger(__name__)


class DiscordToChatto(commands.Cog):
    def __init__(self, bot: ChattoBridgeBot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        # Ignore anything that isn't a user-authored message in the target
        # guild, and skip messages the bridge itself just wrote back via
        # webhook (their webhook_id is set).
        if message.author.bot or message.webhook_id is not None:
            return
        if message.guild is None or message.guild.id != self.bot.guild_id:
            return

        room_id = self.bot.bridge_map.room_for_channel("discord", message.channel.id)
        if room_id is None:
            return
        if not message.content:
            # Attachments-only messages are not handled yet.
            return

        body = f"**{message.author.display_name}**: {message.content}"
        try:
            await self.bot.chatto.post_message(room_id=room_id, body=body)
        except Exception:  # noqa: BLE001 — network / API errors are surfaced in logs
            log.exception("failed to post to chatto room %s", room_id)


async def setup(bot: ChattoBridgeBot) -> None:
    await bot.add_cog(DiscordToChatto(bot))
