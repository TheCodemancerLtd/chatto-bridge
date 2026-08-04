"""Discord bot wiring — delegates to the BridgeEngine."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from chattolib import ChattoClient

    from chatto_bridge.engine import BridgeEngine
    from chatto_bridge.mapping import BridgeMap


class ChattoBridgeBot(commands.Bot):
    """Discord bot that delegates Chatto and bridge map access to the engine."""

    def __init__(self, engine: BridgeEngine, guild_id: int) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self._engine = engine
        self.guild_id = guild_id

    @property
    def engine(self) -> BridgeEngine:
        return self._engine

    @property
    def chatto(self) -> ChattoClient:
        return self.engine.chatto

    @property
    def chatto_ready(self) -> bool:
        return self.engine.chatto_ready

    @property
    def bridge_map(self) -> BridgeMap:
        return self.engine.bridge_map

    @property
    def config(self):
        return self.engine.config

    async def setup_hook(self) -> None:
        guild = discord.Object(id=self.guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
