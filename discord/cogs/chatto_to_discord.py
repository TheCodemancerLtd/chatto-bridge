"""Forwards decoded Chatto room events into their linked Discord channel.

The `NatsListener` cog owns the NATS subscription and dispatches
`chatto_room_event` (a `chatto_bridge.events.RoomEvent`). This cog's
listener does the routing:

    RoomEvent.room_id  ── BridgeMap ──▶  Discord channel

For MVP, only `message_posted` is bridged as a webhook-authored message so
that the Chatto author's display name and avatar carry over. Edits and
reactions are logged but not yet mirrored — the switch statement is the
place to add them.
"""

from __future__ import annotations

import logging

from chatto_bridge.discord.bot import ChattoBridgeBot

import discord
from chatto_bridge.events import RoomEvent
from discord.ext import commands

log = logging.getLogger(__name__)

WEBHOOK_NAME = "chatto-bridge"


class ChattoToDiscord(commands.Cog):
    def __init__(self, bot: ChattoBridgeBot) -> None:
        self.bot = bot
        # Cache one webhook per Discord channel so we don't hit the API on
        # every forwarded message.
        self._webhooks: dict[int, discord.Webhook] = {}

    @commands.Cog.listener()
    async def on_chatto_room_event(self, event: RoomEvent) -> None:
        entries = self.bot.bridge_map.channels_for_room(event.room_id)
        channel_id: int | None = None
        for platform, cid in entries:
            if platform == "discord" and isinstance(cid, int):
                channel_id = cid
                break
        if channel_id is None:
            return

        if event.event_type == "message_posted":
            await self._forward_message_posted(channel_id, event)
        else:
            log.debug("unhandled event_type=%s room=%s", event.event_type, event.room_id)

    async def _forward_message_posted(self, channel_id: int, event: RoomEvent) -> None:
        payload = event.payload
        # `MessagePostedEvent` field names come straight from
        # chatto.core.v1.event.proto. We keep the access defensive so a
        # server-side proto addition doesn't crash the bridge.
        body = getattr(payload, "body", None) or getattr(payload, "text", "")
        author_display = (
            getattr(payload, "author_display_name", None)
            or getattr(payload, "author_id", None)
            or "chatto"
        )
        if not body:
            return

        webhook = await self._get_webhook(channel_id)
        if webhook is None:
            log.warning("no webhook available for channel %s", channel_id)
            return

        try:
            await webhook.send(content=body, username=str(author_display))
        except discord.HTTPException:
            log.exception("failed to forward chatto message to discord")

    async def _get_webhook(self, channel_id: int) -> discord.Webhook | None:
        cached = self._webhooks.get(channel_id)
        if cached is not None:
            return cached
        channel = self.bot.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return None
        for existing in await channel.webhooks():
            if existing.name == WEBHOOK_NAME:
                self._webhooks[channel_id] = existing
                return existing
        created = await channel.create_webhook(name=WEBHOOK_NAME)
        self._webhooks[channel_id] = created
        return created


async def setup(bot: ChattoBridgeBot) -> None:
    await bot.add_cog(ChattoToDiscord(bot))
