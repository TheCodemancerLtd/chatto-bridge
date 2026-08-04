"""Forwards Discord messages into their linked Chatto room via the engine.

Inbound messages are registered with the engine, which handles the Chatto
posting. This keeps the plugin architecture consistent — the plugin doesn't
bypass the engine for outbound operations.
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

        self.bot.engine.register_inbound(
            "discord",
            message.channel.id,
            message.content or "",
            message.author.display_name,
        )


async def setup(bot: ChattoBridgeBot) -> None:
    await bot.add_cog(DiscordToChatto(bot))
