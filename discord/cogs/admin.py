"""`/bridge …` slash commands: link, unlink, and list room↔channel pairs.

Runtime edits live in-memory only; restart re-reads `BRIDGE_MAP` from the
env. Persistence is intentionally out of scope for the initial scaffold.
"""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from chatto_bridge.discord.bot import ChattoBridgeBot


class Admin(commands.Cog):
    bridge_group = app_commands.Group(
        name="bridge",
        description="Manage the Discord ↔ Chatto bridge.",
        default_permissions=discord.Permissions(manage_guild=True),
    )

    def __init__(self, bot: ChattoBridgeBot) -> None:
        self.bot = bot

    @bridge_group.command(name="link", description="Link a Chatto room to this channel.")
    @app_commands.describe(room_id="Chatto room ID (ULID)")
    async def link(
        self,
        interaction: discord.Interaction,
        room_id: str,
    ) -> None:
        self.bot.bridge_map.link(room_id, interaction.channel_id or 0)
        await interaction.response.send_message(
            f"Linked chatto room `{room_id}` ↔ <#{interaction.channel_id}>",
            ephemeral=True,
        )

    @bridge_group.command(
        name="unlink",
        description="Unlink this channel from any Chatto room.",
    )
    async def unlink(self, interaction: discord.Interaction) -> None:
        removed = self.bot.bridge_map.unlink_channel(interaction.channel_id or 0)
        if removed:
            await interaction.response.send_message(
                f"Unlinked <#{interaction.channel_id}>",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "This channel wasn't linked to any Chatto room.",
                ephemeral=True,
            )

    @bridge_group.command(name="list", description="Show all active bridge links.")
    async def list_(self, interaction: discord.Interaction) -> None:
        entries = self.bot.bridge_map.items()
        if not entries:
            await interaction.response.send_message(
                "No bridge links configured.", ephemeral=True
            )
            return
        lines = [f"- `{room}` ↔ <#{channel}>" for room, channel in entries]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)


async def setup(bot: ChattoBridgeBot) -> None:
    await bot.add_cog(Admin(bot))
