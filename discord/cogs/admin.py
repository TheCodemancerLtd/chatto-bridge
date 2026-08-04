"""`/bridge …` slash commands with interactive room discovery."""

from __future__ import annotations

import logging
import re

from chatto_bridge.discord.bot import ChattoBridgeBot
from chatto_bridge.discord.cogs.room_resolver import resolve_room_id

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger(__name__)

_DISCOVERY_TIMEOUT = 30
_MAX_RETRIES = 3
_ULID_RE = re.compile(r"^[0-2ACJEPHTNPZMRGV5DFKRWXSH36789]{26}$", re.IGNORECASE)


class Admin(commands.Cog):
    bridge_group = app_commands.Group(
        name="bridge",
        description="Manage the Discord ↔ Chatto bridge.",
        default_permissions=discord.Permissions(manage_guild=True),
    )

    def __init__(self, bot: ChattoBridgeBot) -> None:
        self.bot = bot

    @bridge_group.command(name="link", description="Link a Chatto room to this channel.")
    @app_commands.describe(room_id="Chatto room ID, URL, or omit to browse rooms")
    async def link(
        self,
        interaction: discord.Interaction,
        room_id: str | None = None,
    ) -> None:
        channel_id = interaction.channel_id or 0

        if room_id is not None:
            resolved = resolve_room_id(room_id)
            if resolved is None:
                await interaction.response.send_message(
                    "Could not extract room ID from that input.",
                    ephemeral=True,
                )
                return

            # Direct link if URL extraction succeeded or input is a valid ULID
            is_direct = (
                room_id.startswith(("http://", "https://"))
                or resolved != room_id
                or _ULID_RE.match(resolved)
            )
            if is_direct:
                self.bot.bridge_map.link(resolved, channel_id)
                await interaction.response.send_message(
                    f"Linked chatto room `{resolved}` ↔ <#{channel_id}>",
                    ephemeral=True,
                )
                return

            # Fuzzy search - trigger discovery with search term
            if not self.bot.chatto_ready:
                await interaction.response.send_message(
                    "Bot is still starting up. Try again in a moment.",
                    ephemeral=True,
                )
                return

            await interaction.response.send_message("Fetching rooms…", ephemeral=True)
            await self._show_room_picker(interaction, channel_id, search=resolved)
            return

        # Discovery flow
        if not self.bot.chatto_ready:
            await interaction.response.send_message(
                "Bot is still starting up. Try again in a moment.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message("Fetching rooms…", ephemeral=True)
        await self._show_room_picker(interaction, channel_id, search=None)

    async def _show_room_picker(
        self,
        interaction: discord.Interaction,
        channel_id: int,
        search: str | None,
    ) -> None:
        try:
            rooms = await self.bot.chatto.list_rooms()
        except Exception:
            log.exception("list_rooms failed")
            await interaction.followup.send(
                "Failed to fetch Chatto rooms. Check connectivity.",
                ephemeral=True,
            )
            return

        # Filter: exclude archived, apply search
        candidates = [r for r in rooms if not r.room.archived and r.room.kind != "ROOM_KIND_DM"]
        if search:
            search_lower = search.lower()
            candidates = [r for r in candidates if search_lower in r.room.name.lower()]

        if not candidates:
            label = f"matching '{search}'" if search else "available"
            await interaction.followup.send(
                f"No {label} rooms found.",
                ephemeral=True,
            )
            return

        # Build numbered list
        lines = [f"{i + 1}. {r.room.name} (`{r.room.id}`)" for i, r in enumerate(candidates)]
        prompt = (
            "Chatto rooms:\n"
            + "\n".join(lines)
            + f"\n\nReply with a number (1-{len(candidates)}) to link this channel."
        )

        await interaction.followup.send(prompt, ephemeral=True)

        for _attempt in range(_MAX_RETRIES):
            try:
                reply = await self.bot.wait_for(
                    "message",
                    timeout=_DISCOVERY_TIMEOUT,
                    check=lambda m: (
                        m.author.id == interaction.user.id
                        and m.channel.id == interaction.channel.id
                        and m.content.strip()
                    ),
                )
            except TimeoutError:
                await interaction.followup.send(
                    "Timed out. Run `/bridge link` again.", ephemeral=True
                )
                return

            content = reply.content.strip()
            if not content.isdigit():
                await interaction.followup.send(
                    f"Please reply with a number (1-{len(candidates)}).",
                    ephemeral=True,
                )
                continue

            idx = int(content) - 1
            if idx < 0 or idx >= len(candidates):
                await interaction.followup.send(
                    f"Please reply with a number (1-{len(candidates)}).",
                    ephemeral=True,
                )
                continue

            chosen = candidates[idx]
            self.bot.bridge_map.link(chosen.room.id, channel_id)
            await interaction.followup.send(
                f"Linked `{chosen.room.name}` (`{chosen.room.id}`) ↔ <#{channel_id}>",
                ephemeral=True,
            )
            return

        await interaction.followup.send("Too many invalid attempts. Try again.", ephemeral=True)

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
            await interaction.response.send_message("No bridge links configured.", ephemeral=True)
            return
        lines = [f"- `{room}` ↔ <#{channel}>" for room, channel in entries]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)


async def setup(bot: ChattoBridgeBot) -> None:
    await bot.add_cog(Admin(bot))
