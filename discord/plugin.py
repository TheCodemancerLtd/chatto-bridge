"""Discord plugin — wraps the discord.py bot and cogs."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from chatto_bridge.engine import BridgeEngine
from chatto_bridge.plugin import BridgePlugin
from discord.config import DiscordConfig

if TYPE_CHECKING:
    from discord.bot import ChattoBridgeBot

log = logging.getLogger(__name__)

COGS = (
    "chatto_bridge.discord.cogs.nats_listener",
    "chatto_bridge.discord.cogs.chatto_to_discord",
    "chatto_bridge.discord.cogs.discord_to_chatto",
    "chatto_bridge.discord.cogs.admin",
)


class DiscordPlugin(BridgePlugin):
    """Discord plugin implementing the BridgePlugin protocol."""

    name = "discord"

    def __init__(self) -> None:
        self.config = DiscordConfig.from_env()
        self._bot: ChattoBridgeBot | None = None

    @property
    def bot(self) -> ChattoBridgeBot | None:
        """Public access to the Discord bot instance."""
        return self._bot

    async def start(self, engine: BridgeEngine) -> None:
        self._bot = ChattoBridgeBot(engine, self.config.guild_id)
        for cog in COGS:
            await self._bot.load_extension(cog)
            log.info("loaded cog: %s", cog)

    async def stop(self) -> None:
        if self._bot is not None:
            await self._bot.close()
            self._bot = None

    async def send_outbound(
        self,
        room_id: str,
        channel_id: str | int,
        content: str,
        author: str,
    ) -> None:
        if self._bot is None:
            return
        # Handle channel_id gracefully — only convert to int if it looks like one
        if isinstance(channel_id, str):
            try:
                cid: int | str = int(channel_id)
            except (ValueError, TypeError):
                cid = channel_id
        else:
            cid = channel_id
        await self._bot.dispatch("bridge_outbound", room_id, cid, content, author)

    async def run(self, engine: BridgeEngine) -> None:
        if self._bot is None:
            return
        await self._bot.start(self.config.bot_token)

    async def on_inbound_message(
        self,
        channel_id: str | int,
        content: str,
        author: str,
    ) -> None:
        # Inbound is handled by the cog directly via engine.register_inbound
        pass

    async def list_channels(self) -> list[tuple[str | int, str]]:
        if self._bot is None:
            return []
        guild = self._bot.get_guild(self.config.guild_id)
        if guild is None:
            return []
        return [(ch.id, ch.name) for ch in guild.text_channels]

    async def link_channel(self, room_id: str, channel_id: str | int) -> None:
        # Handled by the engine's bridge_map directly
        pass

    async def unlink_channel(self, channel_id: str | int) -> bool:
        return False
