"""`commands.Bot` subclass that owns the shared Chatto client and bridge map."""

from __future__ import annotations

import logging

from chatto_bridge.discord.config import BridgeConfig
from chattolib import ChattoClient

import discord
from chatto_bridge.mapping import BridgeMap
from discord.ext import commands

log = logging.getLogger(__name__)

COGS = (
    "chatto_bridge.discord.cogs.nats_listener",
    "chatto_bridge.discord.cogs.chatto_to_discord",
    "chatto_bridge.discord.cogs.discord_to_chatto",
    "chatto_bridge.discord.cogs.admin",
)


class ChattoBridgeBot(commands.Bot):
    """Discord bot wiring: Chatto client + room↔channel map + cogs."""

    chatto: ChattoClient
    bridge_map: BridgeMap
    guild_id: int

    def __init__(self, config: BridgeConfig) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.config = config
        bridge_map = {
            (room, "discord"): channel for room, channel in config.room_to_channel.items()
        }
        self.bridge_map = BridgeMap(bridge_map, path="chatto-bridge.db")
        self.guild_id = config.discord_guild_id

    async def setup_hook(self) -> None:
        # Log into Chatto once; the client is shared across cogs.
        self.chatto = await ChattoClient.login(
            self.config.chatto_login,
            self.config.chatto_password,
            base_url=self.config.chatto_base_url,
        )
        log.info("logged into chatto at %s", self.config.chatto_base_url)

        for cog in COGS:
            await self.load_extension(cog)
            log.info("loaded cog: %s", cog)

        guild = discord.Object(id=self.guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        log.info("synced application commands to guild %s", self.guild_id)

    @property
    def chatto_ready(self) -> bool:
        return hasattr(self, "chatto")

    async def close(self) -> None:
        self.bridge_map.close()
        try:
            await self.chatto.close()
        except Exception:  # noqa: BLE001 — cleanup path, keep going
            log.exception("error closing chatto client")
        await super().close()
